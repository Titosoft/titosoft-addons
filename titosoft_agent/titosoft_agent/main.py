"""Loop principal do TitoSoft Agent.

Ciclo: enrollment (se necessário) -> heartbeat periódico -> inventário a cada N
heartbeats -> backup real (Supervisor) a cada M heartbeats, criptografado antes
do upload. Falhas de rede são logadas e o loop continua — a casa nunca depende
da central para funcionar.
"""
import logging
import sys
import time

import httpx

from titosoft_agent import __version__
from titosoft_agent.adapters import get_adapter
from titosoft_agent.api_client import CentralApiClient
from titosoft_agent.collector import build_heartbeat, build_inventory
from titosoft_agent.config import AgentConfig
from titosoft_agent.credentials import load_credentials, save_credentials
from titosoft_agent.crypto import encrypt_backup
from titosoft_agent.remote_actions import execute_action

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
logger = logging.getLogger("titosoft.agent")


def run() -> None:
    config = AgentConfig()
    adapter = get_adapter(config.adapter, ha_base_url=config.ha_base_url, ha_token=config.ha_token)

    # Credenciais: env > arquivo persistido > enrollment
    agent_id, agent_token = config.agent_id, config.agent_token
    central_public_key = config.central_public_key
    if not (agent_id and agent_token):
        agent_id, agent_token, stored_public_key = load_credentials()
        central_public_key = central_public_key or stored_public_key
    client = CentralApiClient(config.api_base_url, agent_id, agent_token)

    logger.info("TitoSoft Agent v%s | api=%s adapter=%s", __version__, config.api_base_url, config.adapter)

    # Aguarda API central responder
    for _ in range(30):
        if client.check_connectivity():
            break
        time.sleep(5)
    else:
        logger.error("API central inacessível após 150s; abortando.")
        sys.exit(1)

    # Enrollment quando não há credenciais
    if not (client.agent_id and client.agent_token):
        if not config.enrollment_token:
            logger.error("Sem credenciais nem ENROLLMENT_TOKEN. Gere um token no portal e configure.")
            sys.exit(1)
        try:
            host_info = adapter.get_host_info()
            hostname = host_info.get("hostname")
        except Exception:  # noqa: BLE001 — HA pode estar reiniciando
            hostname = None
        data = client.enroll(config.enrollment_token, __version__, hostname)
        central_public_key = data.get("central_public_key")
        save_credentials(data["agent_id"], data["agent_token"], central_public_key)

    heartbeat_count = 0
    while True:
        # Heartbeat
        try:
            heartbeat = client.send_heartbeat(build_heartbeat(adapter, agent_version=__version__))
            if heartbeat.get("central_public_key") and heartbeat.get("central_public_key") != central_public_key:
                central_public_key = heartbeat["central_public_key"]
                save_credentials(client.agent_id, client.agent_token, central_public_key)
            for command in heartbeat.get("pending_actions", []):
                execute_action(
                    command,
                    central_public_key=central_public_key,
                    adapter=adapter,
                    client=client,
                    backup_encryption_key=config.backup_encryption_key,
                )
            logger.info("Heartbeat enviado (#%d)", heartbeat_count + 1)
        except (httpx.HTTPError, RuntimeError) as exc:
            logger.error("Falha ao enviar heartbeat: %s", exc)

        # Inventário periódico (inclui o primeiro ciclo)
        if heartbeat_count % config.inventory_every_n_heartbeats == 0:
            try:
                result = client.send_inventory(build_inventory(adapter))
                logger.info("Inventário enviado: %s", result)
            except (httpx.HTTPError, RuntimeError) as exc:
                logger.error("Falha ao enviar inventário: %s", exc)

        # Backup real: primeiro ciclo e a cada M heartbeats
        if config.backup_enabled and heartbeat_count % config.backup_every_n_heartbeats == 0:
            try:
                backup = adapter.create_local_backup()
                payload, provider = encrypt_backup(backup["content"], config.backup_encryption_key)
                filename = backup["filename"] + (".enc" if provider != "noop" else "")
                result = client.upload_backup(filename, payload, encryption_provider=provider)
                logger.info("Backup enviado (%s, %d bytes, provider=%s): %s", filename, len(payload), provider, result)
            except NotImplementedError as exc:
                logger.warning("Backup indisponível neste adapter: %s", exc)
            except (httpx.HTTPError, RuntimeError) as exc:
                logger.error("Falha no ciclo de backup: %s", exc)
                try:
                    client.send_event(
                        {
                            "event_type": "backup.failed",
                            "severity": "critical",
                            "title": "Falha ao criar/enviar backup",
                            "description": str(exc),
                        }
                    )
                except httpx.HTTPError:
                    pass

        heartbeat_count += 1
        time.sleep(config.heartbeat_interval_seconds)


if __name__ == "__main__":
    run()
