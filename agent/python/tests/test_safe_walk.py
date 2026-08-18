from intelligence.snmp_safe_walk import (
    WalkPolicy,
    WalkRow,
    analyse_rows,
    best_candidates,
    build_learning_roots,
    oid_is_inside,
)


def test_oid_scope():

    assert oid_is_inside(
        "1.3.6.1.2.1.43.5.1",
        "1.3.6.1.2.1.43",
    )

    assert not oid_is_inside(
        "1.3.6.1.4.1.99999.1",
        "1.3.6.1.2.1.43",
    )


def test_learning_roots():

    roots = build_learning_roots(
        "1.3.6.1.4.1.10642.20.1"
    )

    assert (
        "1.3.6.1.2.1.43"
        in roots
    )

    assert (
        "1.3.6.1.4.1.10642"
        in roots
    )


def test_serial_detection():

    roots = [
        "1.3.6.1.4.1.10642"
    ]

    rows = [
        WalkRow(
            oid="1.3.6.1.4.1.10642.1.10.1",
            value="ZT230",
        ),
        WalkRow(
            oid="1.3.6.1.4.1.10642.1.10.2",
            value="23J241700123",
        ),
    ]

    analysis = analyse_rows(
        roots=roots,
        rows=rows,
    )

    serials = best_candidates(
        analysis,
        "serial",
    )

    assert serials

    assert (
        serials[0].value
        == "23J241700123"
    )


def test_counter_detection():

    roots = [
        "1.3.6.1.4.1.10642"
    ]

    rows = [
        WalkRow(
            oid="1.3.6.1.4.1.10642.1.20.1",
            value="156732",
        ),
    ]

    analysis = analyse_rows(
        roots=roots,
        rows=rows,
    )

    counters = best_candidates(
        analysis,
        "counter",
    )

    assert counters

    assert counters[0].value == "156732"


def test_max_rows():

    roots = [
        "1.3.6.1.4.1.10642"
    ]

    rows = [
        WalkRow(
            oid=f"1.3.6.1.4.1.10642.99.{i}",
            value=str(100000 + i),
        )
        for i in range(100)
    ]

    analysis = analyse_rows(
        roots=roots,
        rows=rows,
        policy=WalkPolicy(
            max_rows=10,
            max_seconds=10,
        ),
    )

    assert analysis.rows_seen == 10
    assert analysis.truncated is True


def main():

    tests = (
        test_oid_scope,
        test_learning_roots,
        test_serial_detection,
        test_counter_detection,
        test_max_rows,
    )

    for test in tests:
        test()
        print(
            f"{test.__name__}: OK"
        )

    print()
    print(
        "TODOS OS TESTES SAFE WALK: OK"
    )


if __name__ == "__main__":
    main()
