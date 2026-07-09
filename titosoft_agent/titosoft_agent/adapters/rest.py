"""Adapter REST + WebSocket do Home Assistant (funcional).

Coleta real: /api/config, /api/states (REST) e device/entity/area registry
(WebSocket). Funciona contra qualquer HA (OS, Container, Core) com um
long-lived access token. Backup real requer Supervisor (ver supervisor.py).

Docs: https://developers.home-assistant.io/docs/api/rest/
      https://developers.home-assistant.io/docs/api/websocket/
"""
from typing import Any, Dict, List, Optional

import httpx

from titosoft_agent.adapters.base import HomeAssistantAdapter
from titosoft_agent.ha_ws import HomeAssistantWebSocket
from titosoft_agent.normalize import normalize_inventory

REGISTRY_COMMANDS = [
    "config/device_registry/list",
    "config/entity_registry/list",
    "config/area_registry/list",
]


class RestApiAdapter(HomeAssistantAdapter):
    def __init__(self, ha_base_url: str, ha_token: Optional[str] = None, **_: Any) -> None:
        if not ha_token:
            raise ValueError("Adapter rest requer HA_TOKEN (long-lived access token)")
        self.base_url = ha_base_url.rstrip("/")
        self.token = ha_token
        self.headers = {"Authorization": f"Bearer {ha_token}"}
        self._ws = HomeAssistantWebSocket(self.base_url, ha_token)
        self._inventory_cache: Optional[Dict[str, List[Dict[str, Any]]]] = None

    def _get(self, path: str) -> Any:
        resp = httpx.get(f"{self.base_url}{path}", headers=self.headers, timeout=20)
        resp.raise_for_status()
        return resp.json()

    def _collect_inventory(self) -> Dict[str, List[Dict[str, Any]]]:
        """Uma coleta por ciclo: registries via WS + estados via REST."""
        registries = self._ws.fetch(REGISTRY_COMMANDS)
        states = self._get("/api/states")
        devices, entities = normalize_inventory(
            registries["config/device_registry/list"],
            registries["config/entity_registry/list"],
            registries["config/area_registry/list"],
            states,
        )
        self._inventory_cache = {"devices": devices, "entities": entities}
        return self._inventory_cache

    # ------------------------------------------------------------ contrato --
    def get_core_info(self) -> Dict[str, Any]:
        config = self._get("/api/config")
        return {
            "core_version": config.get("version"),
            "supervisor_version": None,  # via Supervisor API (supervisor.py)
            "os_version": None,
            "installation_type": "Home Assistant Core/Container",
        }

    def get_host_info(self) -> Dict[str, Any]:
        config = self._get("/api/config")
        return {
            "hostname": config.get("location_name"),
            "arch": None,
            "uptime_seconds": None,
            "disk_used_percent": None,
            "memory_used_percent": None,
        }

    def get_services_status(self) -> Dict[str, str]:
        """Infere serviços chave a partir das entidades disponíveis."""
        try:
            states = self._get("/api/states")
        except httpx.HTTPError:
            return {}
        services: Dict[str, str] = {}
        z2m_states = [s for s in states if s["entity_id"].startswith(("sensor.zigbee2mqtt_bridge", "binary_sensor.zigbee2mqtt_bridge"))]
        if z2m_states:
            connected = any(s.get("state") in ("on", "online", "connected") for s in z2m_states)
            services["zigbee2mqtt"] = "online" if connected else "offline"
        return services

    def get_devices(self) -> List[Dict[str, Any]]:
        return self._collect_inventory()["devices"]

    def get_entities(self) -> List[Dict[str, Any]]:
        if self._inventory_cache is None:
            self._collect_inventory()
        entities = self._inventory_cache["entities"]
        self._inventory_cache = None  # invalida para o próximo ciclo
        return entities

    def get_addons(self) -> List[Dict[str, Any]]:
        return []  # sem Supervisor não há add-ons

    def create_local_backup(self) -> Dict[str, Any]:
        raise NotImplementedError(
            "Backup com download do arquivo requer Supervisor (HAOS). Use ADAPTER=supervisor."
        )

    def restart_addon(self, slug: str) -> Dict[str, Any]:
        raise NotImplementedError(
            f"Restart do add-on {slug} requer Supervisor (HAOS). Use ADAPTER=supervisor."
        )
