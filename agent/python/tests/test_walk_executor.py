from intelligence.snmp_walk_executor import (
    validate_private_ipv4,
)


def test_private_ip():

    result = validate_private_ipv4(
        "10.2.128.27"
    )

    assert result == "10.2.128.27"


def test_public_blocked():

    try:
        validate_private_ipv4(
            "8.8.8.8"
        )

    except ValueError:
        return

    raise AssertionError(
        "IP publico deveria ser bloqueado."
    )


def test_ipv6_blocked():

    try:
        validate_private_ipv4(
            "2001:4860:4860::8888"
        )

    except ValueError:
        return

    raise AssertionError(
        "IPv6 deveria ser bloqueado."
    )


def main():

    tests = (
        test_private_ip,
        test_public_blocked,
        test_ipv6_blocked,
    )

    for test in tests:

        test()

        print(
            f"{test.__name__}: OK"
        )

    print()
    print(
        "TODOS OS TESTES WALK EXECUTOR: OK"
    )


if __name__ == "__main__":
    main()
