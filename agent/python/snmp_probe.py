from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from pysnmp.hlapi.v3arch.asyncio import (
    CommunityData,
    ContextData,
    ObjectIdentity,
    ObjectType,
    SnmpEngine,
    UdpTransportTarget,
    get_cmd,
)


OIDS = {
    "descricao": "1.3.6.1.2.1.1.1.0",
    "nome": "1.3.6.1.2.1.1.5.0",
    "uptime": "1.3.6.1.2.1.1.3.0",
    "contador_paginas": "1.3.6.1.2.1.43.10.2.1.4.1.1",
    "status_impressora": "1.3.6.1.2.1.25.3.5.1.1.1",
}


async def snmp_get(
    ip_address: str,
    community: str,
    oid: str,
    timeout: float,
    retries: int,
) -> str | None:
    try:
        transport = await UdpTransportTarget.create(
            (ip_address, 161),
            timeout=timeout,
            retries=retries,
        )

        error_indication, error_status, error_index, var_binds = (
            await get_cmd(
                SnmpEngine(),
                CommunityData(
                    community,
                    mpModel=1,
                ),
                transport,
                ContextData(),
                ObjectType(
                    ObjectIdentity(oid)
                ),
                lookupMib=False,
            )
        )

        if error_indication:
            return None

        if error_status:
            return None

        if not var_binds:
            return None

        value = var_binds[0][1]

        return value.prettyPrint()

    except Exception:
        return None


async def collect_printer(
    ip_address: str,
    community: str,
    timeout: float,
    retries: int,
) -> dict:
    result = {
        "ip_address": ip_address,
        "community": community,
        "snmp_online": False,
        "dados": {},
    }

    for field_name, oid in OIDS.items():
        value = await snmp_get(
            ip_address=ip_address,
            community=community,
            oid=oid,
            timeout=timeout,
            retries=retries,
        )

        if value is not None:
            result["snmp_online"] = True
            result["dados"][field_name] = value
        else:
            result["dados"][field_name] = None

    return result


def print_result(result: dict) -> None:
    print()
    print("=" * 72)
    print("PRINTFLOW AGENT — TESTE SNMP")
    print("=" * 72)

    print(f"IP            : {result['ip_address']}")
    print(
        f"Status SNMP   : "
        f"{'ONLINE' if result['snmp_online'] else 'SEM RESPOSTA'}"
    )

    print()

    for field_name, value in result["dados"].items():
        label = field_name.replace("_", " ").title()

        print(
            f"{label:<20}: "
            f"{value if value is not None else 'Não informado'}"
        )


def save_result(
    result: dict,
    output_file: Path,
) -> None:
    output_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_file.write_text(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "PRINTFLOW Agent — Consulta SNMP básica "
            "de impressoras"
        )
    )

    parser.add_argument(
        "ip",
        help="IP da impressora.",
    )

    parser.add_argument(
        "--community",
        default="public",
        help="Comunidade SNMP. Padrão: public.",
    )

    parser.add_argument(
        "--timeout",
        type=float,
        default=1.0,
        help="Timeout em segundos.",
    )

    parser.add_argument(
        "--retries",
        type=int,
        default=1,
        help="Quantidade de novas tentativas.",
    )

    parser.add_argument(
        "--output",
        default="agent/python/output/snmp_result.json",
        help="Arquivo JSON de saída.",
    )

    return parser.parse_args()


async def main() -> int:
    arguments = parse_arguments()

    result = await collect_printer(
        ip_address=arguments.ip,
        community=arguments.community,
        timeout=arguments.timeout,
        retries=arguments.retries,
    )

    print_result(result)

    save_result(
        result=result,
        output_file=Path(arguments.output),
    )

    print()
    print(
        f"Resultado salvo em: {arguments.output}"
    )

    return 0 if result["snmp_online"] else 2


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
