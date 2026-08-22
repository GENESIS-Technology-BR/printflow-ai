from __future__ import annotations

import asyncio
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


# ============================================================
# PRINTFLOW - PRINTER INTELLIGENCE COLLECTOR
#
# Objetivos:
# - preservar dados confiaveis existentes;
# - nunca confundir descricao/modelo com serial;
# - registrar origem e confianca;
# - separar contador de paginas de outros contadores;
# - permitir evolucao por fabricante;
# - produzir diagnostico JSON reutilizavel.
# ============================================================


KNOWN_VENDOR_NAMES = (
    "zebra",
    "canon",
    "hp",
    "hewlett",
    "ricoh",
    "kyocera",
    "brother",
    "epson",
    "lexmark",
    "xerox",
    "samsung",
)


MODEL_DESCRIPTION_TERMS = (
    "zpl",
    "printer",
    "printing",
    "technologies",
    "series",
    "document solutions",
    "laser",
    "203dpi",
    "300dpi",
    "600dpi",
)


@dataclass
class IntelligenceValue:
    value: Any
    source: str
    confidence: int
    value_type: str
    confirmed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PrinterIntelligenceReport:
    ip_address: str

    manufacturer: IntelligenceValue | None
    model: IntelligenceValue | None
    serial: IntelligenceValue | None
    counter: IntelligenceValue | None
    toner: IntelligenceValue | None

    sys_object_id: str | None

    serial_candidates: list[dict[str, Any]]
    counter_candidates: list[dict[str, Any]]

    learning_error: str | None

    generated_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "ip_address": self.ip_address,
            "manufacturer": (
                self.manufacturer.to_dict()
                if self.manufacturer
                else None
            ),
            "model": (
                self.model.to_dict()
                if self.model
                else None
            ),
            "serial": (
                self.serial.to_dict()
                if self.serial
                else None
            ),
            "counter": (
                self.counter.to_dict()
                if self.counter
                else None
            ),
            "toner": (
                self.toner.to_dict()
                if self.toner
                else None
            ),
            "sys_object_id": self.sys_object_id,
            "serial_candidates": self.serial_candidates,
            "counter_candidates": self.counter_candidates,
            "learning_error": self.learning_error,
            "generated_at": self.generated_at,
        }


def utc_now() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


def clean_text(
    value: Any,
) -> str | None:

    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    invalid = {
        "none",
        "null",
        "unknown",
        "n/a",
        "na",
        "-1",
        "0",
    }

    if text.lower() in invalid:
        return None

    return text


def normalize_vendor(
    value: Any,
) -> str | None:

    text = clean_text(value)

    if not text:
        return None

    low = text.lower()

    if "zebra" in low:
        return "Zebra"

    if "canon" in low:
        return "Canon"

    if (
        "hewlett" in low
        or low == "hp"
        or low.startswith("hp ")
    ):
        return "HP"

    if "ricoh" in low:
        return "Ricoh"

    if "kyocera" in low:
        return "Kyocera"

    if "brother" in low:
        return "Brother"

    if "epson" in low:
        return "Epson"

    if "lexmark" in low:
        return "Lexmark"

    if "xerox" in low:
        return "Xerox"

    if "samsung" in low:
        return "Samsung"

    return text[:80]


def looks_like_model_description(
    value: str,
) -> bool:

    low = value.lower()

    if any(
        term in low
        for term in MODEL_DESCRIPTION_TERMS
    ):
        return True

    if value.count(" ") >= 2:
        return True

    return False


def validate_serial(
    value: Any,
) -> tuple[
    bool,
    int,
    str,
]:

    text = clean_text(value)

    if not text:
        return (
            False,
            0,
            "Serial vazio.",
        )

    if len(text) < 5:
        return (
            False,
            0,
            "Serial muito curto.",
        )

    if len(text) > 64:
        return (
            False,
            0,
            "Serial muito longo.",
        )

    # Bloqueia placeholders hexadecimais sem identidade real.
    # Caso real encontrado nas Ricoh M 320F:
    # 0x000000000000
    if re.fullmatch(r"0x0+", text.lower()):
        return (
            False,
            0,
            "Placeholder hexadecimal sem serial.",
        )

    # Bloqueia o caso real encontrado nas Zebra:
    # ZTC ZT230-203dpi ZPL
    if looks_like_model_description(text):
        return (
            False,
            10,
            "Parece descricao ou modelo.",
        )

    if " " in text:
        return (
            False,
            20,
            "Serial contem espacos.",
        )

    has_letter = bool(
        re.search(
            r"[A-Za-z]",
            text,
        )
    )

    has_number = bool(
        re.search(
            r"\d",
            text,
        )
    )

    if (
        has_letter
        and has_number
        and 7 <= len(text) <= 32
    ):
        return (
            True,
            95,
            "Serial alfanumerico forte.",
        )

    if (
        text.isdigit()
        and 7 <= len(text) <= 24
    ):
        return (
            True,
            80,
            "Serial numerico plausivel.",
        )

    return (
        False,
        30,
        "Baixa confianca como serial.",
    )


