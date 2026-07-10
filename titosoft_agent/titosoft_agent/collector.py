"""Monta payloads de heartbeat e inventário a partir do adapter."""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from titosoft_agent.adapters.base import HomeAssistantAdapter

logger = logging.getLogger("titosoft.agent.collector")


def build_heartbeat(adapter: HomeAssistantAdapter, agent_version: Optional[str] = None) -> Dict[str, Any]:
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "online",
        "agent_version": agent_version,
        "ha": adapter.get_core_info(),
        "host": adapter.get_host_info(),
        "services": adapter.get_services_status(),
    }


def build_inventory(adapter: HomeAssistantAdapter, config: Optional[Any] = None) -> Dict[str, Any]:
    devices = adapter.get_devices()
    # Enriquecimento Zigbee2MQTT via MQTT (opt-in). Nunca quebra o inventário.
    if config is not None and getattr(config, "z2m_mqtt_enabled", False):
        try:
            from titosoft_agent.z2m_mqtt import apply_enrichment, collect_enrichment

            enrichment = collect_enrichment(config)
            touched = apply_enrichment(devices, enrichment)
            if touched:
                logger.info("Inventário enriquecido com Z2M em %d dispositivos", touched)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Enriquecimento Z2M falhou (seguindo sem ele): %s", exc)
    return {
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "devices": devices,
        "entities": adapter.get_entities(),
    }
