from __future__ import annotations

import logging
from pathlib import Path

from api.client import PrintflowApiClient


def _client(tmp_path: Path) -> PrintflowApiClient:
    return PrintflowApiClient(
        api_url="https://example.invalid",
        agent_token="test-token",
        logger=logging.getLogger("test-api-intelligence"),
        queue_directory=tmp_path / "queue",
    )


def _printer(
    *,
    ip_address: str,
    manufacturer: str,
    model: str,
    serial: str | None,
    page_count: int | None,
    learning: dict | None = None,
) -> dict:
    return {
        "discovery": {
            "ip_address": ip_address,
            "hostname": None,
        },
        "snmp": {
            "snmp_online": True,
            "dados": {
                "fabricante": manufacturer,
                "modelo": model,
                "serial": serial,
                "contador_paginas": page_count,
                "learning_diagnostic": learning,
            },
        },
    }


def test_canon_trusted_values_are_preserved(tmp_path: Path):
    payload = _client(tmp_path).build_payload(
        _printer(
            ip_address="10.2.0.122",
            manufacturer="Canon",
            model="Canon GX6000 series 1.070",
            serial="KNDK09992",
            page_count=27377,
        )
    )

    assert payload["serial"] == "KNDK09992"
    assert payload["serial_confirmed"] is True
    assert payload["serial_confidence"] is not None
    assert payload["page_count"] == 27377
    assert payload["page_count_confirmed"] is True


def test_zebra_false_serial_is_replaced_before_api(tmp_path: Path):
    payload = _client(tmp_path).build_payload(
        _printer(
            ip_address="10.2.128.27",
            manufacturer="Zebra",
            model="Zebra Technologies ZT230",
            serial="ZTC ZT230-203dpi ZPL",
            page_count=None,
            learning={
                "serial_candidates": [
                    {
                        "oid": "1.3.6.1.4.1.10642.1.4.0",
                        "value": "52N212401393",
                        "confidence": 90,
                    }
                ],
                "counter_candidates": [
                    {
                        "oid": "1.3.6.1.4.1.10642.1.20.0",
                        "value": "25250016",
                        "confidence": 65,
                    }
                ],
            },
        )
    )

    assert payload["serial"] == "52N212401393"
    assert payload["serial_source"] == "zebra-enterprise-oid"
    assert payload["serial_confidence"] == 99
    assert payload["serial_confirmed"] is True
    assert payload["page_count"] is None
    assert payload["page_count_confirmed"] is False


def test_unconfirmed_learned_serial_is_not_sent(tmp_path: Path):
    payload = _client(tmp_path).build_payload(
        _printer(
            ip_address="10.2.128.50",
            manufacturer="Unknown",
            model="Unknown Printer",
            serial="not a serial description",
            page_count=None,
            learning={
                "serial_candidates": [
                    {
                        "oid": "1.2.3.4",
                        "value": "ABC123456",
                        "confidence": 90,
                    }
                ]
            },
        )
    )

    assert payload["serial"] is None