def normalize_counter(
    value: Any,
) -> int | None:

    if value is None:
        return None

    if isinstance(
        value,
        bool,
    ):
        return None

    try:
        number = int(
            str(value)
            .replace(",", "")
            .strip()
        )

    except (
        TypeError,
        ValueError,
    ):
        return None

    if number < 0:
        return None

    if number > 10_000_000_000:
        return None

    return number


def best_serial_candidate(
    candidates: Iterable[
        dict[str, Any]
    ],
    manufacturer: str | None = None,
) -> IntelligenceValue | None:

    candidate_list = list(candidates)

    if manufacturer == "Ricoh":
        ricoh_serial_oids = {
            "1.3.6.1.4.1.367.3.2.1.2.1.4.0",
        }

        for candidate in candidate_list:
            oid = str(candidate.get("oid") or "")
            value = candidate.get("value")

            if oid not in ricoh_serial_oids:
                continue

            valid, score, _ = validate_serial(value)

            if valid:
                return IntelligenceValue(
                    value=str(value).strip(),
                    source="ricoh-enterprise-oid",
                    confidence=max(score, 99),
                    value_type="serial",
                    confirmed=True,
                )

    if manufacturer == "Zebra":
        for candidate in candidate_list:
            oid = str(candidate.get("oid") or "")
            value = candidate.get("value")

            if oid != "1.3.6.1.4.1.10642.1.4.0":
                continue

            valid, score, _ = validate_serial(value)

            if valid:
                return IntelligenceValue(
                    value=str(value).strip(),
                    source="zebra-enterprise-oid",
                    confidence=max(score, 99),
                    value_type="serial",
                    confirmed=True,
                )

    ranked: list[
        tuple[
            int,
            str,
            dict[str, Any],
        ]
    ] = []

    for candidate in candidate_list:

        value = candidate.get(
            "value"
        )

        valid, local_score, reason = (
            validate_serial(
                value
            )
        )

        if not valid:
            continue

        source_score = int(
            candidate.get(
                "confidence",
                0,
            )
            or 0
        )

        final_score = min(
            max(
                local_score,
                source_score,
            ),
            100,
        )

        ranked.append(
            (
                final_score,
                str(value),
                {
                    **candidate,
                    "validation_reason": reason,
                },
            )
        )

    if not ranked:
        return None

    ranked.sort(
        key=lambda item: (
            -item[0],
            item[1],
        )
    )

    score, value, _ = ranked[0]

    return IntelligenceValue(
        value=value,
        source="snmp-learning",
        confidence=score,
        value_type="serial",
        confirmed=False,
    )


