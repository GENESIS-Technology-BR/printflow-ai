import json
import logging
from types import SimpleNamespace

import pytest
import requests

from api.client import PrintflowApiClient
from core.service import TalvoaAgentService


def client_for(tmp_path, **kwargs):
    return PrintflowApiClient(
        api_url="https://example.invalid",
        agent_token="synthetic-secret",
        logger=logging.getLogger("queue-replay-budget"),
        queue_directory=tmp_path / "queue",
        **kwargs,
    )


def backlog(client, size):
    for index in range(size):
        (client.queue_directory / f"{index:06}.json").write_text(json.dumps({
            "created_at_unix": 1,
            "payload": {"ip": "192.0.2.1", "page_count": index},
        }), encoding="utf-8")


def test_large_backlog_replays_only_configured_batch(tmp_path, monkeypatch, caplog):
    client = client_for(tmp_path, queue_batch_size=3)
    backlog(client, 501)
    posted = []

    def post(url, json, timeout):
        posted.append(json["page_count"])
        return SimpleNamespace(status_code=200)

    monkeypatch.setattr("api.client.requests.post", post)
    with caplog.at_level(logging.WARNING):
        assert client.retry_queue() == {"processed": 3, "success": 3, "failed": 0}
    assert posted == [0, 1, 2]
    assert len(list(client.queue_directory.glob("*.json"))) == 498
    assert "limite operacional" in caplog.text
    assert client.agent_token not in caplog.text
    assert client.retry_queue() == {"processed": 3, "success": 3, "failed": 0}
    assert posted == list(range(6))


@pytest.mark.parametrize("failure", ["timeout", "connection", 401, 422, 429, 503])
def test_failure_stops_replay_cools_down_and_recovers(tmp_path, monkeypatch, caplog, failure):
    client = client_for(tmp_path, queue_batch_size=3, queue_retry_interval_seconds=10)
    backlog(client, 6)
    originals = {path: path.read_bytes() for path in client.queue_directory.glob("*.json")}
    clock = [100.0]
    monkeypatch.setattr("api.client.time.monotonic", lambda: clock[0])
    calls = []
    online = [False]

    def post(url, json, timeout):
        calls.append(json["page_count"])
        if online[0]:
            return SimpleNamespace(status_code=201)
        if failure == "timeout":
            raise requests.Timeout(client.agent_token)
        if failure == "connection":
            raise requests.ConnectionError(client.agent_token)
        return SimpleNamespace(status_code=failure)

    monkeypatch.setattr("api.client.requests.post", post)
    with caplog.at_level(logging.WARNING):
        assert client.retry_queue() == {"processed": 1, "success": 0, "failed": 1}
        clock[0] = 109.9
        assert client.retry_queue() == {"processed": 0, "success": 0, "failed": 0}
    assert calls == [0]
    assert all(path.exists() for path in originals)
    # Re-serialization may change whitespace, but pending measurements must survive.
    assert all(json.loads(path.read_bytes()) == json.loads(raw) for path, raw in originals.items())
    assert "interrompido" in caplog.text
    assert client.agent_token not in caplog.text
    clock[0] = 110.0
    online[0] = True
    assert client.retry_queue() == {"processed": 3, "success": 3, "failed": 0}
    assert calls == [0, 0, 1, 2]
    assert len(list(client.queue_directory.glob("*.json"))) == 3


def test_invalid_files_are_preserved_and_count_toward_batch(tmp_path, monkeypatch):
    client = client_for(tmp_path, queue_batch_size=2)
    invalid = client.queue_directory / "000000.json"
    invalid.write_bytes(b"incomplete-json")
    second = client.queue_directory / "000001.json"
    second.write_text('{"payload": []}', encoding="utf-8")
    third = client.queue_directory / "000002.json"
    third.write_text('{"payload": {"ip": "192.0.2.1"}}', encoding="utf-8")
    monkeypatch.setattr("api.client.requests.post", lambda *args, **kwargs: pytest.fail("batch exceeded"))
    assert client.retry_queue() == {"processed": 2, "success": 0, "failed": 2}
    assert invalid.read_bytes() == b"incomplete-json"
    assert second.exists() and third.exists()


def test_large_offline_queue_does_not_block_current_inventory(tmp_path, monkeypatch):
    client = client_for(tmp_path)
    backlog(client, 501)
    events = []

    def timeout_post(*args, **kwargs):
        events.append("queued")
        raise requests.Timeout("synthetic")

    def send_current(printers):
        events.append("current")
        return {"success": len(printers), "failed": 0, "skipped": 0, "details": []}

    monkeypatch.setattr("api.client.requests.post", timeout_post)
    monkeypatch.setattr(client, "send_inventory", send_current)
    service = object.__new__(TalvoaAgentService)
    service.api_client = client
    service.logger = logging.getLogger("queue-progress")
    assert service.synchronize_api([{"ip": "192.0.2.2"}])["success"] == 1
    assert events == ["queued", "current"]
    assert len(list(client.queue_directory.glob("*.json"))) == 501
    service.synchronize_api([{"ip": "192.0.2.2"}])
    assert events == ["queued", "current", "current"]


@pytest.mark.parametrize("requested,expected", [(0, 1), (-5, 1), (5, 5), (500, 20)])
def test_replay_batch_configuration_has_safe_bounds(tmp_path, requested, expected):
    client = client_for(tmp_path, queue_batch_size=requested)
    assert client.queue_batch_size == expected


def test_service_reads_replay_configuration(tmp_path, monkeypatch):
    monkeypatch.setenv("TALVOA_QUEUE_BATCH_SIZE", "4")
    monkeypatch.setenv("TALVOA_QUEUE_RETRY_INTERVAL_SECONDS", "120")
    service = TalvoaAgentService(
        settings=SimpleNamespace(api_url="https://example.invalid", agent_token="synthetic",
                                 output_directory=tmp_path),
        logger=logging.getLogger("queue-config"),
    )
    assert service.api_client.queue_batch_size == 4
    assert service.api_client.queue_retry_interval_seconds == 120


def test_current_inventory_is_saved_before_http_sync(tmp_path, monkeypatch):
    service = object.__new__(TalvoaAgentService)
    service.logger = logging.getLogger("queue-order")
    service.settings = SimpleNamespace(output_directory=tmp_path, agent_name="Synthetic",
                                       agent_version="test")
    printers = [{"snmp": {"snmp_online": True}, "discovery": {"ip_address": "192.0.2.1"}}]
    monkeypatch.setattr(service, "_send_heartbeat_safe", lambda **kwargs: True)
    monkeypatch.setattr(service, "discover_devices", lambda: [])

    async def collect(devices):
        return printers

    def run_without_event_loop(coroutine):
        coroutine.close()
        return printers

    monkeypatch.setattr(service, "collect_snmp_data", collect)
    monkeypatch.setattr("core.service.asyncio.run", run_without_event_loop)

    def sync(printers):
        saved = json.loads((tmp_path / "agent_inventory.json").read_text(encoding="utf-8"))
        assert saved["printers"] == printers
        raise RuntimeError("synthetic interruption during HTTP")

    monkeypatch.setattr(service, "synchronize_api", sync)
    assert service.run_cycle() == 1
    assert json.loads((tmp_path / "agent_inventory.json").read_text(encoding="utf-8"))["printers"] == printers
