from __future__ import annotations

import time
from dataclasses import dataclass, asdict
from typing import Any, Iterable

from intelligence.snmp_deep_learning import (
    DeepCandidate,
    classify_walk_value,
    enterprise_root_from_sysobjectid,
    normalize_oid,
)


PRINTER_MIB_ROOT = "1.3.6.1.2.1.43"


@dataclass(frozen=True)
class WalkPolicy:
    max_rows: int = 400
    max_seconds: float = 8.0


@dataclass
class WalkRow:
    oid: str
    value: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass
class WalkAnalysis:
    roots: list[str]
    rows_seen: int
    candidates: list[DeepCandidate]
    truncated: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "roots": self.roots,
            "rows_seen": self.rows_seen,
            "candidates": [
                candidate.to_dict()
                for candidate in self.candidates
            ],
            "truncated": self.truncated,
        }


def oid_is_inside(
    oid: str,
    root: str,
) -> bool:

    oid_n = normalize_oid(oid)
    root_n = normalize_oid(root)

    if not oid_n or not root_n:
        return False

    return (
        oid_n == root_n
        or oid_n.startswith(root_n + ".")
    )


def build_learning_roots(
    sys_object_id: Any,
) -> list[str]:

    roots = [
        PRINTER_MIB_ROOT,
    ]

    enterprise = (
        enterprise_root_from_sysobjectid(
            sys_object_id
        )
    )

    if enterprise:
        roots.append(enterprise)

    return list(dict.fromkeys(roots))


def analyse_rows(
    *,
    roots: list[str],
    rows: Iterable[WalkRow],
    policy: WalkPolicy | None = None,
) -> WalkAnalysis:

    active_policy = policy or WalkPolicy()

    started = time.monotonic()

    candidates: list[DeepCandidate] = []

    rows_seen = 0
    truncated = False

    for row in rows:

        if rows_seen >= active_policy.max_rows:
            truncated = True
            break

        if (
            time.monotonic() - started
            > active_policy.max_seconds
        ):
            truncated = True
            break

        if not any(
            oid_is_inside(
                row.oid,
                root,
            )
            for root in roots
        ):
            continue

        rows_seen += 1

        discovered = classify_walk_value(
            row.oid,
            row.value,
        )

        candidates.extend(
            discovered
        )

    candidates.sort(
        key=lambda item: (
            -item.confidence,
            item.candidate_type,
            item.oid,
        )
    )

    return WalkAnalysis(
        roots=roots,
        rows_seen=rows_seen,
        candidates=candidates,
        truncated=truncated,
    )


def best_candidates(
    analysis: WalkAnalysis,
    candidate_type: str,
    limit: int = 10,
) -> list[DeepCandidate]:

    selected = [
        item
        for item in analysis.candidates
        if item.candidate_type
        == candidate_type
    ]

    return selected[:limit]
