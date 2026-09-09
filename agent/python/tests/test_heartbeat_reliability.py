from __future__ import annotations

from types import SimpleNamespace

from core.service import PrintflowAgentService


class FakeLogger:
    def __init__(self) -> None:
        self.warnings: list[tuple[object, ...]] = []

    def warning(self, *args: object) -> None:
        self.warnings.append(args)


class FailingHeartbeatClient:
    def send_heartbeat(self, **kwargs: object) -> None:
        raise RuntimeError("API indisponível")


class RejectedHeartbeatClient:
    def send_heartbeat(self, **kwargs: object) -> bool:
        return False


class RecordingHeartbeatClient:
    def __init__(self) -> None:
        self.payloads: list[dict[str, object]] = []

    def send_heartbeat(self, **kwargs: object) -> None:
        self.payloads.append(dict(kwargs))


def build_service(client: object) -> PrintflowAgentService:
    service = object.__new__(PrintflowAgentService)
    service.settings = SimpleNamespace(
        agent_name="PRINTFLOW Agent Windows",
        agent_version="0.3.7",
    )
    service.logger = FakeLogger()
    service.api_client = client
    return service


def test_heartbeat_failure_does_not_raise() -> None:
    service = build_service(FailingHeartbeatClient())

    result = service._send_heartbeat_safe(status="running")

    assert result is False
    assert service.logger.warnings


def test_heartbeat_preserves_operational_payload() -> None:
    client = RecordingHeartbeatClient()
    service = build_service(client)

    result = service._send_heartbeat_safe(
        status="healthy",
        inventory_complete=True,
        observed_printer_ips=["10.2.0.10", "10.2.0.20"],
    )

    assert result is True
    assert client.payloads == [
        {
            "agent_name": "PRINTFLOW Agent Windows",
            "agent_version": "0.3.7",
            "status": "healthy",
            "inventory_complete": True,
            "observed_printer_ips": ["10.2.0.10", "10.2.0.20"],
            "retries": 2,
            "retry_delay_seconds": 1.0,
        }
    ]


def test_heartbeat_false_result_is_reported_as_failure() -> None:
    service = build_service(RejectedHeartbeatClient())

    result = service._send_heartbeat_safe(status="running")

    assert result is False
    assert service.logger.warnings
