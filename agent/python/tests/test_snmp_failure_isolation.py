from __future__ import annotations

import asyncio
from dataclasses import dataclass

import pytest

import core.service as service_module
from core.service import PrintflowAgentService


@dataclass
class FakeDevice:
    ip_address: str
    possible_printer: bool = True


class FakeLogger:
    def info(self, *args: object) -> None:
        pass

    def warning(self, *args: object) -> None:
        pass

    def exception(self, *args: object) -> None:
        pass


def test_snmp_failure_is_isolated_per_printer(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    async def fake_collect_printer_intelligence(**kwargs: object) -> dict[str, object]:
        ip = str(kwargs["ip_address"])
        calls.append(ip)
        if ip == "10.2.0.10":
            raise RuntimeError("timeout SNMP")
        return {
            "snmp_online": True,
            "dados": {"contador_paginas": 1234},
        }

    monkeypatch.setattr(
        service_module,
        "collect_printer_intelligence",
        fake_collect_printer_intelligence,
    )

    service = object.__new__(PrintflowAgentService)
    service.logger = FakeLogger()
    service.settings = type(
        "Settings",
        (),
        {
            "snmp_community": "public",
            "snmp_timeout": 1.0,
            "snmp_retries": 1,
        },
    )()

    result = asyncio.run(
        service.collect_snmp_data(
            [
                FakeDevice("10.2.0.10"),
                FakeDevice("10.2.0.20"),
            ]
        )
    )

    assert calls == ["10.2.0.10", "10.2.0.20"]
    assert len(result) == 2
    assert result[0]["snmp"]["snmp_online"] is False
    assert "timeout SNMP" in result[0]["snmp"]["erro"]
    assert result[1]["snmp"]["snmp_online"] is True
