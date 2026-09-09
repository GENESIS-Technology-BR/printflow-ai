from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from api.client import PrintflowApiClient


class Logger:
    def info(self, *args):
        pass

    def error(self, *args):
        pass


def build_client(tmp_path: Path) -> PrintflowApiClient:
    return PrintflowApiClient(
        api_url="https://printflow.invalid",
        agent_token="token-test",
        logger=Logger(),
        queue_directory=tmp_path / "queue",
    )


def test_heartbeat_retries_transient_connection_failure(tmp_path: Path) -> None:
    client = build_client(tmp_path)
    ok = SimpleNamespace(status_code=200)

    with patch("api.client.requests.post", side_effect=[
        __import__("requests").ConnectionError("offline"),
        ok,
    ]) as post, patch("api.client.time.sleep") as sleep:
        result = client.send_heartbeat(
            agent_name="Agent",
            agent_version="1.0",
            status="healthy",
            retries=2,
            retry_delay_seconds=1,
        )

    assert result is True
    assert post.call_count == 2
    sleep.assert_called_once_with(1.0)


def test_heartbeat_does_not_retry_invalid_token(tmp_path: Path) -> None:
    client = build_client(tmp_path)
    unauthorized = SimpleNamespace(status_code=401)

    with patch("api.client.requests.post", return_value=unauthorized) as post:
        result = client.send_heartbeat(
            agent_name="Agent",
            agent_version="1.0",
            status="healthy",
            retries=2,
        )

    assert result is False
    assert post.call_count == 1
