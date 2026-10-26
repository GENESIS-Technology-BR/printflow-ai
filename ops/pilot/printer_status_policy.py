"""Pure operational status model for printer monitoring pilot.

A printer cannot be considered online if its collecting Agent is offline,
delayed, or unknown. No database or network side effects.
"""
from datetime import datetime
from typing import Optional
from heartbeat_policy import heartbeat_state


def printer_operational_state(
    agent_last_seen: Optional[datetime],
    printer_last_seen: Optional[datetime],
    now: datetime,
    *,
    interval_minutes: int = 5,
    missed_cycles: int = 3,
) -> str:
    """online, delayed, offline, or unknown.

    Unknown printer telemetry stays unknown even if the Agent is healthy.
    """
    agent = heartbeat_state(agent_last_seen, now, interval_minutes, missed_cycles)
    if agent == "unknown":
        return "unknown"
    if agent == "offline":
        return "offline"
    if printer_last_seen is None:
        return "unknown"
    printer = heartbeat_state(printer_last_seen, now, interval_minutes, missed_cycles)
    if printer == "unknown":
        return "unknown"
    if printer == "offline":
        return "offline"
    if agent == "delayed" or printer == "delayed":
        return "delayed"
    return "online"
