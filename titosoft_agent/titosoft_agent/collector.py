"""Monta payloads de heartbeat e inventário a partir do adapter."""
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from titosoft_agent.adapters.base import HomeAssistantAdapter


def build_heartbeat(adapter: HomeAssistantAdapter, agent_version: Optional[str] = None) -> Dict[str, Any]:
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "online",
        "agent_version": agent_version,
        "ha": adapter.get_core_info(),
        "host": adapter.get_host_info(),
        "services": adapter.get_services_status(),
    }


def build_inventory(adapter: HomeAssistantAdapter) -> Dict[str, Any]:
    return {
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "devices": adapter.get_devices(),
        "entities": adapter.get_entities(),
    }
