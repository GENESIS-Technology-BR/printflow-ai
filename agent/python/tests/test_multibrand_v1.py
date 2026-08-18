from __future__ import annotations

import asyncio

from intelligence.snmp_learning import learn_printer_identity
from intelligence.snmp_normalizer import (
    decode_hex_text,
    normalize_text,
    normalize_vendor,
)
from intelligence.vendor_profiles import get_vendor_profile


def test_hex_decode():
    result = decode_hex_text(
        "0x43414e4f4e20475836303030"
    )

    assert result == "CANON GX6000"


def test_vendor_normalization():
    assert normalize_vendor("Hewlett-Packard") == "HP"
    assert normalize_vendor("Canon") == "Canon"
    assert normalize_vendor("Zebra Technologies") == "Zebra"
    assert normalize_vendor("RICOH") == "Ricoh"


def test_profile_fallback():
    profile = get_vendor_profile("fabricante-inexistente")

    assert profile.name == "generic"


def test_hp_profile():
    profile = get_vendor_profile("HP")

    assert len(profile.serial_oids) >= 2


def test_learning():
    fake = {
        "1.3.6.1.2.1.43.5.1.1.17.1": "SERIAL-123",
        "1.3.6.1.2.1.43.10.2.1.4.1.1": "27346",
        "1.3.6.1.2.1.1.1.0": "Canon GX6000",
    }

    async def getter(oid: str):
        return fake.get(oid)

    report = asyncio.run(
        learn_printer_identity(
            "Canon",
            getter,
        )
    )

    serial = [
        item
        for item in report.candidates
        if item.field == "serial"
        and item.valid
    ]

    assert serial
    assert serial[0].value == "SERIAL-123"


def main():
    tests = (
        test_hex_decode,
        test_vendor_normalization,
        test_profile_fallback,
        test_hp_profile,
        test_learning,
    )

    for test in tests:
        test()
        print(f"{test.__name__}: OK")

    print()
    print("TODOS OS TESTES MULTIMARCA V1: OK")


if __name__ == "__main__":
    main()
