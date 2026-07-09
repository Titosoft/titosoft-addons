"""Cliente HTTP do agente para a API central TitoSoft.

Toda comunicação é OUTBOUND (agente -> API). O agente nunca abre porta.
"""
import hashlib
import logging
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger("titosoft.agent.api")


class CentralApiClient:
    def __init__(self, base_url: str, agent_id: Optional[str] = None, agent_token: Optional[str] = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.agent_id = agent_id
        self.agent_token = agent_token

    # ------------------------------------------------------------- helpers --
    def _headers(self) -> Dict[str, str]:
        return {"X-Agent-Token": self.agent_token or ""}

    def _post(self, path: str, json: Dict[str, Any], authenticated: bool = True) -> Dict[str, Any]:
        headers = self._headers() if authenticated else {}
        resp = httpx.post(f"{self.base_url}{path}", json=json, headers=headers, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def check_connectivity(self) -> bool:
        try:
            resp = httpx.get(f"{self.base_url}/healthz", timeout=10)
            return resp.status_code == 200
        except httpx.HTTPError as exc:
            logger.error("Sem conectividade com a API central: %s", exc)
            return False

    # ---------------------------------------------------------------- flows --
    def enroll(self, enrollment_token: str, agent_version: str, hostname: Optional[str]) -> Dict[str, Any]:
        data = self._post(
            "/v1/agents/enroll",
            {"enrollment_token": enrollment_token, "agent_version": agent_version, "hostname": hostname},
            authenticated=False,
        )
        self.agent_id = data["agent_id"]
        self.agent_token = data["agent_token"]
        logger.info("Enrollment concluído: agent_id=%s installation=%s", data["agent_id"], data["installation_id"])
        return data

    def send_heartbeat(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._post(f"/v1/agents/{self.agent_id}/heartbeat", payload)

    def send_inventory(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._post(f"/v1/agents/{self.agent_id}/inventory", payload)

    def send_event(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._post(f"/v1/agents/{self.agent_id}/events", payload)

    def upload_backup(self, filename: str, content: bytes, encryption_provider: str = "noop") -> Dict[str, Any]:
        """Fluxo completo: request-upload -> PUT no storage -> report."""
        meta = self._post(
            f"/v1/agents/{self.agent_id}/backups/request-upload",
            {"filename": filename, "size_bytes": len(content), "encryption_provider": encryption_provider},
        )
        backup_id = meta["backup_id"]
        sha256 = hashlib.sha256(content).hexdigest()
        try:
            put = httpx.put(meta["upload_url"], content=content, timeout=120)
            put.raise_for_status()
            report = {"status": "success", "size_bytes": len(content), "sha256": sha256}
        except httpx.HTTPError as exc:
            logger.error("Falha no upload do backup: %s", exc)
            report = {"status": "failed", "error_message": f"Upload falhou: {exc}"}
        return self._post(f"/v1/agents/{self.agent_id}/backups/{backup_id}/report", report)

    def report_remote_action(
        self,
        action_id: str,
        status: str,
        result: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
    ) -> Dict[str, Any]:
        payload = {"status": status, "result": result or {}, "error_message": error_message}
        return self._post(f"/v1/agents/{self.agent_id}/remote-actions/{action_id}/report", payload)