def build_report(
    *,
    ip_address: str,
    primary: dict[str, Any],
    learning: dict[str, Any] | None = None,
) -> PrinterIntelligenceReport:

    learning = (
        learning
        or {}
    )

    manufacturer_raw = (
        primary.get("fabricante")
        or primary.get("manufacturer")
    )

    model_raw = (
        primary.get("modelo")
        or primary.get("model")
    )

    serial_raw = primary.get(
        "serial"
    )

    counter_raw = (
        primary.get(
            "contador_paginas"
        )
        if "contador_paginas" in primary
        else primary.get(
            "page_count"
        )
    )

    toner_raw = (
        primary.get(
            "toner_percentual"
        )
        if "toner_percentual" in primary
        else primary.get(
            "toner"
        )
    )

    manufacturer_value = (
        normalize_vendor(
            manufacturer_raw
        )
    )

    manufacturer = (
        IntelligenceValue(
            value=manufacturer_value,
            source="snmp-primary",
            confidence=100,
            value_type="manufacturer",
            confirmed=True,
        )
        if manufacturer_value
        else None
    )

    model_text = clean_text(
        model_raw
    )

    model = (
        IntelligenceValue(
            value=model_text,
            source="snmp-primary",
            confidence=100,
            value_type="model",
            confirmed=True,
        )
        if model_text
        else None
    )

    serial = None

    serial_valid, serial_score, _ = (
        validate_serial(
            serial_raw
        )
    )

    if serial_valid:
        serial = IntelligenceValue(
            value=str(
                serial_raw
            ).strip(),
            source="snmp-primary",
            confidence=serial_score,
            value_type="serial",
            confirmed=True,
        )

    serial_candidates = list(
        learning.get(
            "serial_candidates",
            [],
        )
        or []
    )

    if serial is None:
        learned_serial = (
            best_serial_candidate(
                serial_candidates,
                manufacturer=manufacturer_value,
            )
        )

        if learned_serial:
            serial = learned_serial

    counter_number = (
        normalize_counter(
            counter_raw
        )
    )

    counter = None

    if counter_number is not None:
        counter = IntelligenceValue(
            value=counter_number,
            source=(
                primary.get(
                    "contador_origem"
                )
                or "snmp-primary"
            ),
            confidence=100,
            value_type="pages",
            confirmed=True,
        )

    toner_number = (
        normalize_counter(
            toner_raw
        )
    )

    toner = None

    if (
        toner_number is not None
        and 0 <= toner_number <= 100
    ):
        toner = IntelligenceValue(
            value=toner_number,
            source="snmp-primary",
            confidence=100,
            value_type="percent",
            confirmed=True,
        )

    counter_candidates = list(
        learning.get(
            "counter_candidates",
            [],
        )
        or []
    )

    return PrinterIntelligenceReport(
        ip_address=ip_address,
        manufacturer=manufacturer,
        model=model,
        serial=serial,
        counter=counter,
        toner=toner,
        sys_object_id=learning.get(
            "sys_object_id"
        ),
        serial_candidates=serial_candidates,
        counter_candidates=counter_candidates,
        learning_error=learning.get(
            "error"
        ),
        generated_at=utc_now(),
    )


async def collect_one(
    *,
    ip_address: str,
    community: str = "public",
    timeout: float = 2.0,
    retries: int = 1,
) -> PrinterIntelligenceReport:

    from snmp.engine import (
        collect_printer_intelligence,
    )

    primary = await (
        collect_printer_intelligence(
            ip_address=ip_address,
            community=community,
            timeout=timeout,
            retries=retries,
        )
    )

    learning = (
        primary.get(
            "learning_diagnostic"
        )
        or {}
    )

    return build_report(
        ip_address=ip_address,
        primary=(
            primary.get("dados")
            if isinstance(
                primary.get("dados"),
                dict,
            )
            else primary
        ),
        learning=learning,
    )


async def collect_many(
    *,
    ip_addresses: list[str],
    community: str = "public",
    timeout: float = 2.0,
    retries: int = 1,
) -> list[
    PrinterIntelligenceReport
]:

    reports: list[
        PrinterIntelligenceReport
    ] = []

    for ip_address in ip_addresses:

        try:

            report = await asyncio.wait_for(
                collect_one(
                    ip_address=ip_address,
                    community=community,
                    timeout=timeout,
                    retries=retries,
                ),
                timeout=12.0,
            )

            reports.append(
                report
            )

        except Exception as exc:

            reports.append(
                PrinterIntelligenceReport(
                    ip_address=ip_address,
                    manufacturer=None,
                    model=None,
                    serial=None,
                    counter=None,
                    toner=None,
                    sys_object_id=None,
                    serial_candidates=[],
                    counter_candidates=[],
                    learning_error=(
                        f"{type(exc).__name__}: "
                        f"{exc}"
                    ),
                    generated_at=utc_now(),
                )
            )

    return reports


def save_reports(
    *,
    reports: list[
        PrinterIntelligenceReport
    ],
    destination: str | Path,
) -> Path:

    path = Path(
        destination
    )

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    payload = {
        "schema": (
            "printflow-printer-intelligence-v1"
        ),
        "generated_at": utc_now(),
        "total": len(
            reports
        ),
        "printers": [
            report.to_dict()
            for report in reports
        ],
    }

    path.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return path
