#!/usr/bin/env python3
"""Offline, no-secret audit of Render wake-up references in GitHub workflows."""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
HOST = re.compile(r"https?://[a-z0-9.-]*onrender\.com", re.I)
SCHEDULE = re.compile(r"(?m)^\s*schedule\s*:")
INTERVAL = re.compile(r"(?i)(curl|wget|requests\.|httpx\.|urllib|Invoke-WebRequest|Invoke-RestMethod|fetch\s*\()")
PIN = re.compile(r"(?i)(sleep\s+[0-9]+|while\s+true|for\s*\(\s*;;\s*\))")

def main():
    if not WORKFLOWS.is_dir():
        print("ERROR: workflow directory missing", file=sys.stderr)
        return 2
    critical = 0
    files = sorted(list(WORKFLOWS.glob("*.yml")) + list(WORKFLOWS.glob("*.yaml")))
    print(f"TALVOA Render wake audit — {len(files)} workflows")
    for f in files:
        body = f.read_text(encoding="utf-8", errors="replace")
        hosts = sorted(set(HOST.findall(body)))
        scheduled = bool(SCHEDULE.search(body))
        network = bool(INTERVAL.search(body))
        loop = bool(PIN.search(body))
        if not hosts:
            continue
        risk = scheduled and network
        print(f"{'REVIEW' if risk else 'INFO'} {f.relative_to(ROOT)} schedule={scheduled} network_calls={network} loop={loop} hosts={','.join(hosts)}")
        critical += int(risk)
    print("Review required:", critical)
    print("Static patterns only; external monitors, Actions configured elsewhere and runtime calls not covered.")
    return 1 if critical else 0

if __name__ == "__main__":
    raise SystemExit(main())
