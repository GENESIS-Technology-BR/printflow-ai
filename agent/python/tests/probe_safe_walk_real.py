from __future__ import annotations

import argparse
import asyncio
import ipaddress
import time
from typing import Any

from pysnmp.hlapi.v3arch.asyncio import (
    CommunityData,
    ContextData,
    ObjectIdentity,
    ObjectType,
    SnmpEngine,
    UdpTransportTarget,
    walk_cmd,
)

DEFAULT_ROOTS = (
    "1.3.6.1.2.1.43",       # Printer-MIB
    "1.3.6.1.4.1",          # Enterprise
)

MAX_ROWS_PER_ROOT = 120
MAX_TOTAL_SECONDS = 8.0


def validate_target(value: str) -> str:
    ip = ipaddress.ip_address(value.strip())

    if not ip.is_private:
        raise ValueError("Somente IPv4 privado e permitido.")

    if ip.version != 4:
        raise ValueError("Somente IPv4 e permitido.")

    return str(ip)


def clean_value(value: Any) -> str:
    try:
        return value.prettyPrint()
    except Exception:
        return str(value)


async def walk_root(
    ip_address: str,
    community: str,
    root: str,
) -> list[tuple[str, str]]:

    engine = SnmpEngine()

    target = await UdpTransportTarget.create(
        (ip_address, 161),
        timeout=1.0,
        retries=0,
    )

    rows: list[tuple[str, str]] = []

    try:
        iterator = walk_cmd(
            engine,
            CommunityData(
                community,
                mpModel=1,
            ),
            target,
            ContextData(),
            ObjectType(
                ObjectIdentity(root)
            ),
            lexicographicMode=False,
            lookupMib=False,
        )

        async for (
            error_indication,
            error_status,
            error_index,
            var_binds,
        ) in iterator:

            if error_indication:
                print(
                    f"[ERRO] {root}: "
                    f"{error_indication}"
                )
                break

            if error_status:
                print(
                    f"[ERRO] {root}: "
                    f"{error_status.prettyPrint()}"
                )
                break

            for oid, value in var_binds:
                oid_text = oid.prettyPrint()
                value_text = clean_value(value)

                rows.append(
                    (oid_text, value_text)
                )

                if len(rows) >= MAX_ROWS_PER_ROOT:
                    return rows

    finally:
        try:
            engine.close_dispatcher()
        except Exception:
            pass

    return rows


def interesting(
    oid: str,
    value: str,
) -> bool:

    text = value.strip()

    if not text:
        return False

    low = text.lower()

    keywords = (
        "serial",
        "zebra",
        "zt230",
        "zd230",
        "model",
        "counter",
        "count",
        "print",
        "page",
    )

    if any(k in low for k in keywords):
        return True

    if len(text) >= 6 and any(c.isdigit() for c in text):
        return True

    return False


async def main() -> int:

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--ip",
        required=True,
    )

    parser.add_argument(
        "--community",
        default="public",
    )

    args = parser.parse_args()

    target = validate_target(args.ip)

    print("=" * 60)
    print("PRINTFLOW SAFE WALK REAL")
    print("SOMENTE LEITURA")
    print("IP:", target)
    print("=" * 60)

    started = time.monotonic()

    total_rows = 0
    candidates: list[tuple[str, str]] = []

    for root in DEFAULT_ROOTS:

        elapsed = time.monotonic() - started

        if elapsed >= MAX_TOTAL_SECONDS:
            print()
            print("LIMITE GLOBAL DE TEMPO ATINGIDO")
            break

        print()
        print("ROOT:", root)

        try:
            rows = await asyncio.wait_for(
                walk_root(
                    target,
                    args.community,
                    root,
                ),
                timeout=max(
                    1.0,
                    MAX_TOTAL_SECONDS - elapsed,
                ),
            )

        except asyncio.TimeoutError:
            print("TIMEOUT CONTROLADO")
            continue

        total_rows += len(rows)

        print(
            "ROWS:",
            len(rows),
        )

        for oid, value in rows:

            if interesting(oid, value):
                candidates.append(
                    (oid, value)
                )

    print()
    print("=" * 60)
    print("CANDIDATOS ENCONTRADOS")
    print("=" * 60)

    if not candidates:
        print("Nenhum candidato encontrado.")

    else:
        for oid, value in candidates[:80]:
            print(
                f"{oid} = {value}"
            )

    print()
    print("=" * 60)
    print("RESUMO")
    print("=" * 60)
    print("ROWS TOTAL:", total_rows)
    print(
        "CANDIDATOS:",
        len(candidates),
    )
    print(
        "TEMPO:",
        round(
            time.monotonic() - started,
            2,
        ),
        "s",
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        asyncio.run(main())
    )
