from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from intelligence.printer_intelligence_collector import (
    collect_many,
    save_reports,
)


async def run() -> int:

    parser = argparse.ArgumentParser(
        description=(
            "PRINTFLOW Printer Intelligence "
            "Universal Diagnostic"
        )
    )

    parser.add_argument(
        "--ip",
        action="append",
        dest="ips",
        required=True,
        help=(
            "IPv4 da impressora. "
            "Pode repetir --ip."
        ),
    )

    parser.add_argument(
        "--community",
        default="public",
    )

    parser.add_argument(
        "--output",
        default=(
            "output/"
            "PRINTFLOW-Printer-Intelligence.json"
        ),
    )

    args = parser.parse_args()

    print("=" * 62)
    print(
        "PRINTFLOW - PRINTER INTELLIGENCE"
    )
    print(
        "DIAGNOSTICO UNIVERSAL - SOMENTE LEITURA"
    )
    print("=" * 62)

    reports = await collect_many(
        ip_addresses=args.ips,
        community=args.community,
    )

    print()

    for report in reports:

        print(
            "IP:",
            report.ip_address,
        )

        print(
            "  Fabricante:",
            (
                report.manufacturer.value
                if report.manufacturer
                else "Nao identificado"
            ),
        )

        print(
            "  Modelo:",
            (
                report.model.value
                if report.model
                else "Nao identificado"
            ),
        )

        print(
            "  Serial:",
            (
                report.serial.value
                if report.serial
                else "Nao confirmado"
            ),
        )

        print(
            "  Contador:",
            (
                report.counter.value
                if report.counter
                else "Nao confirmado"
            ),
        )

        print(
            "  SysObjectID:",
            (
                report.sys_object_id
                or "Nao informado"
            ),
        )

        print(
            "  Candidatos serial:",
            len(
                report.serial_candidates
            ),
        )

        print(
            "  Candidatos contador:",
            len(
                report.counter_candidates
            ),
        )

        if report.learning_error:
            print(
                "  Learning error:",
                report.learning_error,
            )

        print()

    path = save_reports(
        reports=reports,
        destination=Path(
            args.output
        ),
    )

    print("=" * 62)
    print(
        "ARQUIVO GERADO:"
    )
    print(path.resolve())
    print("=" * 62)

    return 0


if __name__ == "__main__":
    raise SystemExit(
        asyncio.run(
            run()
        )
    )
