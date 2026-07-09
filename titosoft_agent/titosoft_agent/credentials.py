"""Persistência das credenciais do agente após o enrollment.

Como add-on, /data é o diretório persistente do add-on. Fora dele, cai em
~/.titosoft-agent.json. Permissões 0600; o token nunca vai para log.
"""
import json
import logging
import os
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger("titosoft.agent.credentials")


def _credentials_path() -> Path:
    explicit = os.environ.get("CREDENTIALS_PATH")
    if explicit:
        return Path(explicit)
    data_dir = Path("/data")
    if data_dir.is_dir() and os.access(data_dir, os.W_OK):
        return data_dir / "agent_credentials.json"
    return Path.home() / ".titosoft-agent.json"


def load_credentials() -> Tuple[Optional[str], Optional[str], Optional[str]]:
    path = _credentials_path()
    if not path.exists():
        return None, None, None
    try:
        data = json.loads(path.read_text())
        return data.get("agent_id"), data.get("agent_token"), data.get("central_public_key")
    except (json.JSONDecodeError, OSError) as exc:
        logger.error("Falha ao ler credenciais em %s: %s", path, exc)
        return None, None, None


def save_credentials(agent_id: str, agent_token: str, central_public_key: Optional[str] = None) -> None:
    path = _credentials_path()
    payload = {"agent_id": agent_id, "agent_token": agent_token}
    if central_public_key:
        payload["central_public_key"] = central_public_key
    path.write_text(json.dumps(payload))
    os.chmod(path, 0o600)
    logger.info("Credenciais do agente salvas em %s", path)
