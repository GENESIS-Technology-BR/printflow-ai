from __future__ import annotations

import json
from pathlib import Path

from core.service import PrintflowAgentService


class FakeLogger:
    def warning(self, *args: object) -> None:
        pass


def test_local_health_snapshot_is_written(tmp_path: Path) -> None:
    service = object.__new__(PrintflowAgentService)
    service.logger = FakeLogger()
    service.settings = type(
        "Settings",
        (),
        {
            "output_directory": tmp_path,
            "agent_version": "test",
        },
    )()

    service._write_local_health(
        status="healthy",
        cycle_started_monotonic=0.0,
        printers_count=7,
        api_failed=1,
    )

    health_path = tmp_path / "agent_health.json"
    assert health_path.exists()

    payload = json.loads(
        health_path.read_text(encoding="utf-8")
    )

    assert payload["status"] == "healthy"
    assert payload["printers_count"] == 7
    assert payload["api_failed"] == 1
    assert payload["agent_version"] == "test"
    assert "updated_at" in payload
    assert "cycle_duration_seconds" in payload
