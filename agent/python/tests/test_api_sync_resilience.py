from __future__ import annotations

from pathlib import Path

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


class FailingApiClient:
    is_configured = True

    def retry_queue(self) -> dict[str, int]:
        return {"processed": 0, "success": 0, "failed": 0}

    def send_inventory(self, printers: list[dict[str, object]]) -> dict[str, object]:
        raise RuntimeError("API temporariamente indisponível")


def test_api_failure_returns_result_and_allows_local_inventory(tmp_path: Path) -> None:
    service = object.__new__(PrintflowAgentService)
    service.logger = FakeLogger()
    service.api_client = FailingApiClient()
    service.settings = type(
        "Settings",
        (),
        {
            "agent_name": "PRINTFLOW Agent",
            "agent_version": "test",
            "output_directory": tmp_path,
        },
    )()

    printers = [
        {"snmp": {"snmp_online": True}},
        {"snmp": {"snmp_online": False}},
    ]

    api_result = service.synchronize_api(printers)

    assert api_result["success"] == 0
    assert api_result["failed"] == 2

    output = service.save_inventory(
        devices=[],
        printers=printers,
        api_result=api_result,
    )

    assert output.exists()
