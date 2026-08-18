from __future__ import annotations

import asyncio
import ipaddress
import time
from dataclasses import dataclass
from typing import Any

from pysnmp.hlapi.v3arch.asyncio import (
    CommunityData,
    ContextData,
    ObjectIdentity,
    ObjectType,
    SnmpEngine,
    UdpTransportTarget,
    get_cmd,
    walk_cmd,
)

from intelligence.snmp_safe_walk import (
    WalkAnalysis,
    WalkPolicy,
    WalkRow,
    analyse_rows,
    build_learning_roots,
)


SYS_OBJECT_ID = "1.3.6.1.2.1.1.2.0"


@dataclass
class SafeWalkResult:
    ip_address: str
    sys_object_id: str | None
    analysis: WalkAnalysis
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "ip_address": self.ip_address,
            "sys_object_id": self.sys_object_id,
            "analysis": self.analysis.to_dict(),
            "error": self.error,
        }


def validate_private_ipv4(
    value: str,
) -> str:

    ip = ipaddress.ip_address(
        str(value).strip()
    )

    if ip.version != 4:
        raise ValueError(
            "Somente IPv4 permitido."
        )

    if not ip.is_private:
        raise ValueError(
            "Somente IPv4 privado permitido."
        )

    return str(ip)


async def _get_value(
    *,
    engine: SnmpEngine,
    target: Any,
    community: str,
    oid: str,
) -> str | None:

    result = await get_cmd(
        engine,
        CommunityData(
            community,
            mpModel=1,
        ),
        target,
        ContextData(),
        ObjectType(
            ObjectIdentity(oid)
        ),
        lookupMib=False,
    )

    (
        error_indication,
        error_status,
        error_index,
        var_binds,
    ) = result

    if error_indication:
        return None

    if error_status:
        return None

    if not var_binds:
        return None

    try:
        return (
            var_binds[0][1]
            .prettyPrint()
        )
    except Exception:
        return str(
            var_binds[0][1]
        )


async def _walk_root(
    *,
    engine: SnmpEngine,
    target: Any,
    community: str,
    root: str,
    max_rows: int,
    deadline: float,
) -> list[WalkRow]:

    rows: list[WalkRow] = []

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

        if time.monotonic() >= deadline:
            break

        if error_indication:
            break

        if error_status:
            break

        for oid, value in var_binds:

            rows.append(
                WalkRow(
                    oid=oid.prettyPrint(),
                    value=value.prettyPrint(),
                )
            )

            if len(rows) >= max_rows:
                return rows

    return rows


async def safe_walk_printer(
    *,
    ip_address: str,
    community: str = "public",
    timeout: float = 1.0,
    retries: int = 0,
    policy: WalkPolicy | None = None,
) -> SafeWalkResult:

    target_ip = validate_private_ipv4(
        ip_address
    )

    active_policy = (
        policy
        or WalkPolicy()
    )

    engine = SnmpEngine()

    try:

        target = await UdpTransportTarget.create(
            (target_ip, 161),
            timeout=timeout,
            retries=retries,
        )

        sys_object_id = await _get_value(
            engine=engine,
            target=target,
            community=community,
            oid=SYS_OBJECT_ID,
        )

        roots = build_learning_roots(
            sys_object_id
        )

        deadline = (
            time.monotonic()
            + active_policy.max_seconds
        )

        all_rows: list[WalkRow] = []

        remaining = (
            active_policy.max_rows
        )

        for root in roots:

            if remaining <= 0:
                break

            if time.monotonic() >= deadline:
                break

            rows = await _walk_root(
                engine=engine,
                target=target,
                community=community,
                root=root,
                max_rows=remaining,
                deadline=deadline,
            )

            all_rows.extend(rows)

            remaining = (
                active_policy.max_rows
                - len(all_rows)
            )

        analysis = analyse_rows(
            roots=roots,
            rows=all_rows,
            policy=active_policy,
        )

        return SafeWalkResult(
            ip_address=target_ip,
            sys_object_id=sys_object_id,
            analysis=analysis,
        )

    except Exception as exc:

        empty = WalkAnalysis(
            roots=[],
            rows_seen=0,
            candidates=[],
            truncated=False,
        )

        return SafeWalkResult(
            ip_address=target_ip,
            sys_object_id=None,
            analysis=empty,
            error=(
                f"{type(exc).__name__}: "
                f"{exc}"
            ),
        )

    finally:

        try:
            engine.close_dispatcher()
        except Exception:
            pass
