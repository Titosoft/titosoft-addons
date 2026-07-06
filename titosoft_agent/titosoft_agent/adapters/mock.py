"""Adapter mock: simula um Home Assistant OS com dispositivos Zigbee/Tuya/Matter.

Usado no desenvolvimento e no container agent-demo do docker compose.
Pequenas variações aleatórias simulam telemetria real (disco, bateria, LQI).
"""
import random
import time
from typing import Any, Dict, List

from titosoft_agent.adapters.base import HomeAssistantAdapter

_STARTED_AT = time.time() - 1_038_800  # uptime simulado ~12 dias


class MockHomeAssistantAdapter(HomeAssistantAdapter):
    def get_core_info(self) -> Dict[str, Any]:
        return {
            "core_version": "2026.6.4",
            "supervisor_version": "2026.06.2",
            "os_version": "17.1",
            "installation_type": "Home Assistant OS",
        }

    def get_host_info(self) -> Dict[str, Any]:
        return {
            "hostname": "ha-silva-alphaville",
            "arch": "aarch64",
            "uptime_seconds": int(time.time() - _STARTED_AT),
            "disk_used_percent": round(random.uniform(40, 48), 1),
            "memory_used_percent": round(random.uniform(55, 68), 1),
        }

    def get_services_status(self) -> Dict[str, str]:
        return {
            "zigbee2mqtt": "online",
            "mosquitto": "online",
            "matter_server": "unknown",
            "remote_access": "online",
        }

    def get_devices(self) -> List[Dict[str, Any]]:
        return [
            {
                "external_id": "z2m-0x00158d0001demo01",
                "source": "zigbee2mqtt",
                "protocol": "zigbee",
                "integration": "zigbee2mqtt",
                "manufacturer": "Aqara",
                "model": "Motion Sensor P1",
                "technical_model": "RTCGQ14LM",
                "name": "Sensor Movimento - Sala",
                "area": "Sala",
                "power_source": "battery",
                "battery_percent": round(random.uniform(80, 90)),
                "lqi": round(random.uniform(160, 210)),
                "availability_status": "online",
                "raw_payload": {"ieee_address": "0x00158d0001demo01"},
            },
            {
                "external_id": "z2m-0x00158d0001demo02",
                "source": "zigbee2mqtt",
                "protocol": "zigbee",
                "integration": "zigbee2mqtt",
                "manufacturer": "Sonoff",
                "model": "SNZB-04",
                "technical_model": "SNZB-04",
                "name": "Sensor Porta - Entrada",
                "area": "Entrada",
                "power_source": "battery",
                "battery_percent": round(random.uniform(10, 18)),  # gera alerta de bateria baixa
                "lqi": round(random.uniform(120, 170)),
                "availability_status": "online",
            },
            {
                "external_id": "z2m-0x00158d0001demo03",
                "source": "zigbee2mqtt",
                "protocol": "zigbee",
                "integration": "zigbee2mqtt",
                "manufacturer": "Tuya",
                "model": "ZY-M100",
                "technical_model": "TS0601",
                "name": "Presença - Cozinha",
                "area": "Cozinha",
                "power_source": "mains",
                "lqi": round(random.uniform(80, 110)),
                "availability_status": "offline",  # gera alerta de dispositivo offline
            },
            {
                "external_id": "tuya-plug-demo-01",
                "source": "tuya",
                "protocol": "wifi",
                "integration": "tuya",
                "manufacturer": "Tuya",
                "model": "Smart Plug 16A",
                "name": "Tomada - Home Office",
                "area": "Home Office",
                "power_source": "mains",
                "availability_status": "online",
            },
            {
                "external_id": "matter-lock-demo-01",
                "source": "matter",
                "protocol": "matter",
                "integration": "matter",
                "manufacturer": "Aqara",
                "model": "Door Lock U100",
                "name": "Fechadura - Porta Principal",
                "area": "Entrada",
                "power_source": "battery",
                "battery_percent": round(random.uniform(60, 70)),
                "availability_status": "online",
            },
        ]

    def get_entities(self) -> List[Dict[str, Any]]:
        return [
            {
                "entity_id": "binary_sensor.sensor_movimento_sala",
                "device_external_id": "z2m-0x00158d0001demo01",
                "domain": "binary_sensor",
                "name": "Movimento Sala",
                "state": random.choice(["on", "off"]),
            },
            {
                "entity_id": "binary_sensor.sensor_porta_entrada",
                "device_external_id": "z2m-0x00158d0001demo02",
                "domain": "binary_sensor",
                "name": "Porta Entrada",
                "state": "off",
            },
            {
                "entity_id": "switch.tomada_home_office",
                "device_external_id": "tuya-plug-demo-01",
                "domain": "switch",
                "name": "Tomada Home Office",
                "state": "on",
            },
            {
                "entity_id": "lock.fechadura_principal",
                "device_external_id": "matter-lock-demo-01",
                "domain": "lock",
                "name": "Fechadura Principal",
                "state": "locked",
            },
        ]

    def get_addons(self) -> List[Dict[str, Any]]:
        return [
            {"slug": "core_mosquitto", "name": "Mosquitto broker", "version": "6.5.1", "state": "started"},
            {"slug": "zigbee2mqtt", "name": "Zigbee2MQTT", "version": "2.3.0", "state": "started"},
            {"slug": "titosoft_agent", "name": "TitoSoft Agent", "version": "0.1.0", "state": "started"},
        ]

    def create_local_backup(self) -> Dict[str, Any]:
        """Simula criação de backup local: devolve conteúdo fake + metadados."""
        payload = random.randbytes(256 * 1024) if hasattr(random, "randbytes") else bytes(random.getrandbits(8) for _ in range(256 * 1024))
        return {
            "filename": f"ha-backup-{int(time.time())}.tar.gz",
            "content": payload,
            "size_bytes": len(payload),
        }
