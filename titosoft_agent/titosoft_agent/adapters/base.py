"""Contrato entre o agente e o Home Assistant local.

Implementações previstas:
- MockHomeAssistantAdapter (Fase 1): dados simulados p/ desenvolvimento.
- RestApiAdapter (Fase 1, parcial): HA REST API (/api/config, /api/states).
- SupervisorApiAdapter (Fase 2): Supervisor API (host, add-ons, backups reais).
- WebSocket API (Fase 2): estados/eventos em tempo real.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List


class HomeAssistantAdapter(ABC):
    @abstractmethod
    def get_core_info(self) -> Dict[str, Any]:
        """Versões do Core/Supervisor/OS e tipo de instalação."""

    @abstractmethod
    def get_host_info(self) -> Dict[str, Any]:
        """Hostname, arquitetura, uptime, disco e memória."""

    @abstractmethod
    def get_services_status(self) -> Dict[str, str]:
        """Status de serviços chave: zigbee2mqtt, mosquitto, matter, remote_access."""

    @abstractmethod
    def get_devices(self) -> List[Dict[str, Any]]:
        """Dispositivos no formato do contrato InventoryDevice da API."""

    @abstractmethod
    def get_entities(self) -> List[Dict[str, Any]]:
        """Entidades no formato do contrato InventoryEntity da API."""

    @abstractmethod
    def get_addons(self) -> List[Dict[str, Any]]:
        """Add-ons instalados (via Supervisor quando disponível)."""

    @abstractmethod
    def create_local_backup(self) -> Dict[str, Any]:
        """Dispara backup local. Fase 1: simulado; Fase 2: Supervisor API."""

    @abstractmethod
    def restart_addon(self, slug: str) -> Dict[str, Any]:
        """Reinicia um add-on permitido via Supervisor API."""

    @abstractmethod
    def update_core(self, version: str) -> Dict[str, Any]:
        """Atualiza o HA Core para uma versão (rollout canário, Fase 2)."""
