"""Normalização dos registries reais do HA (fixtures no formato da WebSocket API)."""
from titosoft_agent.normalize import normalize_inventory

DEVICE_REGISTRY = [
    {
        "id": "dev-z2m-1",
        "name": "0x00158d0001aabb01",
        "name_by_user": "Sensor Porta Entrada",
        "manufacturer": "SONOFF",
        "model": "SNZB-04",
        "sw_version": "1.0.6",
        "area_id": "entrada",
        "identifiers": [["mqtt", "zigbee2mqtt_0x00158d0001aabb01"]],
        "connections": [],
    },
    {
        "id": "dev-zha-1",
        "name": "Aqara Motion P1",
        "name_by_user": None,
        "manufacturer": "Aqara",
        "model": "RTCGQ14LM",
        "sw_version": None,
        "area_id": "sala",
        "identifiers": [["zha", "00:15:8d:00:01:aa:bb:02"]],
        "connections": [["zigbee", "00:15:8d:00:01:aa:bb:02"]],
    },
    {
        "id": "dev-tuya-1",
        "name": "Smart Plug",
        "name_by_user": "Tomada Escritório",
        "manufacturer": "Tuya",
        "model": "Plug 16A",
        "sw_version": "3.1",
        "area_id": None,
        "identifiers": [["tuya", "abc123"]],
        "connections": [],
    },
]

ENTITY_REGISTRY = [
    {"entity_id": "binary_sensor.porta_entrada", "device_id": "dev-z2m-1", "platform": "mqtt", "name": None, "original_name": "Porta Entrada"},
    {"entity_id": "sensor.porta_entrada_battery", "device_id": "dev-z2m-1", "platform": "mqtt", "name": None, "original_name": "Bateria"},
    {"entity_id": "sensor.porta_entrada_linkquality", "device_id": "dev-z2m-1", "platform": "mqtt", "name": None, "original_name": "LQI"},
    {"entity_id": "binary_sensor.movimento_sala", "device_id": "dev-zha-1", "platform": "zha", "name": None, "original_name": "Movimento"},
    {"entity_id": "switch.tomada_escritorio", "device_id": "dev-tuya-1", "platform": "tuya", "name": None, "original_name": "Tomada"},
]

AREA_REGISTRY = [
    {"area_id": "entrada", "name": "Entrada"},
    {"area_id": "sala", "name": "Sala"},
]

STATES = [
    {"entity_id": "binary_sensor.porta_entrada", "state": "off", "attributes": {}},
    {"entity_id": "sensor.porta_entrada_battery", "state": "17", "attributes": {"device_class": "battery", "unit_of_measurement": "%"}},
    {"entity_id": "sensor.porta_entrada_linkquality", "state": "144", "attributes": {"unit_of_measurement": "lqi"}},
    {"entity_id": "binary_sensor.movimento_sala", "state": "unavailable", "attributes": {}},
    {"entity_id": "switch.tomada_escritorio", "state": "on", "attributes": {}},
]


def test_normalize_devices():
    devices, entities = normalize_inventory(DEVICE_REGISTRY, ENTITY_REGISTRY, AREA_REGISTRY, STATES)
    by_id = {d["external_id"]: d for d in devices}

    z2m = by_id["dev-z2m-1"]
    assert z2m["integration"] == "zigbee2mqtt"
    assert z2m["protocol"] == "zigbee"
    assert z2m["source"] == "zigbee2mqtt"
    assert z2m["name"] == "Sensor Porta Entrada"
    assert z2m["area"] == "Entrada"
    assert z2m["battery_percent"] == 17.0
    assert z2m["lqi"] == 144.0
    assert z2m["availability_status"] == "online"

    zha = by_id["dev-zha-1"]
    assert zha["integration"] == "zha"
    assert zha["protocol"] == "zigbee"
    assert zha["availability_status"] == "offline"  # única entidade unavailable
    assert zha["area"] == "Sala"

    tuya = by_id["dev-tuya-1"]
    assert tuya["integration"] == "tuya"
    assert tuya["source"] == "tuya"


def test_normalize_entities():
    _, entities = normalize_inventory(DEVICE_REGISTRY, ENTITY_REGISTRY, AREA_REGISTRY, STATES)
    assert len(entities) == 5
    battery = next(e for e in entities if e["entity_id"] == "sensor.porta_entrada_battery")
    assert battery["device_external_id"] == "dev-z2m-1"
    assert battery["state"] == "17"
    assert battery["domain"] == "sensor"


def test_service_devices_and_orphan_entities_excluded():
    """Add-ons/Supervisor/Backup (entry_type=service) e entidades órfãs de sistema
    não devem entrar no inventário."""
    devices_reg = DEVICE_REGISTRY + [
        {"id": "dev-supervisor", "name": "Supervisor", "entry_type": "service", "identifiers": [["hassio", "supervisor"]]},
        {"id": "dev-addon-backup", "name": "Backup", "entry_type": "service", "identifiers": [["hassio", "core_backup"]]},
    ]
    entities_reg = ENTITY_REGISTRY + [
        {"entity_id": "update.backup_update", "device_id": "dev-addon-backup", "platform": "hassio", "original_name": "Backup"},
        {"entity_id": "sun.sun", "device_id": None, "platform": "sun", "original_name": "Sun"},
        {"entity_id": "automation.luzes_noite", "device_id": None, "platform": "automation", "original_name": "Luzes"},
    ]
    devices, entities = normalize_inventory(devices_reg, entities_reg, AREA_REGISTRY, STATES)

    ids = {d["external_id"] for d in devices}
    assert "dev-supervisor" not in ids
    assert "dev-addon-backup" not in ids
    assert ids == {"dev-z2m-1", "dev-zha-1", "dev-tuya-1"}  # só dispositivos reais

    ent_ids = {e["entity_id"] for e in entities}
    assert "update.backup_update" not in ent_ids
    assert "sun.sun" not in ent_ids
    assert "automation.luzes_noite" not in ent_ids
    assert len(entities) == 5  # só as dos 3 dispositivos reais
