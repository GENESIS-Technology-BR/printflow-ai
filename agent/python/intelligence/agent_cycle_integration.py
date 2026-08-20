from __future__ import annotations

import atexit
import json
import os
import sys
import threading
from pathlib import Path
from typing import Any

from intelligence.printer_intelligence_collector import (
    PrinterIntelligenceReport,
    build_report,
    save_reports,
)


OUTPUT_NAME = "PRINTFLOW-Printer-Intelligence.json"

_LOCK = threading.Lock()
_INSTALLED = False
_RUNNING = False


def _valid_ip(value: Any) -> str | None:
    if value is None:
        return None

    text = str(value).strip()
    parts = text.split(".")

    if len(parts) != 4:
        return None

    try:
        numbers = [int(part) for part in parts]
    except ValueError:
        return None

    if not all(0 <= number <= 255 for number in numbers):
        return None

    return ".".join(str(number) for number in numbers)


def _inventory_rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [
            item
            for item in payload
            if isinstance(item, dict)
        ]

    if not isinstance(payload, dict):
        return []

    for key in (
        "printers",
        "impressoras",
        "devices",
        "equipamentos",
        "inventory",
        "inventario",
        "items",
        "results",
        "dados",
    ):
        value = payload.get(key)

        if isinstance(value, list):
            return [
                item
                for item in value
                if isinstance(item, dict)
            ]

    if any(
        key in payload
        for key in (
            "ip",
            "ip_address",
            "endereco_ip",
            "host",
            "address",
        )
    ):
        return [payload]

    return []


def _extract_ips(payload: Any) -> list[str]:
    result: list[str] = []

    for row in _inventory_rows(payload):
        discovery = row.get("discovery")
        snmp = row.get("snmp")

        if not isinstance(discovery, dict):
            discovery = {}

        if not isinstance(snmp, dict):
            snmp = {}

        raw_candidates = (
            row.get("ip_address"),
            row.get("ip"),
            row.get("endereco_ip"),
            row.get("host"),
            row.get("address"),
            discovery.get("ip_address"),
            discovery.get("ip"),
            snmp.get("ip_address"),
            snmp.get("ip"),
        )

        for raw in raw_candidates:
            ip_address = _valid_ip(raw)

            if (
                ip_address
                and ip_address not in result
            ):
                result.append(ip_address)
                break

    return result


def _find_inventory() -> Path | None:
    configured = os.getenv("PRINTFLOW_INVENTORY_PATH")
    candidates: list[Path] = []

    if configured:
        candidates.append(Path(configured))

    executable_dir = Path(sys.executable).resolve().parent
    module_root = Path(__file__).resolve().parents[1]

    candidates.extend(
        [
            module_root / "output" / "agent_inventory.json",
            module_root / "agent_inventory.json",
            Path.cwd() / "agent_inventory.json",
            Path.cwd() / "output" / "agent_inventory.json",
            Path.cwd() / "agent" / "python"
            / "output" / "agent_inventory.json",
            executable_dir / "agent_inventory.json",
            executable_dir / "output" / "agent_inventory.json",
        ]
    )

    visited: set[str] = set()

    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except OSError:
            continue

        key = str(resolved).lower()

        if key in visited:
            continue

        visited.add(key)

        if resolved.is_file():
            return resolved

    return None


def build_reports_from_inventory(
    payload: Any,
) -> list[PrinterIntelligenceReport]:
    reports: list[PrinterIntelligenceReport] = []

    for row in _inventory_rows(payload):
        discovery = row.get("discovery")
        snmp = row.get("snmp")

        if not isinstance(discovery, dict):
            discovery = {}

        if not isinstance(snmp, dict):
            snmp = {}

        primary = snmp.get("dados")

        if not isinstance(primary, dict):
            primary = row

        ip_address = _valid_ip(
            discovery.get("ip_address")
            or snmp.get("ip_address")
            or row.get("ip_address")
            or row.get("ip")
        )

        if not ip_address:
            continue

        learning = primary.get("learning_diagnostic")

        if not isinstance(learning, dict):
            learning = {}

        reports.append(
            build_report(
                ip_address=ip_address,
                primary=primary,
                learning=learning,
            )
        )

    return reports


def generate_from_inventory(
    *,
    inventory_path: str | Path | None = None,
    destination: str | Path | None = None,
) -> Path | None:
    inventory = (
        Path(inventory_path).resolve()
        if inventory_path
        else _find_inventory()
    )

    if inventory is None or not inventory.is_file():
        print(
            "[Printer Intelligence] "
            "agent_inventory.json nao encontrado. "
            "Diagnostico ignorado sem afetar o Agent."
        )
        return None

    try:
        original_content = inventory.read_text(
            encoding="utf-8"
        )
        payload = json.loads(original_content)
    except Exception as exc:
        print(
            "[Printer Intelligence] "
            "inventario invalido: "
            f"{type(exc).__name__}: {exc}"
        )
        return None

    ip_addresses = _extract_ips(payload)

    output_path = (
        Path(destination).resolve()
        if destination
        else inventory.parent / OUTPUT_NAME
    )

    if not ip_addresses:
        output_path.write_text(
            json.dumps(
                {
                    "schema": (
                        "printflow-printer-intelligence-v1"
                    ),
                    "total": 0,
                    "source_inventory": str(inventory),
                    "inventory_preserved": True,
                    "warning": (
                        "Nenhum IPv4 foi encontrado "
                        "no inventario."
                    ),
                    "printers": [],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        print(
            "[Printer Intelligence] "
            f"JSON gerado: {output_path}"
        )
        return output_path

    print(
        "[Printer Intelligence] "
        f"normalizando {len(ip_addresses)} impressora(s) "
        "do inventario existente."
    )

    try:
        reports = build_reports_from_inventory(payload)

        saved_path = save_reports(
            reports=reports,
            destination=output_path,
        )

        diagnostic = json.loads(
            saved_path.read_text(encoding="utf-8")
        )

        diagnostic["source_inventory"] = str(inventory)
        diagnostic["inventory_preserved"] = True
        diagnostic["second_snmp_collection"] = False

        saved_path.write_text(
            json.dumps(
                diagnostic,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        if inventory.read_text(encoding="utf-8") != original_content:
            raise RuntimeError(
                "O inventario original foi alterado."
            )

        print(
            "[Printer Intelligence] "
            f"diagnostico gerado: {saved_path}"
        )

        return saved_path

    except BaseException as exc:
        print(
            "[Printer Intelligence] "
            "falha isolada: "
            f"{type(exc).__name__}: {exc}"
        )
        return None


def _run_at_exit() -> None:
    global _RUNNING

    if _RUNNING:
        return

    _RUNNING = True

    try:
        generate_from_inventory()
    except BaseException as exc:
        print(
            "[Printer Intelligence] "
            "erro isolado no encerramento: "
            f"{type(exc).__name__}: {exc}"
        )
    finally:
        _RUNNING = False


def install_agent_cycle_hook() -> bool:
    global _INSTALLED

    with _LOCK:
        if _INSTALLED:
            return False

        disabled = os.getenv(
            "PRINTFLOW_DISABLE_PRINTER_INTELLIGENCE",
            "",
        ).strip().lower()

        if disabled in {
            "1",
            "true",
            "yes",
            "sim",
        }:
            print(
                "[Printer Intelligence] "
                "integracao desativada."
            )
            return False

        atexit.register(_run_at_exit)
        _INSTALLED = True

        print(
            "[Printer Intelligence] "
            "integracao registrada no ciclo do Agent."
        )

        return True
