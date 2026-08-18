from __future__ import annotations

import argparse
import asyncio
import ipaddress
import json
import platform
import socket

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


# ============================================================
# PRINTFLOW DIAGNOSTIC ROBOT
#
# IMPORTANTE:
# - nao executa shell arbitrario;
# - nao executa PowerShell recebido do servidor;
# - nao aceita comandos livres;
# - somente jobs internos previamente autorizados.
# ============================================================

ALLOWED_JOBS = {
    "SYSTEM_INFO",
    "DISCOVER_NETWORKS",
    "SCAN_PRINTERS",
    "DIAGNOSE_PRINTER",
    "READ_SNMP",
    "CHECK_COUNTERS",
    "CHECK_SERIAL",
    "CHECK_SUPPLIES",
    "SNMP_LEARN",
    "TEST_API",
    "SEND_DIAGNOSTICS",
    "REFRESH_INVENTORY",
}


@dataclass
class DiagnosticResult:
    job: str
    success: bool
    generated_at: str
    data: dict[str, Any]
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _now() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


def _validate_private_ip(
    value: str,
) -> str:

    ip = ipaddress.ip_address(
        str(value).strip()
    )

    if not (
        ip.is_private
        or ip.is_link_local
        or ip.is_loopback
    ):
        raise ValueError(
            "O Diagnostic Robot somente permite "
            "diagnostico de enderecos locais/privados."
        )

    return str(ip)


def _serialize_network(
    network: Any,
) -> dict[str, Any]:

    fields = (
        "cidr",
        "original_cidr",
        "interface",
        "interface_name",
        "ip_address",
        "gateway",
        "source",
        "reason",
    )

    result: dict[str, Any] = {}

    for field in fields:

        value = getattr(
            network,
            field,
            None,
        )

        if value is not None:
            result[field] = str(value)

    if not result:
        result["value"] = str(network)

    return result


async def _collect_printer(
    ip_address: str,
    community: str,
    timeout: float,
    retries: int,
) -> dict[str, Any]:

    # Import tardio:
    # evita carregar SNMP quando o job nao precisa.
    from snmp.engine import (
        collect_printer_intelligence,
    )

    result = await collect_printer_intelligence(
        ip_address=ip_address,
        community=community,
        timeout=timeout,
        retries=retries,
    )

    if not isinstance(
        result,
        dict,
    ):
        raise RuntimeError(
            "Motor SNMP retornou formato inesperado."
        )

    return result


