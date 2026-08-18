from intelligence.snmp_deep_learning import (
    enterprise_root_from_sysobjectid,
    classify_walk_value,
)


def test_zebra_enterprise_root():

    root = enterprise_root_from_sysobjectid(
        "1.3.6.1.4.1.10642.20.1"
    )

    assert root == "1.3.6.1.4.1.10642"


def test_enterprise_generic():

    root = enterprise_root_from_sysobjectid(
        "1.3.6.1.4.1.99999.1.2.3"
    )

    assert root == "1.3.6.1.4.1.99999"


def test_invalid_root():

    root = enterprise_root_from_sysobjectid(
        "1.3.6.1.2.1.1.1.0"
    )

    assert root is None


def test_serial_candidate():

    result = classify_walk_value(
        "1.3.6.1.4.1.10642.1.1",
        "23J241700123",
    )

    serials = [
        item
        for item in result
        if item.candidate_type == "serial"
    ]

    assert serials
    assert serials[0].confidence >= 80


def test_counter_candidate():

    result = classify_walk_value(
        "1.3.6.1.4.1.10642.1.2",
        "147832",
    )

    counters = [
        item
        for item in result
        if item.candidate_type == "counter"
    ]

    assert counters


def main():

    tests = (
        test_zebra_enterprise_root,
        test_enterprise_generic,
        test_invalid_root,
        test_serial_candidate,
        test_counter_candidate,
    )

    for test in tests:
        test()
        print(
            f"{test.__name__}: OK"
        )

    print()
    print(
        "TODOS OS TESTES DEEP LEARNING: OK"
    )


if __name__ == "__main__":
    main()
