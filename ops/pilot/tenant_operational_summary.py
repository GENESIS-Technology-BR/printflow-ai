"""Tenant-scoped read-only operational summary for TALVOA pilot dashboards.

Consumes already authorized records. No database, API or deploy side effects.
"""
from datetime import datetime
from typing import Iterable, Mapping, Optional
from tenant_printer_statuses import tenant_printer_statuses

STATES = ("online", "delayed", "offline", "unknown")


def tenant_operational_summary(
    *,
    authorized_tenant_id: str,
    requested_tenant_id: str,
    printers: Iterable[Mapping],
    now: Optional[datetime] = None,
) -> dict:
    rows = tenant_printer_statuses(
        authorized_tenant_id=authorized_tenant_id,
        requested_tenant_id=requested_tenant_id,
        printers=printers,
        now=now,
    )
    counts = {state: 0 for state in STATES}
    for row in rows:
        counts[row["operational_status"]] += 1
    return {
        "tenant_id": requested_tenant_id,
        "total": len(rows),
        "counts": counts,
        "attention": counts["delayed"],
        "critical": counts["offline"],
        "unverified": counts["unknown"],
        "printers": rows,
        "policy_version": "pilot-v1",
    }
