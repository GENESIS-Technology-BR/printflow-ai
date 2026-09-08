from __future__ import annotations

from pathlib import Path

import core.service as service_module
from core.service import PrintflowAgentService


class FakeLogger:
    def __init__(self) -> None:
        self.warnings: list[tuple[object, ...]] = []

    def info(self, *args: object) -> None:
        pass

    def warning(self, *args: object) -> None:
        self.warnings.append(args)

    def exception(self, *args: object) -> None:
        pass


class FakeApiClient:
    def __init__(self) -> None:
        self.heartbeats: list[dict[str, object]] = []

    def send_heartbeat(self, **kwargs: object) -> None:
        self.heartbeats.append(dict(kwargs))


def test_cycle_above_sla_is_reported_as_slow(monkeypatch, tmp_path: Path) -> None:
    service = object.__new__(PrintflowAgentService)
    service.logger = FakeLogger()
    service.api_client = FakeApiClient()
    service.settings = type(
        "Settings",
        (),
        {
            "agent_name": "PRINTFLOW Agent",
            "agent_version": "test",
            "cycle_sla_seconds": 90,
            "output_directory": tmp_path,
        },
    )()

    service.discover_devices = lambda: []
    async def fake_collect(_devices):
        return []
    service.collect_snmp_data = fake_collect
    service.synchronize_api = lambda printers: {
        "success": 0,
        "failed": 0,
        "skipped": 0,
    }
    service.save_inventory = lambda **kwargs: tmp_path / "agent_inventory.json"

    monotonic_values = iter([0.0, 95.0, 95.0])
    monkeypatch.setattr(
        service_module,
        "_monotonic",
        lambda: next(monotonic_values),
    )

    result = service.run_cycle()

    assert result == 0
    assert service.api_client.heartbeats[-1]["status"] == "slow"
    assert service.logger.warnings
