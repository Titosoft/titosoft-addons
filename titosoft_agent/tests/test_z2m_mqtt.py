import json

from titosoft_agent.z2m_mqtt import (
    apply_enrichment,
    parse_bridge_devices,
    parse_state_message,
)

BRIDGE_DEVICES = [
    {"type": "Coordinator", "ieee_address": "0x00124b0000000000", "friendly_name": "Coordinator"},
    {
        "type": "Router",
        "ieee_address": "0x00158D0001ABCD12",
        "friendly_name": "sala_interruptor",
        "power_source": "Mains (single phase)",
        "network_address": 12345,
        "definition": {"vendor": "Tuya", "model": "TS0011"},
    },
    {
        "type": "EndDevice",
        "ieee_address": "0x00158d0001beef34",
        "friendly_name": "quarto_sensor",
        "power_source": "Battery",
        "definition": {"vendor": "Aqara", "model": "WSDCGQ11LM"},
    },
    {"ieee_address": None, "friendly_name": "sem_ieee"},  # ignorado
]


def test_parse_bridge_devices_roles_and_power():
    by_ieee, friendly = parse_bridge_devices(BRIDGE_DEVICES)
    router = by_ieee["0x00158d0001abcd12"]  # normalizado p/ minúsculo
    assert router["zigbee_role"] == "router"
    assert router["power_source"] == "mains"
    assert router["vendor"] == "Tuya"
    assert by_ieee["0x00158d0001beef34"]["zigbee_role"] == "end_device"
    assert by_ieee["0x00158d0001beef34"]["power_source"] == "battery"
    assert friendly["sala_interruptor"] == "0x00158d0001abcd12"
    assert "sem_ieee" not in friendly


def test_parse_state_message_extracts_lqi_and_last_seen():
    _, friendly = parse_bridge_devices(BRIDGE_DEVICES)
    parsed = parse_state_message(
        "zigbee2mqtt/sala_interruptor",
        json.dumps({"state": "ON", "linkquality": 87, "last_seen": "2026-07-10T12:00:00Z"}),
        "zigbee2mqtt",
        friendly,
    )
    assert parsed is not None
    ieee, extra = parsed
    assert ieee == "0x00158d0001abcd12"
    assert extra["lqi"] == 87.0
    assert extra["last_seen"] == "2026-07-10T12:00:00Z"


def test_parse_state_message_ignores_bridge_and_unknown():
    _, friendly = parse_bridge_devices(BRIDGE_DEVICES)
    assert parse_state_message("zigbee2mqtt/bridge/state", "online", "zigbee2mqtt", friendly) is None
    assert parse_state_message("zigbee2mqtt/desconhecido", "{}", "zigbee2mqtt", friendly) is None
    assert parse_state_message("outro/topico", "{}", "zigbee2mqtt", friendly) is None


def test_apply_enrichment_merges_into_ha_devices():
    by_ieee, _ = parse_bridge_devices(BRIDGE_DEVICES)
    by_ieee["0x00158d0001abcd12"]["lqi"] = 87.0
    devices = [
        {
            "external_id": "dev-1",
            "power_source": None,
            "lqi": None,
            "raw_payload": {"identifiers": [["mqtt", "zigbee2mqtt_0x00158D0001ABCD12"]]},
        },
        {  # dispositivo não-Z2M: intocado
            "external_id": "dev-2",
            "raw_payload": {"identifiers": [["hue", "abc"]]},
        },
    ]
    touched = apply_enrichment(devices, by_ieee)
    assert touched == 1
    assert devices[0]["power_source"] == "mains"
    assert devices[0]["lqi"] == 87.0
    assert devices[0]["raw_payload"]["z2m"]["role"] == "router"
    assert "z2m" not in devices[1]["raw_payload"]


def test_apply_enrichment_does_not_override_existing_lqi():
    by_ieee, _ = parse_bridge_devices(BRIDGE_DEVICES)
    by_ieee["0x00158d0001abcd12"]["lqi"] = 30.0
    devices = [{
        "external_id": "dev-1",
        "lqi": 99.0,  # já veio do registry → não sobrescreve
        "raw_payload": {"identifiers": [["mqtt", "zigbee2mqtt_0x00158d0001abcd12"]]},
    }]
    apply_enrichment(devices, by_ieee)
    assert devices[0]["lqi"] == 99.0


def test_empty_enrichment_is_noop():
    devices = [{"external_id": "x", "raw_payload": {}}]
    assert apply_enrichment(devices, {}) == 0
