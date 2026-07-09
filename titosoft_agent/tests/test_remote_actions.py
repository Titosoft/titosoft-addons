import base64
import json
from datetime import datetime, timedelta, timezone

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from titosoft_agent.remote_actions import verify_action


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _canonical(payload):
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _command(action_type="restart_addon", payload=None):
    private = Ed25519PrivateKey.generate()
    public = _b64(private.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw))
    signed = {
        "id": "action-1",
        "installation_id": "inst-1",
        "action_type": action_type,
        "payload": payload or {"slug": "zigbee2mqtt"},
        "issued_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat(),
        "version": "1.0",
    }
    return {
        "public": public,
        "command": {
            "id": "action-1",
            "action_type": action_type,
            "payload": signed["payload"],
            "signed_payload": signed,
            "signature": _b64(private.sign(_canonical(signed))),
        },
    }


def test_verify_action_accepts_signed_allowlisted_command():
    data = _command()
    action = verify_action(data["command"], data["public"])
    assert action["id"] == "action-1"
    assert action["action_type"] == "restart_addon"
    assert action["payload"] == {"slug": "zigbee2mqtt"}


def test_verify_action_rejects_tampered_payload():
    data = _command()
    data["command"]["signed_payload"]["payload"]["slug"] = "ssh"
    with pytest.raises(ValueError):
        verify_action(data["command"], data["public"])
