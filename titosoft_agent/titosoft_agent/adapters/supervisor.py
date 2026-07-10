"""Adapter Supervisor API (funcional) — para o agente rodando como add-on em HAOS.

Dentro de um add-on o Supervisor injeta SUPERVISOR_TOKEN e expõe:
- http://supervisor/...            -> Supervisor API (host, addons, backups)
- http://supervisor/core/api/...   -> proxy para a REST API do Core
- ws://supervisor/core/websocket   -> proxy para a WebSocket API do Core

Inventário reutiliza a mesma normalização do RestApiAdapter via proxies.
Docs: https://developers.home-assistant.io/docs/api/supervisor/endpoints/
"""
import logging
import os
import time
from typing import Any, Dict, List, Optional

import httpx

from titosoft_agent.adapters.base import HomeAssistantAdapter
from titosoft_agent.ha_ws import HomeAssistantWebSocket
from titosoft_agent.normalize import normalize_inventory
from titosoft_agent.adapters.rest import REGISTRY_COMMANDS

logger = logging.getLogger("titosoft.agent.supervisor")

# slugs de add-ons monitorados -> nome do serviço no heartbeat
SERVICE_ADDONS = {
    "zigbee2mqtt": "zigbee2mqtt",
    "core_mosquitto": "mosquitto",
    "core_matter_server": "matter_server",
}


class SupervisorApiAdapter(HomeAssistantAdapter):
    def __init__(
        self,
        supervisor_url: str = "http://supervisor",
        supervisor_token: Optional[str] = None,
        backup_timeout_seconds: int = 1800,
        **_: Any,
    ) -> None:
        self.base_url = supervisor_url.rstrip("/")
        self.token = supervisor_token or os.environ.get("SUPERVISOR_TOKEN")
        if not self.token:
            raise ValueError("SUPERVISOR_TOKEN ausente — este adapter só roda dentro de um add-on")
        self.headers = {"Authorization": f"Bearer {self.token}"}
        self.backup_timeout = backup_timeout_seconds
        self._ws = HomeAssistantWebSocket(f"{self.base_url}/core", self.token)
        self._inventory_cache: Optional[Dict[str, List[Dict[str, Any]]]] = None

    # ------------------------------------------------------------- helpers --
    def _get(self, path: str, timeout: int = 30) -> Dict[str, Any]:
        resp = httpx.get(f"{self.base_url}{path}", headers=self.headers, timeout=timeout)
        resp.raise_for_status()
        return resp.json().get("data", {})

    def _post(self, path: str, json: Optional[Dict[str, Any]] = None, timeout: int = 60) -> Dict[str, Any]:
        resp = httpx.post(f"{self.base_url}{path}", headers=self.headers, json=json, timeout=timeout)
        resp.raise_for_status()
        body = resp.json()
        if body.get("result") not in (None, "ok"):
            raise RuntimeError(f"Supervisor {path} devolveu: {body}")
        return body.get("data", {})

    def _core_get(self, path: str) -> Any:
        resp = httpx.get(f"{self.base_url}/core/api{path}", headers=self.headers, timeout=30)
        resp.raise_for_status()
        return resp.json()

    # ------------------------------------------------------------ contrato --
    def get_core_info(self) -> Dict[str, Any]:
        core = self._get("/core/info")
        supervisor = self._get("/supervisor/info")
        os_info = self._get("/os/info")
        return {
            "core_version": core.get("version"),
            "supervisor_version": supervisor.get("version"),
            "os_version": os_info.get("version"),
            "installation_type": "Home Assistant OS",
        }

    def get_host_info(self) -> Dict[str, Any]:
        host = self._get("/host/info")
        stats = {}
        try:
            stats = self._get("/core/stats")
        except httpx.HTTPError:
            logger.warning("Sem /core/stats — memória indisponível")
        disk_total = host.get("disk_total") or 0
        disk_used = host.get("disk_used") or 0
        return {
            "hostname": host.get("hostname"),
            "arch": None,
            "uptime_seconds": int(host["boot_timestamp"] and (time.time() - host["boot_timestamp"] / 1_000_000)) if host.get("boot_timestamp") else None,
            "disk_used_percent": round(disk_used / disk_total * 100, 1) if disk_total else None,
            "memory_used_percent": stats.get("memory_percent"),
        }

    def get_services_status(self) -> Dict[str, str]:
        services: Dict[str, str] = {}
        try:
            addons = self._get("/addons").get("addons", [])
        except httpx.HTTPError:
            return services
        by_slug = {a.get("slug"): a for a in addons}
        for slug, service_name in SERVICE_ADDONS.items():
            addon = by_slug.get(slug)
            if addon is not None:
                services[service_name] = "online" if addon.get("state") == "started" else "offline"
        return services

    def _collect_inventory(self) -> Dict[str, List[Dict[str, Any]]]:
        registries = self._ws.fetch(REGISTRY_COMMANDS)
        states = self._core_get("/states")
        devices, entities = normalize_inventory(
            registries["config/device_registry/list"],
            registries["config/entity_registry/list"],
            registries["config/area_registry/list"],
            states,
        )
        self._inventory_cache = {"devices": devices, "entities": entities}
        return self._inventory_cache

    def get_devices(self) -> List[Dict[str, Any]]:
        return self._collect_inventory()["devices"]

    def get_entities(self) -> List[Dict[str, Any]]:
        if self._inventory_cache is None:
            self._collect_inventory()
        entities = self._inventory_cache["entities"]
        self._inventory_cache = None
        return entities

    def get_addons(self) -> List[Dict[str, Any]]:
        addons = self._get("/addons").get("addons", [])
        return [
            {"slug": a.get("slug"), "name": a.get("name"), "version": a.get("version"), "state": a.get("state")}
            for a in addons
        ]

    def create_local_backup(self) -> Dict[str, Any]:
        """Backup FULL real via Supervisor + download do arquivo .tar."""
        name = f"titosoft-{time.strftime('%Y%m%d-%H%M%S')}"
        logger.info("Criando backup full '%s' (pode demorar vários minutos)...", name)
        data = self._post("/backups/new/full", {"name": name}, timeout=self.backup_timeout)
        slug = data.get("slug")
        if not slug:
            raise RuntimeError(f"Supervisor não devolveu slug do backup: {data}")

        logger.info("Baixando backup %s...", slug)
        resp = httpx.get(
            f"{self.base_url}/backups/{slug}/download",
            headers=self.headers,
            timeout=self.backup_timeout,
        )
        resp.raise_for_status()
        content = resp.content
        return {"filename": f"{name}.tar", "content": content, "size_bytes": len(content), "slug": slug}

    def restart_addon(self, slug: str) -> Dict[str, Any]:
        if slug not in SERVICE_ADDONS:
            raise ValueError(f"Add-on não permitido para restart remoto: {slug}")
        self._post(f"/addons/{slug}/restart", timeout=120)
        return {"slug": slug, "status": "restart_requested"}

    def update_core(self, version: str) -> Dict[str, Any]:
        """Atualiza o HA Core via Supervisor. O Supervisor faz backup parcial do
        Core por padrão; o backup full já foi disparado antes desta ação."""
        logger.info("Atualizando HA Core para %s (pode reiniciar o Core)...", version)
        self._post("/core/update", {"version": version}, timeout=self.backup_timeout)
        return {"version": version, "status": "update_requested"}
