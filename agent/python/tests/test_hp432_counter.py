import asyncio

from snmp.engine import PrinterIntelligenceEngine, SnmpRequestResult


UNIT_OID = "1.3.6.1.2.1.43.10.2.1.3.1.1"


def _read(unit):
    engine = PrinterIntelligenceEngine()
    async def fake_get_value(ip_address, oid):
        assert oid == UNIT_OID
        return SnmpRequestResult(success=unit is not None, value=str(unit) if unit is not None else None)
    engine.get_value = fake_get_value
    return asyncio.run(engine.resolve_page_count(
        ip_address="10.2.0.124",
        vendor="HP",
        raw_data={"descricao": "HP Laser MFP 432fdn", "contador_paginas": "35654"},
    ))


def test_hp432_accepts_exact_lifetime_counter_when_units_are_impressions():
    value, source, candidates = _read(7)
    assert value == 35654
    assert source == "hp432-prt-marker-impressions"
    assert candidates[UNIT_OID] == 7


def test_hp432_rejects_sheets_or_unknown_units():
    for unit in (8, 2, None):
        value, source, _ = _read(unit)
        assert value is None
        assert source == "hp432-counter-unit-not-verified"
