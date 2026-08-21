from __future__ import annotations

import json
from pathlib import Path

from intelligence import agent_cycle_integration as integration
from intelligence.printer_intelligence_collector import (
    PrinterIntelligenceReport,
)


def _report(ip_address: str) -> PrinterIntelligenceReport:
    return PrinterIntelligenceReport(
        ip_address=ip_address,
        manufacturer=None,
        model=None,
        serial=None,
        counter=None,
        toner=None,
        sys_object_id=None,
        serial_candidates=[],
        counter_candidates=[],
        learning_error=None,
        generated_at="2026-08-19T00:00:00+00:00",
    )


def test_extract_ips():
    payload = {
        "printers": [
            {"ip": "10.2.0.122"},
            {"ip_address": "10.2.128.27"},
            {"endereco_ip": "10.2.128.197"},
            {"ip": "10.2.128.27"},
            {"ip": "999.1.1.1"},
        ]
    }

    assert integration._extract_ips(payload) == [
        "10.2.0.122",
        "10.2.128.27",
        "10.2.128.197",
    ]


def test_inventory_is_preserved(
    tmp_path: Path,
    monkeypatch,
):
    inventory = tmp_path / "agent_inventory.json"
    destination = (
        tmp_path
        / "PRINTFLOW-Printer-Intelligence.json"
    )

    original = json.dumps(
        {
            "printers": [
                {
                    "ip": "10.2.0.122",
                    "serial": "KNDK09992",
                    "contador_paginas": 27357,
                }
            ]
        },
        indent=2,
    )

    inventory.write_text(
        original,
        encoding="utf-8",
    )

    async def fake_collect(**kwargs):
        return [_report(kwargs["ip_addresses"][0])]

    monkeypatch.setattr(
        integration,
        "_collect_reports",
        fake_collect,
    )

    result = integration.generate_from_inventory(
        inventory_path=inventory,
        destination=destination,
        total_timeout=1.0,
    )

    assert result == destination.resolve()
    assert inventory.read_text(encoding="utf-8") == original

    payload = json.loads(
        destination.read_text(encoding="utf-8")
    )

    assert payload["total"] == 1
    assert payload["inventory_preserved"] is True


def test_empty_inventory(
    tmp_path: Path,
):
    inventory = tmp_path / "agent_inventory.json"
    destination = (
        tmp_path
        / "PRINTFLOW-Printer-Intelligence.json"
    )

    inventory.write_text(
        '{"printers": []}',
        encoding="utf-8",
    )

    result = integration.generate_from_inventory(
        inventory_path=inventory,
        destination=destination,
    )

    assert result == destination.resolve()

    payload = json.loads(
        destination.read_text(encoding="utf-8")
    )

    assert payload["total"] == 0
    assert payload["printers"] == []


def test_hook_is_idempotent(
    monkeypatch,
):
    monkeypatch.setattr(
        integration,
        "_INSTALLED",
        False,
    )

    registered = []

    monkeypatch.setattr(
        integration.atexit,
        "register",
        lambda function: registered.append(function),
    )

    assert integration.install_agent_cycle_hook() is True
    assert integration.install_agent_cycle_hook() is False
    assert len(registered) == 1
