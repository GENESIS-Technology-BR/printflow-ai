from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Awaitable, Callable

from intelligence.snmp_normalizer import normalize_text
from intelligence.vendor_profiles import get_vendor_profile


@dataclass
class LearningCandidate:
    field: str
    oid: str
    value: str | None
    valid: bool


@dataclass
class LearningReport:
    vendor: str | None
    candidates: list[LearningCandidate]

    def to_dict(self) -> dict[str, Any]:
        return {
            "vendor": self.vendor,
            "candidates": [
                asdict(item)
                for item in self.candidates
            ],
        }


def _valid_value(value: Any) -> bool:
    text = normalize_text(value)

    if not text:
        return False

    invalid = {
        "unknown",
        "none",
        "n/a",
        "na",
        "0",
        "-1",
        "nosuchobject",
        "nosuchinstance",
    }

    return text.lower() not in invalid


async def learn_printer_identity(
    vendor: str | None,
    getter: Callable[[str], Awaitable[Any]],
) -> LearningReport:
    profile = get_vendor_profile(vendor)

    candidates: list[LearningCandidate] = []

    for oid in profile.serial_oids:
        value = await getter(oid)

        candidates.append(
            LearningCandidate(
                field="serial",
                oid=oid,
                value=normalize_text(value),
                valid=_valid_value(value),
            )
        )

    for oid in profile.page_count_oids:
        value = await getter(oid)

        candidates.append(
            LearningCandidate(
                field="page_count",
                oid=oid,
                value=normalize_text(value),
                valid=_valid_value(value),
            )
        )

    for oid in profile.description_oids:
        value = await getter(oid)

        candidates.append(
            LearningCandidate(
                field="description",
                oid=oid,
                value=normalize_text(value),
                valid=_valid_value(value),
            )
        )

    return LearningReport(
        vendor=vendor,
        candidates=candidates,
    )
