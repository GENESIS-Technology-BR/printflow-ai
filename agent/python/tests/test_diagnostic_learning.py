from __future__ import annotations

import asyncio

from intelligence.diagnostic_learning_bridge import (
    ALLOWED_LEARNING_JOB,
    DiagnosticLearningRequest,
    execute_learning_job,
    validate_private_target,
)


def test_private_target():
    assert (
        validate_private_target(
            "10.2.0.122"
        )
        == "10.2.0.122"
    )


def test_public_target_blocked():
    try:
        validate_private_target(
            "8.8.8.8"
        )
    except ValueError:
        return

    raise AssertionError(
        "IP publico deveria ser bloqueado."
    )


def test_invalid_job_blocked():
    async def run():
        def factory(ip_address):
            async def getter(oid):
                return None

            return getter

        result = await execute_learning_job(
            DiagnosticLearningRequest(
                job="EXEC_COMMAND",
                ip_address="10.2.0.122",
                vendor="Canon",
            ),
            factory,
        )

        assert result.success is False
        assert "nao autorizado" in (
            result.error or ""
        ).lower()

    asyncio.run(run())


def test_learning_job():
    async def run():

        fake_values = {
            "1.3.6.1.2.1.43.5.1.1.17.1":
                "KNDK09992",
            "1.3.6.1.2.1.43.10.2.1.4.1.1":
                "27346",
            "1.3.6.1.2.1.1.1.0":
                "Canon GX6000 series 1.070",
        }

        def factory(ip_address):
            assert ip_address == "10.2.0.122"

            async def getter(oid):
                return fake_values.get(oid)

            return getter

        result = await execute_learning_job(
            DiagnosticLearningRequest(
                job=ALLOWED_LEARNING_JOB,
                ip_address="10.2.0.122",
                vendor="Canon",
            ),
            factory,
        )

        assert result.success is True
        assert result.vendor == "Canon"
        assert result.report is not None

        candidates = (
            result.report["candidates"]
        )

        serials = [
            item
            for item in candidates
            if item["field"] == "serial"
            and item["valid"]
        ]

        counters = [
            item
            for item in candidates
            if item["field"] == "page_count"
            and item["valid"]
        ]

        assert serials
        assert counters

        assert (
            serials[0]["value"]
            == "KNDK09992"
        )

        assert (
            counters[0]["value"]
            == "27346"
        )

    asyncio.run(run())


def main():

    tests = (
        test_private_target,
        test_public_target_blocked,
        test_invalid_job_blocked,
        test_learning_job,
    )

    for test in tests:
        test()
        print(
            f"{test.__name__}: OK"
        )

    print()
    print(
        "TODOS OS TESTES "
        "DIAGNOSTIC LEARNING: OK"
    )


if __name__ == "__main__":
    main()
