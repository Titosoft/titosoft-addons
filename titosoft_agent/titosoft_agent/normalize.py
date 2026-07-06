"""Normalização dos registries do Home Assistant para o contrato da API central.

Função pura (testável sem rede): recebe device_registry, entity_registry,
area_registry e states e devolve payloads de InventoryDevice/InventoryEntity.
"""
from typing import Any, Dict, List, Optional, Tuple

# platform (entity_registry) -> (protocol, integration)
PLATFORM_MAP: Dict[str, Tuple[str, str]] = {
    "zha": ("zigbee", "zha"),
    "mqtt": ("mqtt", "mqtt"),
    "matter": ("matter", "matter"),
    "tuya": ("tuya_cloud", "tuya"),
    "hue": ("zigbee", "hue"),
    "esphome": ("wifi", "esphome"),
    "zwave_js": ("zwave", "zwave_js"),
    "tasmota": ("wifi", "tasmota"),
    "shelly": ("wifi", "shelly"),
}

INTEGRATION_TO_SOURCE = {
    "zha": "zha",
    "zigbee2mqtt": "zigbee2mqtt",
    "matter": "matter",
    "tuya": "tuya",
}


def _is_zigbee2mqtt_device(device: Dict[str, Any]) -> bool:
    for identifier in device.get("identifiers") or []:
        if isinstance(identifier, (list, tuple)) and len(identifier) >= 2:
            if identifier[0] == "mqtt" and "zigbee2mqtt" in str(identifier[1]):
                return True
    return False


def _infer_protocol_integration(device: Dict[str, Any], platforms: List[str]) -> Tuple[str, Optional[str]]:
    if _is_zigbee2mqtt_device(device):
        return "zigbee", "zigbee2mqtt"
    for platform in platforms:
        if platform in PLATFORM_MAP:
            return PLATFORM_MAP[platform]
    return "unknown", platforms[0] if platforms else None


def normalize_inventory(
    device_registry: List[Dict[str, Any]],
    entity_registry: List[Dict[str, Any]],
    area_registry: List[Dict[str, Any]],
    states: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    areas = {a["area_id"]: a.get("name") for a in area_registry}
    states_by_entity = {s["entity_id"]: s for s in states}
    entities_by_device: Dict[str, List[Dict[str, Any]]] = {}
    for entry in entity_registry:
        if entry.get("device_id"):
            entities_by_device.setdefault(entry["device_id"], []).append(entry)

    devices_out: List[Dict[str, Any]] = []
    for device in device_registry:
        device_id = device["id"]
        entries = entities_by_device.get(device_id, [])
        platforms = sorted({e.get("platform") for e in entries if e.get("platform")})
        protocol, integration = _infer_protocol_integration(device, platforms)

        battery: Optional[float] = None
        rssi: Optional[float] = None
        lqi: Optional[float] = None
        any_available = False
        has_state = False
        for entry in entries:
            state = states_by_entity.get(entry["entity_id"])
            if not state:
                continue
            has_state = True
            if state.get("state") not in ("unavailable", "unknown"):
                any_available = True
            attrs = state.get("attributes") or {}
            if attrs.get("device_class") == "battery":
                try:
                    battery = float(state.get("state"))
                except (TypeError, ValueError):
                    pass
            if entry["entity_id"].endswith("_linkquality") or attrs.get("unit_of_measurement") == "lqi":
                try:
                    lqi = float(state.get("state"))
                except (TypeError, ValueError):
                    pass
            if "rssi" in attrs and isinstance(attrs["rssi"], (int, float)):
                rssi = float(attrs["rssi"])

        availability = "online" if any_available else ("offline" if has_state else "unknown")

        devices_out.append(
            {
                "external_id": device_id,
                "source": INTEGRATION_TO_SOURCE.get(integration or "", "home_assistant"),
                "protocol": protocol,
                "integration": integration,
                "manufacturer": device.get("manufacturer"),
                "model": device.get("model"),
                "technical_model": device.get("model_id") or device.get("hw_version"),
                "name": device.get("name_by_user") or device.get("name"),
                "area": areas.get(device.get("area_id")),
                "firmware_version": device.get("sw_version"),
                "battery_percent": battery,
                "lqi": lqi,
                "rssi": rssi,
                "availability_status": availability,
                "raw_payload": {
                    "identifiers": device.get("identifiers"),
                    "connections": device.get("connections"),
                    "via_device_id": device.get("via_device_id"),
                },
            }
        )

    entities_out: List[Dict[str, Any]] = []
    for entry in entity_registry:
        state = states_by_entity.get(entry["entity_id"], {})
        entities_out.append(
            {
                "entity_id": entry["entity_id"],
                "device_external_id": entry.get("device_id"),
                "domain": entry["entity_id"].split(".")[0],
                "name": entry.get("name") or entry.get("original_name"),
                "state": state.get("state"),
                "attributes": state.get("attributes"),
            }
        )
    return devices_out, entities_out
