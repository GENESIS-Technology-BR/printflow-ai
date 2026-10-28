#!/usr/bin/env python3
"""TALVOA demo preflight: local, read-only, no network or credentials.

Run from repository root: python3 ops/demo_preflight.py
Exit code 1 means the presentation is NOT cleared.
This is a source preflight, NOT a substitute for end-to-end homologation.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = {
    "API entrypoint": "backend/main.py",
    "Authentication": "backend/modules/auth/router.py",
    "Partner isolation": "backend/modules/partners/access.py",
    "Printer inventory": "backend/modules/printers/router.py",
    "Dashboard": "backend/modules/dashboard/router.py",
    "Reports/usage": "backend/modules/usage/router.py",
    "Frontend": "frontend/src/App.tsx",
    "Homologation criteria": "docs/qa/talvoa-1.0-homologacao.md",
}
checks = []
for label, relative in REQUIRED.items():
    path = ROOT / relative
    ok = path.is_file() and path.stat().st_size > 0
    checks.append(ok)
    print(f"{'OK' if ok else 'BLOCKED'}: {label} ({relative})")

# Explicit fail-closed gate: source files alone never prove the demo is safe.
qa = ROOT / REQUIRED["Homologation criteria"]
if qa.is_file():
    text = qa.read_text(encoding="utf-8")
    rows = [line.split("|") for line in text.splitlines() if line.startswith("| H")]
    expected = {f"H{i:02d}" for i in range(1, 15)}
    found = {cells[1].strip() for cells in rows if len(cells) >= 5}
    missing = expected - found
    # Unit tests or partial results do not constitute end-to-end acceptance.
    pending = [(cells[1].strip(), cells[4].strip()) for cells in rows
               if len(cells) >= 5 and cells[4].strip().casefold() != "aprovado"]
    print(f"Not approved: {len(pending)}; missing acceptance IDs: {len(missing)}")
    for item, status in pending:
        print(f"  {item}: {status}")
    for item in sorted(missing):
        print(f"  {item}: missing")
    checks.append(not pending and not missing)

print("No deployments, external requests, database changes or secrets used.")
if not all(checks):
    print("NOT CLEARED: resolve missing source files and pending homologation before customer demo.")
    sys.exit(1)
print("Source preflight passed. Live functional testing is STILL REQUIRED.")
