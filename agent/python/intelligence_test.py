from __future__ import annotations

import argparse
import asyncio
import json

from snmp.engine import (
    collect_printer_intelligence,
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Teste da inteligência SNMP "
            "do PRINTFLOW"
        )
    )

    parser.add_argument(
        "ip",
        help="IP da impressora.",
    )

    parser.add_argument(
        "--community",
        default="public",
    )

    return parser.parse_args()


async def main() -> int:
    arguments = parse_arguments()

    result = await collect_printer_intelligence(
        ip_address=arguments.ip,
        community=arguments.community,
    )

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        )
    )

    return (
        0
        if result.get("snmp_online")
        else 2
    )


if __name__ == "__main__":
    raise SystemExit(
        asyncio.run(main())
    )
