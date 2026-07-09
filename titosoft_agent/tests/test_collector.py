from titosoft_agent.adapters import get_adapter
from titosoft_agent.adapters.mock import MockHomeAssistantAdapter
from titosoft_agent.collector import build_heartbeat, build_inventory


def test_factory_returns_mock():
    adapter = get_adapter("mock")
    assert isinstance(adapter, MockHomeAssistantAdapter)


def test_heartbeat_payload_shape():
    payload = build_heartbeat(MockHomeAssistantAdapter(), agent_version="0.2.0")
    assert payload["status"] == "online"
    assert payload["agent_version"] == "0.2.0"
    assert payload["ha"]["core_version"]
    assert payload["ha"]["installation_type"] == "Home Assistant OS"
    assert 0 <= payload["host"]["disk_used_percent"] <= 100
    assert payload["services"]["zigbee2mqtt"] == "online"


def test_inventory_payload_shape():
    payload = build_inventory(MockHomeAssistantAdapter())
    assert len(payload["devices"]) >= 3
    assert len(payload["entities"]) >= 3
    device = payload["devices"][0]
    assert device["external_id"]
    assert device["source"] in ("home_assistant", "zigbee2mqtt", "zha", "matter", "tuya")
    entity = payload["entities"][0]
    assert "." in entity["entity_id"]


def test_mock_backup_has_content_and_size():
    backup = MockHomeAssistantAdapter().create_local_backup()
    assert backup["filename"].endswith(".tar.gz")
    assert backup["size_bytes"] == len(backup["content"]) > 0