class DiagnosticRobot:

    def __init__(self) -> None:

        self._handlers: dict[
            str,
            Callable[..., dict[str, Any]],
        ] = {}

        self.register(
            "SYSTEM_INFO",
            self._system_info,
        )

        self.register(
            "DISCOVER_NETWORKS",
            self._discover_networks,
        )

        self.register(
            "DIAGNOSE_PRINTER",
            self._diagnose_printer,
        )

        self.register(
            "READ_SNMP",
            self._diagnose_printer,
        )

        self.register(
            "CHECK_COUNTERS",
            self._check_counters,
        )

        self.register(
            "CHECK_SERIAL",
            self._check_serial,
        )

        self.register(
            "CHECK_SUPPLIES",
            self._check_supplies,
        )

        self.register(
            "SNMP_LEARN",
            self._snmp_learn,
        )

    def register(
        self,
        job: str,
        handler: Callable[..., dict[str, Any]],
    ) -> None:

        normalized = str(
            job
        ).strip().upper()

        if normalized not in ALLOWED_JOBS:

            raise ValueError(
                f"Job nao autorizado: {normalized}"
            )

        self._handlers[
            normalized
        ] = handler

    def available_jobs(
        self,
    ) -> list[str]:

        return sorted(
            self._handlers
        )

    def execute(
        self,
        job: str,
        **kwargs: Any,
    ) -> DiagnosticResult:

        normalized = str(
            job
        ).strip().upper()

        if normalized not in ALLOWED_JOBS:

            return DiagnosticResult(
                job=normalized,
                success=False,
                generated_at=_now(),
                data={},
                error=(
                    "Job rejeitado pelo "
                    "PRINTFLOW Diagnostic Robot."
                ),
            )

        handler = self._handlers.get(
            normalized
        )

        if handler is None:

            return DiagnosticResult(
                job=normalized,
                success=False,
                generated_at=_now(),
                data={},
                error=(
                    "Job permitido, mas ainda "
                    "nao implementado nesta versao."
                ),
            )

        try:

            data = handler(
                **kwargs
            )

            return DiagnosticResult(
                job=normalized,
                success=True,
                generated_at=_now(),
                data=data,
            )

        except Exception as exc:

            return DiagnosticResult(
                job=normalized,
                success=False,
                generated_at=_now(),
                data={},
                error=(
                    f"{type(exc).__name__}: {exc}"
                ),
            )

    # ========================================================
    # SYSTEM INFO
    # ========================================================

    @staticmethod
    def _system_info(
        **_: Any,
    ) -> dict[str, Any]:

        return {
            "hostname": socket.gethostname(),
            "platform": platform.system(),
            "platform_release": platform.release(),
            "machine": platform.machine(),
            "python_runtime": platform.python_version(),
        }

    # ========================================================
    @staticmethod
    def _snmp_learn(
        *,
        ip_address: str,
        vendor: str | None = None,
        getter_factory: Any = None,
        **_: Any,
    ) -> dict[str, Any]:

        from intelligence.diagnostic_learning_bridge import (
            ALLOWED_LEARNING_JOB,
            DiagnosticLearningRequest,
            execute_learning_job,
        )

        import asyncio

        if getter_factory is None:
            return {
                "success": False,
                "job": ALLOWED_LEARNING_JOB,
                "ip_address": ip_address,
                "vendor": vendor,
                "report": None,
                "error": "getter_factory obrigatorio nesta etapa.",
            }

        request = DiagnosticLearningRequest(
            job=ALLOWED_LEARNING_JOB,
            ip_address=ip_address,
            vendor=vendor,
        )

        async def run_learning():
            return await execute_learning_job(
                request=request,
                getter_factory=getter_factory,
            )

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            response = asyncio.run(
                run_learning()
            )
            return response.to_dict()

        return {
            "success": False,
            "job": ALLOWED_LEARNING_JOB,
            "ip_address": ip_address,
            "vendor": vendor,
            "report": None,
            "error": "Event loop ativo; execucao real sera integrada na proxima etapa.",
        }


    # DISCOVER NETWORKS
    # ========================================================

    @staticmethod
    def _discover_networks(
        **_: Any,
    ) -> dict[str, Any]:

        from network_manager import (
            detect_local_networks,
        )

        networks = detect_local_networks()

        serialized = [
            _serialize_network(
                network
            )
            for network in networks
        ]

        return {
            "total": len(serialized),
            "networks": serialized,
        }

    # ========================================================
    # FULL PRINTER DIAGNOSTIC
    # ========================================================

    @staticmethod
    def _diagnose_printer(
        *,
        ip_address: str,
        community: str = "public",
        timeout: float = 2.0,
        retries: int = 1,
        **_: Any,
    ) -> dict[str, Any]:

        validated_ip = _validate_private_ip(
            ip_address
        )

        result = asyncio.run(
            _collect_printer(
                ip_address=validated_ip,
                community=community,
                timeout=float(timeout),
                retries=int(retries),
            )
        )

        return {
            "ip_address": validated_ip,
            "diagnostic": result,
        }

    # ========================================================
    # COUNTER
    # ========================================================

    @classmethod
    def _check_counters(
        cls,
        **kwargs: Any,
    ) -> dict[str, Any]:

        result = cls._diagnose_printer(
            **kwargs
        )

        diagnostic = (
            result.get(
                "diagnostic"
            )
            or {}
        )

        data = (
            diagnostic.get(
                "dados"
            )
            or {}
        )

        return {
            "ip_address": result["ip_address"],
            "snmp_online": diagnostic.get(
                "snmp_online"
            ),
            "contador_paginas": data.get(
                "contador_paginas"
            ),
            "contador_origem": data.get(
                "contador_origem"
            ),
            "contador_candidatos": data.get(
                "contador_candidatos"
            ),
        }

    # ========================================================
    # SERIAL
    # ========================================================

    @classmethod
    def _check_serial(
        cls,
        **kwargs: Any,
    ) -> dict[str, Any]:

        result = cls._diagnose_printer(
            **kwargs
        )

        diagnostic = (
            result.get(
                "diagnostic"
            )
            or {}
        )

        data = (
            diagnostic.get(
                "dados"
            )
            or {}
        )

        return {
            "ip_address": result["ip_address"],
            "snmp_online": diagnostic.get(
                "snmp_online"
            ),
            "fabricante": data.get(
                "fabricante"
            ),
            "modelo": data.get(
                "modelo"
            ),
            "serial": data.get(
                "serial"
            ),
            "identity_confidence": data.get(
                "identity_confidence"
            ),
        }

    # ========================================================
    # SUPPLIES
    # ========================================================

    @classmethod
    def _check_supplies(
        cls,
        **kwargs: Any,
    ) -> dict[str, Any]:

        result = cls._diagnose_printer(
            **kwargs
        )

        diagnostic = (
            result.get(
                "diagnostic"
            )
            or {}
        )

        data = (
            diagnostic.get(
                "dados"
            )
            or {}
        )

        return {
            "ip_address": result["ip_address"],
            "snmp_online": diagnostic.get(
                "snmp_online"
            ),
            "toner_percentual": data.get(
                "toner_percentual"
            ),
            "suprimentos": data.get(
                "suprimentos"
            ),
        }


def save_result(
    result: DiagnosticResult,
    output_file: Path,
) -> None:

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_file.write_text(
        json.dumps(
            result.to_dict(),
            indent=2,
            ensure_ascii=False,
            default=str,
        ),
        encoding="utf-8",
    )


def cli() -> int:

    parser = argparse.ArgumentParser(
        description=(
            "PRINTFLOW Diagnostic Robot"
        )
    )

    parser.add_argument(
        "job",
        help="Job PRINTFLOW autorizado.",
    )

    parser.add_argument(
        "--ip",
        dest="ip_address",
        default=None,
        help="IP privado da impressora.",
    )

    parser.add_argument(
        "--community",
        default="public",
    )

    parser.add_argument(
        "--output",
        default=None,
    )

    args = parser.parse_args()

    robot = DiagnosticRobot()

    kwargs: dict[str, Any] = {}

    if args.ip_address:
        kwargs["ip_address"] = (
            args.ip_address
        )

    if args.community:
        kwargs["community"] = (
            args.community
        )

    result = robot.execute(
        args.job,
        **kwargs,
    )

    print(
        json.dumps(
            result.to_dict(),
            indent=2,
            ensure_ascii=False,
            default=str,
        )
    )

    if args.output:

        save_result(
            result,
            Path(args.output),
        )

    return (
        0
        if result.success
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(
        cli()
    )
