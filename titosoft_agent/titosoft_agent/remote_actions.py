"""Execução local de ações remotas assinadas pela central."""
import base64
import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from titosoft_agent.api_client import CentralApiClient
from titosoft_agent.collector import build_inventory
from titosoft_agent.crypto import encrypt_backup

logger = logging.getLogger("titosoft.agent.remote_actions")

ALLOWED_ACTIONS = ("backup_now", "restart_addon", "diagnose_device", "update_core")
ALLOWED_RESTART_ADDONS = ("zigbee2mqtt", "core_mosquitto", "core_matter_server")
# Versão do HA Core: ex. 2026.6, 2026.6.4, 2026.6.0b3. Defesa em profundidade —
# a central já valida, mas o agente nunca confia cegamente no payload.
CORE_VERSION_RE = re.compile(r"^\d{4}\.\d{1,2}(\.\d+)?(b\d+)?$")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _canonical_json(payload: Dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def verify_action(command: Dict[str, Any], central_public_key: str) -> Dict[str, Any]:
    signed_payload = command.get("signed_payload") or {}
    signature = command.get("signature") or ""
    public_key = Ed25519PublicKey.from_public_bytes(_b64decode(central_public_key))
    try:
        public_key.verify(_b64decode(signature), _canonical_json(signed_payload))
    except InvalidSignature as exc:
        raise ValueError("assinatura inválida") from exc

    action_id = command.get("id")
    if signed_payload.get("id") != action_id:
        raise ValueError("id da ação não confere com payload assinado")
    action_type = signed_payload.get("action_type")
    if action_type not in ALLOWED_ACTIONS:
        raise ValueError(f"ação não permitida: {action_type}")
    expires_at = _parse_dt(signed_payload.get("expires_at"))
    if expires_at and expires_at <= datetime.now(timezone.utc):
        raise ValueError("ação expirada")
    payload = signed_payload.get("payload") or {}
    if action_type == "restart_addon" and payload.get("slug") not in ALLOWED_RESTART_ADDONS:
        raise ValueError(f"add-on não permitido: {payload.get('slug')}")
    if action_type == "diagnose_device":
        device_external_id = payload.get("device_external_id")
        if not isinstance(device_external_id, str) or not device_external_id.strip():
            raise ValueError("device_external_id inválido")
    if action_type == "update_core":
        version = payload.get("version")
        if not isinstance(version, str) or not CORE_VERSION_RE.match(version.strip()):
            raise ValueError(f"versão de Core inválida: {version}")
    return {"id": action_id, "action_type": action_type, "payload": payload}


def execute_action(
    command: Dict[str, Any],
    *,
    central_public_key: Optional[str],
    adapter: Any,
    client: CentralApiClient,
    backup_encryption_key: Optional[str],
) -> None:
    action_id = command.get("id")
    if not central_public_key:
        logger.error("Ação remota %s ignorada: CENTRAL_PUBLIC_KEY ausente", action_id)
        client.report_remote_action(action_id, "failed", error_message="CENTRAL_PUBLIC_KEY ausente no agente")
        return

    try:
        action = verify_action(command, central_public_key)
    except Exception as exc:  # noqa: BLE001
        logger.error("Ação remota %s rejeitada: %s", action_id, exc)
        client.report_remote_action(action_id, "failed", error_message=f"Ação rejeitada: {exc}")
        return

    client.report_remote_action(action["id"], "running")
    try:
        if action["action_type"] == "backup_now":
            backup = adapter.create_local_backup()
            payload, provider = encrypt_backup(backup["content"], backup_encryption_key)
            filename = backup["filename"] + (".enc" if provider != "noop" else "")
            result = client.upload_backup(filename, payload, encryption_provider=provider)
        elif action["action_type"] == "restart_addon":
            result = adapter.restart_addon(action["payload"]["slug"])
        elif action["action_type"] == "update_core":
            result = adapter.update_core(action["payload"]["version"])
        elif action["action_type"] == "diagnose_device":
            inventory = build_inventory(adapter)
            device_external_id = action["payload"]["device_external_id"]
            matched = next(
                (device for device in inventory["devices"] if device.get("external_id") == device_external_id),
                None,
            )
            inventory_result = client.send_inventory(inventory)
            result = {
                "device_external_id": device_external_id,
                "device_found": matched is not None,
                "availability_status": matched.get("availability_status") if matched else None,
                "inventory": inventory_result,
            }
        else:
            raise ValueError(f"ação não implementada: {action['action_type']}")
        client.report_remote_action(action["id"], "succeeded", result=result)
        logger.info("Ação remota %s concluída: %s", action["id"], action["action_type"])
    except Exception as exc:  # noqa: BLE001
        logger.exception("Ação remota %s falhou", action["id"])
        client.report_remote_action(action["id"], "failed", error_message=str(exc))
