"""TALVOA pilot: deterministic Agent heartbeat and printer freshness classification.

Pure functions: no network calls, no database writes, no deployment side effects.
Times must be timezone-aware; stale and future timestamps fail closed.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional


def heartbeat_state(last_seen: Optional[datetime], now: datetime,
                    expected_interval_minutes: int = 5,
                    missed_cycles: int = 3) -> str:
    """Return online, delayed, offline, or unknown.

    online: <= one expected interval; delayed: <= missed_cycles intervals.
    """
    if last_seen is None or last_seen.tzinfo is None or now.tzinfo is None:
        return "unknown"
    if expected_interval_minutes <= 0 or missed_cycles < 2:
        raise ValueError("invalid heartbeat policy")
    age = (now.astimezone(timezone.utc) - last_seen.astimezone(timezone.utc)).total_seconds()
    if age < 0:
        return "unknown"
    interval = timedelta(minutes=expected_interval_minutes).total_seconds()
    if age <= interval:
        return "online"
    if age <= interval * missed_cycles:
        return "delayed"
    return "offline"
