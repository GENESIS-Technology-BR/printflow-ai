"""Read-only, tenant-scoped status projection for API integration.

The authenticated caller must supply an explicit authorized tenant ID.
No implicit cross-tenant lookup, no database writes, and no network access.
"""
from datetime import datetime
from typing import Iterable, Mapping, Optional
from printer_status_payload import printer_status_payload


def tenant_printer_statuses(
    *,
    authorized_tenant_id: str,
    requested_tenant_id: str,
    printers: Iterable[Mapping],
    now: Optional[datetime] = None,
) -> list[dict]:
    """Fail closed when tenant scope is missing or mismatched."""
    if not authorized_tenant_id or not requested_tenant_id:
        raise PermissionError("explicit tenant scope required")
    if authorized_tenant_id != requested_tenant_id:
        raise PermissionError("cross-tenant status access denied")
    result = []
    for record in printers:
        if record.get("tenant_id") != requested_tenant_id:
            # Never leak a record from another tenant, even if upstream query is wrong.
            continue
        result.append(printer_status_payload(
            printer_id=str(record["printer_id"]),
            agent_last_seen=record.get("agent_last_seen"),
            printer_last_seen=record.get("printer_last_seen"),
            now=now,
        ))
    return result
