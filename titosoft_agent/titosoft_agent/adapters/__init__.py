from titosoft_agent.adapters.base import HomeAssistantAdapter
from titosoft_agent.adapters.mock import MockHomeAssistantAdapter


def get_adapter(name: str, **kwargs) -> HomeAssistantAdapter:
    """Fábrica de adapters. Fase 1: mock funcional; rest/supervisor esqueletos."""
    if name == "mock":
        return MockHomeAssistantAdapter()
    if name == "rest":
        from titosoft_agent.adapters.rest import RestApiAdapter

        return RestApiAdapter(**kwargs)
    if name == "supervisor":
        from titosoft_agent.adapters.supervisor import SupervisorApiAdapter

        return SupervisorApiAdapter(**kwargs)
    raise ValueError(f"Adapter desconhecido: {name}")
