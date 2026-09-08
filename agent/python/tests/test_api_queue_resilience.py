from __future__ import annotations

from core.service import PrintflowAgentService


class FakeLogger:
    def info(self, *args: object) -> None:
        pass

    def warning(self, *args: object) -> None:
        pass

    def error(self, *args: object) -> None:
        pass

    def exception(self, *args: object) -> None:
        pass


class QueueFailingClient:
    is_configured = True

    def __init__(self) -> None:
        self.inventory_calls = 0

    def retry_queue(self) -> dict[str, int]:
        raise RuntimeError("fila indisponível")

    def send_inventory(self, printers: list[dict[str, object]]) -> dict[str, object]:
        self.inventory_calls += 1
        return {
            "success": len(printers),
            "failed": 0,
            "skipped": 0,
            "details": [],
        }


class UnconfiguredClient:
    is_configured = False

    def send_inventory(self, printers: list[dict[str, object]]) -> dict[str, object]:
        raise AssertionError("send_inventory não deve ser chamado sem token")


def build_service(client: object) -> PrintflowAgentService:
    service = object.__new__(PrintflowAgentService)
    service.logger = FakeLogger()
    service.api_client = client
    return service


def test_queue_failure_does_not_block_current_inventory() -> None:
    client = QueueFailingClient()
    service = build_service(client)

    result = service.synchronize_api(
        [{"snmp": {"snmp_online": True}}]
    )

    assert client.inventory_calls == 1
    assert result["success"] == 1
    assert result["failed"] == 0


def test_missing_token_skips_remote_sync_without_exception() -> None:
    service = build_service(UnconfiguredClient())

    result = service.synchronize_api(
        [
            {"snmp": {"snmp_online": True}},
            {"snmp": {"snmp_online": False}},
        ]
    )

    assert result == {
        "success": 0,
        "failed": 0,
        "skipped": 2,
        "details": [],
    }
