"""Adapter for operational dashboard/API payloads (isolated pilot component).

Use this function only after the caller has authenticated and scoped the
printer/Agent records to the correct tenant. This module does not query DB.
"""
from datetime import datetime, timezone
from typing import Optional
from printer_status_policy import printer_operational_state


def printer_status_payload(
    *,
    printer_id: str,
    agent_last_seen: Optional[datetime],
    printer_last_seen: Optional[datetime],
    now: Optional[datetime] = None,
) -> dict:
    """Return a stable, serializable read-only status projection."""
    if not printer_id or not printer_id.strip():
        raise ValueError("printer_id is required")
    current = now if now is not None else datetime.now(timezone.utc)
    state = printer_operational_state(agent_last_seen, printer_last_seen, current)
    return {
        "printer_id": printer_id,
        "operational_status": state,
        "agent_last_seen": agent_last_seen.isoformat() if agent_last_seen else None,
        "printer_last_seen": printer_last_seen.isoformat() if printer_last_seen else None,
        "evaluated_at": current.isoformat(),
        "policy_version": "pilot-v1",
    }
