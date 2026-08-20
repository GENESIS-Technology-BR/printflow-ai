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

    result = integration.generate_from_inventory(
        inventory_path=inventory,
        destination=destination,
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


def test_extract_ips_from_real_agent_inventory():
    payload = {
        "summary": {
            "devices_found": 1,
            "possible_printers": 1,
        },
        "printers": [
            {
                "discovery": {
                    "ip_address": "10.2.0.122",
                    "possible_printer": True,
                },
                "snmp": {
                    "ip_address": "10.2.0.122",
                    "snmp_online": True,
                    "dados": {
                        "fabricante": "Canon",
                        "serial": "KNDK09992",
                    },
                },
            },
            {
                "discovery": {
                    "ip_address": "10.2.128.27",
                    "possible_printer": True,
                },
                "snmp": {
                    "ip_address": "10.2.128.27",
                    "snmp_online": True,
                },
            },
            {
                "discovery": {
                    "ip_address": "10.2.128.197",
                    "possible_printer": True,
                },
                "snmp": {
                    "ip_address": "10.2.128.197",
                    "snmp_online": True,
                },
            },
        ],
    }

    assert integration._extract_ips(payload) == [
        "10.2.0.122",
        "10.2.128.27",
        "10.2.128.197",
    ]


def test_discovery_ip_wins_without_duplication():
    payload = {
        "printers": [
            {
                "discovery": {
                    "ip_address": "10.2.0.122",
                },
                "snmp": {
                    "ip_address": "10.2.0.122",
                },
            }
        ]
    }

    assert integration._extract_ips(payload) == [
        "10.2.0.122"
    ]


def test_reports_use_existing_snmp_inventory():
    payload = {
        "printers": [
            {
                "discovery": {"ip_address": "10.2.0.122"},
                "snmp": {
                    "ip_address": "10.2.0.122",
                    "dados": {
                        "fabricante": "Canon",
                        "modelo": "Canon GX6000 series 1.070",
                        "serial": "KNDK09992",
                        "contador_paginas": 27377,
                        "toner_percentual": 14,
                    },
                },
            },
            {
                "discovery": {"ip_address": "10.2.128.27"},
                "snmp": {
                    "ip_address": "10.2.128.27",
                    "dados": {
                        "fabricante": "Zebra",
                        "modelo": "Zebra Technologies ZT230",
                        "serial": "ZTC ZT230-203dpi ZPL",
                        "contador_paginas": None,
                        "learning_diagnostic": {
                            "serial_candidates": [
                                {
                                    "oid": "1.3.6.1.4.1.10642.1.4.0",
                                    "value": "52N212401393",
                                    "confidence": 90,
                                }
                            ],
                            "counter_candidates": [],
                        },
                    },
                },
            },
        ]
    }

    reports = integration.build_reports_from_inventory(payload)

    assert len(reports) == 2
    assert reports[0].serial
    assert reports[0].serial.value == "KNDK09992"
    assert reports[0].counter
    assert reports[0].counter.value == 27377
    assert reports[1].serial
    assert reports[1].serial.value == "52N212401393"
    assert reports[1].serial.confirmed is True
    assert reports[1].counter is None
