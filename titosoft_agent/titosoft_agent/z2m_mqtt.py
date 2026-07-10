"""Enriquecimento Zigbee2MQTT via MQTT (Fase 2 P2.3).

O registry do HA já traz os dispositivos Z2M, mas sem o diagnóstico RF que só o
Z2M expõe: papel na malha (Router/EndDevice), fonte de energia, LQI e last_seen.
Este módulo lê o tópico retido `<base>/bridge/devices` (roster) e uma janela
curta de tópicos de estado (`<base>/+`, que carregam `linkquality`/`last_seen`),
e devolve um enriquecimento por endereço IEEE.

Parsing é puro (testável sem broker); o I/O MQTT fica isolado em collect_enrichment
e degrada graciosamente: qualquer falha → dict vazio, inventário segue normal.
"""
import json
import logging
import time
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("titosoft.agent.z2m")


def _normalize_power_source(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    v = value.lower()
    if "battery" in v:
        return "battery"
    if "mains" in v or "dc source" in v:
        return "mains"
    return None


def _role_from_type(device_type: Optional[str]) -> Optional[str]:
    if not device_type:
        return None
    t = device_type.lower()
    if t == "router":
        return "router"
    if t == "enddevice":
        return "end_device"
    if t == "coordinator":
        return "coordinator"
    return None


def parse_bridge_devices(payload: List[Dict[str, Any]]) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, str]]:
    """Do array de `bridge/devices` → ({ieee: meta}, {friendly_name: ieee}).

    meta = role, power_source, vendor, model, network_address. Ignora o coordinator
    e entradas sem ieee_address.
    """
    by_ieee: Dict[str, Dict[str, Any]] = {}
    friendly_to_ieee: Dict[str, str] = {}
    for entry in payload or []:
        ieee = entry.get("ieee_address") or entry.get("ieeeAddr")
        if not ieee:
            continue
        ieee = str(ieee).lower()
        definition = entry.get("definition") or {}
        role = _role_from_type(entry.get("type"))
        by_ieee[ieee] = {
            "zigbee_role": role,
            "power_source": _normalize_power_source(entry.get("power_source")),
            "vendor": (definition.get("vendor") if isinstance(definition, dict) else None),
            "model": (definition.get("model") if isinstance(definition, dict) else None),
            "network_address": entry.get("network_address"),
        }
        friendly = entry.get("friendly_name")
        if friendly:
            friendly_to_ieee[str(friendly)] = ieee
    return by_ieee, friendly_to_ieee


def parse_state_message(
    topic: str, payload_raw: str, base_topic: str, friendly_to_ieee: Dict[str, str]
) -> Optional[Tuple[str, Dict[str, Any]]]:
    """Extrai (ieee, {lqi, last_seen}) de um tópico de estado `<base>/<friendly>`.

    Ignora tópicos de bridge e mensagens sem linkquality/last_seen.
    """
    prefix = f"{base_topic}/"
    if not topic.startswith(prefix):
        return None
    friendly = topic[len(prefix):]
    if not friendly or friendly.startswith("bridge"):
        return None
    ieee = friendly_to_ieee.get(friendly)
    if not ieee:
        return None
    try:
        data = json.loads(payload_raw)
    except (ValueError, TypeError):
        return None
    if not isinstance(data, dict):
        return None
    out: Dict[str, Any] = {}
    if isinstance(data.get("linkquality"), (int, float)):
        out["lqi"] = float(data["linkquality"])
    if data.get("last_seen"):
        out["last_seen"] = data["last_seen"]
    if not out:
        return None
    return ieee, out


def _ieee_from_ha_device(device: Dict[str, Any]) -> Optional[str]:
    """Extrai o IEEE do identifier do HA: ('mqtt', 'zigbee2mqtt_0x00158d...')."""
    for identifier in (device.get("raw_payload") or {}).get("identifiers") or []:
        if isinstance(identifier, (list, tuple)) and len(identifier) >= 2 and identifier[0] == "mqtt":
            value = str(identifier[1])
            marker = "zigbee2mqtt_"
            if marker in value:
                return value.split(marker, 1)[1].lower()
    return None


def apply_enrichment(devices: List[Dict[str, Any]], enrichment: Dict[str, Dict[str, Any]]) -> int:
    """Mescla o enriquecimento nos devices (in place). Retorna quantos foram tocados.

    Preenche power_source, lqi (se ausente) e last_seen_at diretamente (o contrato
    da API já os aceita) e guarda role/vendor/network_address em raw_payload.z2m.
    """
    if not enrichment:
        return 0
    touched = 0
    for device in devices:
        ieee = _ieee_from_ha_device(device)
        if not ieee or ieee not in enrichment:
            continue
        meta = enrichment[ieee]
        if meta.get("power_source") and not device.get("power_source"):
            device["power_source"] = meta["power_source"]
        if meta.get("lqi") is not None and device.get("lqi") is None:
            device["lqi"] = meta["lqi"]
        if meta.get("last_seen") and not device.get("last_seen_at"):
            device["last_seen_at"] = meta["last_seen"]
        raw = device.setdefault("raw_payload", {})
        if isinstance(raw, dict):
            raw["z2m"] = {
                "role": meta.get("zigbee_role"),
                "vendor": meta.get("vendor"),
                "network_address": meta.get("network_address"),
            }
        touched += 1
    return touched


def collect_enrichment(config: Any) -> Dict[str, Dict[str, Any]]:
    """Conecta ao broker, lê bridge/devices + janela de estados, devolve {ieee: meta}.

    Degrada graciosamente: sem paho-mqtt ou falha de conexão → {}.
    """
    try:
        import paho.mqtt.client as mqtt
    except ImportError:
        logger.warning("paho-mqtt ausente — enriquecimento Z2M desligado")
        return {}

    base = config.z2m_mqtt_base_topic
    collected: Dict[str, Dict[str, Any]] = {}
    friendly_to_ieee: Dict[str, str] = {}
    pending_states: List[Tuple[str, str]] = []
    got_roster = {"done": False}

    def on_connect(client, userdata, flags, rc, *args):
        client.subscribe(f"{base}/bridge/devices")
        client.subscribe(f"{base}/+")

    def on_message(client, userdata, msg):
        payload = msg.payload.decode("utf-8", "replace")
        if msg.topic == f"{base}/bridge/devices":
            try:
                by_ieee, mapping = parse_bridge_devices(json.loads(payload))
                collected.update(by_ieee)
                friendly_to_ieee.update(mapping)
                got_roster["done"] = True
            except (ValueError, TypeError):
                pass
        else:
            pending_states.append((msg.topic, payload))

    try:
        client = mqtt.Client()
        if config.z2m_mqtt_username:
            client.username_pw_set(config.z2m_mqtt_username, config.z2m_mqtt_password or "")
        client.on_connect = on_connect
        client.on_message = on_message
        client.connect(config.z2m_mqtt_host, config.z2m_mqtt_port, keepalive=30)
        client.loop_start()
        deadline = time.monotonic() + max(1.0, config.z2m_mqtt_collect_seconds)
        while time.monotonic() < deadline:
            time.sleep(0.1)
        client.loop_stop()
        client.disconnect()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Falha ao coletar enriquecimento Z2M: %s", exc)
        return {}

    # Aplica os estados retidos (linkquality/last_seen) sobre o roster
    for topic, payload in pending_states:
        parsed = parse_state_message(topic, payload, base, friendly_to_ieee)
        if parsed:
            ieee, extra = parsed
            collected.setdefault(ieee, {}).update(extra)

    logger.info("Enriquecimento Z2M: %d dispositivos", len(collected))
    return collected
