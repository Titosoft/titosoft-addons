"""Configuração do agente via variáveis de ambiente (12-factor).

Em produção como add-on do Home Assistant, essas variáveis virão do
options.json do Supervisor. Nunca gravar token em log.
"""
import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AgentConfig:
    api_base_url: str = field(default_factory=lambda: os.environ.get("TITOSOFT_API_URL", "http://localhost:8000"))
    agent_id: Optional[str] = field(default_factory=lambda: os.environ.get("AGENT_ID") or None)
    agent_token: Optional[str] = field(default_factory=lambda: os.environ.get("AGENT_TOKEN") or None)
    central_public_key: Optional[str] = field(default_factory=lambda: os.environ.get("CENTRAL_PUBLIC_KEY") or None)
    enrollment_token: Optional[str] = field(default_factory=lambda: os.environ.get("ENROLLMENT_TOKEN") or None)
    heartbeat_interval_seconds: int = field(default_factory=lambda: int(os.environ.get("HEARTBEAT_INTERVAL_SECONDS", "60")))
    # A cada N heartbeats envia inventário (default: 5 -> ~5 min com heartbeat de 60s)
    inventory_every_n_heartbeats: int = field(default_factory=lambda: int(os.environ.get("INVENTORY_EVERY_N_HEARTBEATS", "5")))
    # mock | rest | supervisor — adapter usado para falar com o Home Assistant
    adapter: str = field(default_factory=lambda: os.environ.get("ADAPTER", "mock"))
    ha_base_url: str = field(default_factory=lambda: os.environ.get("HA_BASE_URL", "http://homeassistant.local:8123"))
    ha_token: Optional[str] = field(default_factory=lambda: os.environ.get("HA_TOKEN") or None)
    # Backup real (via Supervisor quando ADAPTER=supervisor)
    backup_enabled: bool = field(default_factory=lambda: os.environ.get("BACKUP_ENABLED", "true").lower() == "true")
    backup_every_n_heartbeats: int = field(default_factory=lambda: int(os.environ.get("BACKUP_EVERY_N_HEARTBEATS", "1440")))
    # Passphrase de criptografia AES-256-GCM do backup (vazio = sem criptografia)
    backup_encryption_key: Optional[str] = field(default_factory=lambda: os.environ.get("BACKUP_ENCRYPTION_KEY") or None)
    # Enriquecimento Zigbee2MQTT via MQTT (Fase 2 P2.3): LQI, papel na malha
    # (Router/EndDevice), fonte de energia e last_seen do bridge/devices.
    z2m_mqtt_enabled: bool = field(default_factory=lambda: os.environ.get("Z2M_MQTT_ENABLED", "false").lower() == "true")
    z2m_mqtt_host: str = field(default_factory=lambda: os.environ.get("Z2M_MQTT_HOST", "core-mosquitto"))
    z2m_mqtt_port: int = field(default_factory=lambda: int(os.environ.get("Z2M_MQTT_PORT", "1883")))
    z2m_mqtt_username: Optional[str] = field(default_factory=lambda: os.environ.get("Z2M_MQTT_USERNAME") or None)
    z2m_mqtt_password: Optional[str] = field(default_factory=lambda: os.environ.get("Z2M_MQTT_PASSWORD") or None)
    z2m_mqtt_base_topic: str = field(default_factory=lambda: os.environ.get("Z2M_MQTT_BASE_TOPIC", "zigbee2mqtt"))
    z2m_mqtt_collect_seconds: float = field(default_factory=lambda: float(os.environ.get("Z2M_MQTT_COLLECT_SECONDS", "4")))

    @property
    def enrolled(self) -> bool:
        return bool(self.agent_id and self.agent_token)
