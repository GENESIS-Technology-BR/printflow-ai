from intelligence.printer_intelligence_collector import (
    best_serial_candidate,
    build_report,
    normalize_counter,
    normalize_vendor,
    validate_serial,
)


def test_canon_serial():

    valid, confidence, _ = (
        validate_serial(
            "KNDK09992"
        )
    )

    assert valid
    assert confidence >= 90


def test_zebra_description_blocked():

    valid, confidence, _ = (
        validate_serial(
            "ZTC ZT230-203dpi ZPL"
        )
    )

    assert not valid
    assert confidence <= 20


def test_zebra_zd_description_blocked():

    valid, confidence, _ = (
        validate_serial(
            "ZTC ZD230-203dpi ZPL"
        )
    )

    assert not valid
    assert confidence <= 20


def test_vendor():

    assert (
        normalize_vendor(
            "Zebra Technologies"
        )
        == "Zebra"
    )

    assert (
        normalize_vendor(
            "Canon"
        )
        == "Canon"
    )


def test_counter():

    assert (
        normalize_counter(
            "27357"
        )
        == 27357
    )


def test_primary_wins():

    report = build_report(
        ip_address="10.2.0.122",
        primary={
            "fabricante": "Canon",
            "modelo": (
                "Canon GX6000 series 1.070"
            ),
            "serial": "KNDK09992",
            "contador_paginas": 27357,
            "contador_origem": (
                "canon-vendor-consensus"
            ),
            "toner_percentual": 14,
        },
        learning={
            "serial_candidates": [
                {
                    "value": "FAKE123456",
                    "confidence": 99,
                    "oid": "1.2.3",
                }
            ],
        },
    )

    assert report.serial
    assert (
        report.serial.value
        == "KNDK09992"
    )

    assert report.serial.confirmed


def test_bad_primary_serial_removed():

    report = build_report(
        ip_address="10.2.128.27",
        primary={
            "fabricante": "Zebra",
            "modelo": (
                "Zebra Technologies ZT230"
            ),
            "serial": (
                "ZTC ZT230-203dpi ZPL"
            ),
            "contador_paginas": None,
        },
        learning={
            "serial_candidates": [],
            "counter_candidates": [],
        },
    )

    assert report.serial is None
    assert report.counter is None


def test_learned_serial():

    result = best_serial_candidate(
        [
            {
                "value": (
                    "ZTC ZT230-203dpi ZPL"
                ),
                "confidence": 99,
                "oid": "1.2.3",
            },
            {
                "value": "23J241700123",
                "confidence": 90,
                "oid": "1.2.4",
            },
        ]
    )

    assert result
    assert (
        result.value
        == "23J241700123"
    )


def main():

    tests = (
        test_canon_serial,
        test_zebra_description_blocked,
        test_zebra_zd_description_blocked,
        test_vendor,
        test_counter,
        test_primary_wins,
        test_bad_primary_serial_removed,
        test_learned_serial,
    )

    for test in tests:
        test()
        print(
            f"{test.__name__}: OK"
        )

    print()
    print(
        "TODOS OS TESTES COLLECTOR UNIVERSAL: OK"
    )


if __name__ == "__main__":
    main()
