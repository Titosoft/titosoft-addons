"""Cliente WebSocket do Home Assistant (chamadas one-shot, síncronas).

Usado para ler os registries (devices, entities, áreas), que não existem na
REST API. Docs: https://developers.home-assistant.io/docs/api/websocket/
"""
import json
import logging
from typing import Any, Dict, List

import websocket

logger = logging.getLogger("titosoft.agent.ws")


class HomeAssistantWebSocket:
    def __init__(self, base_url: str, token: str, timeout: int = 30) -> None:
        # http(s)://host:8123 -> ws(s)://host:8123/api/websocket
        ws_url = base_url.rstrip("/")
        if ws_url.startswith("https://"):
            ws_url = "wss://" + ws_url[len("https://"):]
        elif ws_url.startswith("http://"):
            ws_url = "ws://" + ws_url[len("http://"):]
        self.url = f"{ws_url}/api/websocket"
        self.token = token
        self.timeout = timeout

    def fetch(self, commands: List[str]) -> Dict[str, Any]:
        """Autentica e executa uma lista de comandos, ex.: config/device_registry/list."""
        ws = websocket.create_connection(self.url, timeout=self.timeout)
        try:
            first = json.loads(ws.recv())
            if first.get("type") == "auth_required":
                ws.send(json.dumps({"type": "auth", "access_token": self.token}))
                auth = json.loads(ws.recv())
                if auth.get("type") != "auth_ok":
                    raise RuntimeError(f"Autenticação WebSocket falhou: {auth}")

            results: Dict[str, Any] = {}
            for idx, command in enumerate(commands, start=1):
                ws.send(json.dumps({"id": idx, "type": command}))
            pending = set(range(1, len(commands) + 1))
            while pending:
                msg = json.loads(ws.recv())
                msg_id = msg.get("id")
                if msg_id in pending and msg.get("type") == "result":
                    if not msg.get("success"):
                        raise RuntimeError(f"Comando {commands[msg_id - 1]} falhou: {msg.get('error')}")
                    results[commands[msg_id - 1]] = msg.get("result")
                    pending.discard(msg_id)
            return results
        finally:
            ws.close()
