from __future__ import annotations

import ipaddress
from dataclasses import dataclass, asdict
from typing import Any, Awaitable, Callable

from intelligence.snmp_learning import (
    learn_printer_identity,
)
from intelligence.snmp_normalizer import (
    normalize_vendor,
)


ALLOWED_LEARNING_JOB = "SNMP_LEARN"


@dataclass
class DiagnosticLearningRequest:
    job: str
    ip_address: str
    vendor: str | None = None


@dataclass
class DiagnosticLearningResponse:
    success: bool
    job: str
    ip_address: str
    vendor: str | None
    report: dict[str, Any] | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def validate_private_target(
    ip_address: str,
) -> str:
    try:
        ip = ipaddress.ip_address(
            str(ip_address).strip()
        )
    except ValueError as exc:
        raise ValueError(
            "IP invalido."
        ) from exc

    if not isinstance(
        ip,
        ipaddress.IPv4Address,
    ):
        raise ValueError(
            "Somente IPv4 e permitido."
        )

    if not ip.is_private:
        raise ValueError(
            "Somente IP privado e permitido."
        )

    if (
        ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_unspecified
    ):
        raise ValueError(
            "Endereco IPv4 nao permitido."
        )

    return str(ip)


async def execute_learning_job(
    request: DiagnosticLearningRequest,
    getter_factory: Callable[
        [str],
        Callable[
            [str],
            Awaitable[Any],
        ],
    ],
) -> DiagnosticLearningResponse:

    if request.job != ALLOWED_LEARNING_JOB:
        return DiagnosticLearningResponse(
            success=False,
            job=request.job,
            ip_address=request.ip_address,
            vendor=request.vendor,
            error=(
                "Job nao autorizado pelo "
                "PRINTFLOW Diagnostic Robot."
            ),
        )

    try:
        target = validate_private_target(
            request.ip_address
        )

    except ValueError as exc:
        return DiagnosticLearningResponse(
            success=False,
            job=request.job,
            ip_address=request.ip_address,
            vendor=request.vendor,
            error=str(exc),
        )

    vendor = normalize_vendor(
        request.vendor
    )

    getter = getter_factory(
        target
    )

    try:
        report = await learn_printer_identity(
            vendor=vendor,
            getter=getter,
        )

    except Exception as exc:
        return DiagnosticLearningResponse(
            success=False,
            job=request.job,
            ip_address=target,
            vendor=vendor,
            error=(
                f"Falha no SNMP Learning: "
                f"{type(exc).__name__}: {exc}"
            ),
        )

    return DiagnosticLearningResponse(
        success=True,
        job=request.job,
        ip_address=target,
        vendor=vendor,
        report=report.to_dict(),
    )
