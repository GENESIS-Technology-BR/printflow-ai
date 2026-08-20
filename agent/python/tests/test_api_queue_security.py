from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from types import SimpleNamespace

from api.client import PrintflowApiClient


def _client(tmp_path: Path) -> PrintflowApiClient:
    return PrintflowApiClient(
        api_url="https://example.invalid",
        agent_token="current-secret-token",
        logger=logging.getLogger("test-api-queue-security"),
        queue_directory=tmp_path / "queue",
    )


def test_queue_never_persists_agent_token(tmp_path: Path):
    client = _client(tmp_path)
    queue_file = client.save_to_queue(
        payload={
            "ip": "10.2.128.27",
            "agent_token": "secret-that-must-not-be-written",
        },
        reason="offline",
    )

    raw = queue_file.read_text(encoding="utf-8")
    content = json.loads(raw)

    assert "secret-that-must-not-be-written" not in raw
    assert "agent_token" not in content["payload"]


def test_retry_sanitizes_legacy_queue_and_uses_current_token(
    tmp_path: Path,
    monkeypatch,
):
    client = _client(tmp_path)
    legacy_file = client.queue_directory / "legacy.json"
    legacy_file.write_text(
        json.dumps(
            {
                "reason": "offline",
                "created_at_unix": int(time.time() * 1000),
                "payload": {
                    "ip": "10.2.128.27",
                    "agent_token": "obsolete-secret-token",
                },
            }
        ),
        encoding="utf-8",
    )
    posted = {}

    def fake_post(_url, json, timeout):
        posted.update(json)
        return SimpleNamespace(status_code=503)

    monkeypatch.setattr("api.client.requests.post", fake_post)

    result = client.retry_queue()

    assert result == {"processed": 1, "success": 0, "failed": 1}
    assert posted["agent_token"] == "current-secret-token"
    assert "agent_token" not in json.loads(
        legacy_file.read_text(encoding="utf-8")
    )["payload"]


def test_health_check_requires_real_health_success(tmp_path, monkeypatch):
    client = _client(tmp_path)

    monkeypatch.setattr(
        "api.client.requests.get",
        lambda url, timeout: SimpleNamespace(status_code=405),
    )

    assert client.health_check() is False


def test_expired_queue_item_is_removed(tmp_path: Path):
    client = _client(tmp_path)
    expired = client.queue_directory / "expired.json"
    expired.write_text(
        json.dumps({
            "created_at_unix": int(time.time() * 1000)
            - (client.MAX_QUEUE_AGE_SECONDS + 1) * 1000,
            "payload": {"ip": "10.0.0.1"},
        }),
        encoding="utf-8",
    )

    result = client.prune_queue()

    assert result["expired"] == 1
    assert not expired.exists()


def test_heartbeat_sends_current_agent_state(tmp_path, monkeypatch):
    client = _client(tmp_path)
    posted = {}

    def fake_post(url, json, timeout):
        posted.update(json)
        return SimpleNamespace(status_code=200)

    monkeypatch.setattr("api.client.requests.post", fake_post)

    assert client.send_heartbeat(
        agent_name="PRINTFLOW Agent Windows",
        agent_version="0.1.0",
        status="healthy",
        inventory_complete=True,
        observed_printer_ips=["10.2.0.122", "10.2.128.27"],
    ) is True
    assert posted["status"] == "healthy"
    assert posted["agent_token"] == "current-secret-token"
    assert posted["inventory_complete"] is True
    assert posted["observed_printer_ips"] == [
        "10.2.0.122",
        "10.2.128.27",
    ]
