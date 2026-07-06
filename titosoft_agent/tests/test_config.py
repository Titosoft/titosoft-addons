from titosoft_agent.config import AgentConfig


def test_defaults(monkeypatch):
    for var in ("TITOSOFT_API_URL", "AGENT_ID", "AGENT_TOKEN", "ENROLLMENT_TOKEN"):
        monkeypatch.delenv(var, raising=False)
    config = AgentConfig()
    assert config.api_base_url == "http://localhost:8000"
    assert config.heartbeat_interval_seconds == 60
    assert config.adapter == "mock"
    assert not config.enrolled


def test_enrolled_when_credentials_present(monkeypatch):
    monkeypatch.setenv("AGENT_ID", "abc")
    monkeypatch.setenv("AGENT_TOKEN", "tok")
    assert AgentConfig().enrolled
