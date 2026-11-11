"""Read-only integration boundary for authenticated printer status dashboard.

The API must authenticate the actor, authorize the tenant, and fetch rows with
tenant-scoped queries before invoking this function. Never trust tenant IDs
supplied by the browser as proof of authorization.
"""
from datetime import datetime
from typing import Iterable, Mapping, Optional
from tenant_operational_summary import tenant_operational_summary


def build_dashboard_response(
    *,
    authenticated_tenant_id: str,
    requested_tenant_id: str,
    authorized_printer_rows: Iterable[Mapping],
    now: Optional[datetime] = None,
) -> dict:
    """Convert tenant-filtered database rows into stable dashboard JSON."""
    summary = tenant_operational_summary(
        authorized_tenant_id=authenticated_tenant_id,
        requested_tenant_id=requested_tenant_id,
        printers=authorized_printer_rows,
        now=now,
    )
    return {
        "tenant_id": summary["tenant_id"],
        "cards": {
            "total": summary["total"],
            "online": summary["counts"]["online"],
            "attention": summary["attention"],
            "critical": summary["critical"],
            "unknown": summary["unverified"],
        },
        "printers": summary["printers"],
        "policy_version": summary["policy_version"],
    }
