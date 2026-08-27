import asyncio

from snmp.engine import (
    PrinterIntelligenceEngine,
    SnmpRequestResult,
)


PRINT_OID = (
    "1.3.6.1.4.1.1347.42.3.1.1.1.1.1"
)

COPY_OID = (
    "1.3.6.1.4.1.1347.42.3.1.1.1.1.2"
)


def test_kyocera_uses_print_plus_copy_total():

    engine = PrinterIntelligenceEngine()

    async def fake_get_value(
        ip_address: str,
        oid: str,
    ) -> SnmpRequestResult:

        values = {
            PRINT_OID: "80000",
            COPY_OID: "1296",
        }

        return SnmpRequestResult(
            success=oid in values,
            value=values.get(oid),
        )

    engine.get_value = fake_get_value

    count, source, candidates = asyncio.run(
        engine.resolve_page_count(
            ip_address="10.2.0.101",
            vendor="Kyocera",
            raw_data={
                "contador_paginas": "82880",
            },
        )
    )

    assert count == 81296
    assert source == "kyocera-print-copy-total"
    assert candidates[PRINT_OID] == 80000
    assert candidates[COPY_OID] == 1296


def test_kyocera_falls_back_when_private_counter_fails():

    engine = PrinterIntelligenceEngine()

    async def fake_get_value(
        ip_address: str,
        oid: str,
    ) -> SnmpRequestResult:

        return SnmpRequestResult(
            success=False,
            error="OID indisponivel",
        )

    engine.get_value = fake_get_value

    count, source, _ = asyncio.run(
        engine.resolve_page_count(
            ip_address="10.2.0.101",
            vendor="Kyocera",
            raw_data={
                "contador_paginas": "82880",
            },
        )
    )

    assert count == 82880
    assert source == "printer-mib-fallback"
