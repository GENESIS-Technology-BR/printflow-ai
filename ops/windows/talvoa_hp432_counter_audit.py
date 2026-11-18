"""Read-only comparison of HP Laser MFP 432 Printer-MIB counters.

Run from agent/python with the agent venv:
  python ../../ops/windows/talvoa_hp432_counter_audit.py

No database writes, no HTTP POST, no tokens, no network scan.
SNMP v2c default community is read from PRINTFLOW_SNMP_COMMUNITY.
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'agent' / 'python'))

from snmp.engine import PrinterIntelligenceEngine
from snmp.oids import PRINTER_OIDS

IP = os.environ.get("TALVOA_HP_AUDIT_IP", "10.2.0.124")
BASE = "1.3.6.1.2.1.43.10.2.1.4"
PRIMARY = PRINTER_OIDS["contador_paginas"]


async def main() -> None:
    engine = PrinterIntelligenceEngine(
        community=os.environ.get("PRINTFLOW_SNMP_COMMUNITY", "public"),
        timeout=2.0,
        retries=1,
    )
    print("HP432 COUNTER AUDIT (READ ONLY) | IP:", IP, flush=True)
    print("REFERENCE IN EWS: Informacao > Contadores de uso > Total de impressoes > Total")
    for attempt in range(1, 4):
        started = datetime.now(timezone.utc).isoformat(timespec="seconds")
        primary = await engine.get_value(IP, PRIMARY)
        candidates = await engine.walk_values(IP, BASE, maximum_rows=32)
        ended = datetime.now(timezone.utc).isoformat(timespec="seconds")
        print(f"\nSAMPLE {attempt} | BEGIN UTC: {started} | END UTC: {ended}")
        print("PRIMARY OID:", PRIMARY, "| VALUE:", primary.value if primary.success else "UNAVAILABLE")
        print("PRINTER-MIB MARKERS:")
        if not candidates:
            print("NO RESPONSE")
        for oid, value in sorted(candidates.items()):
            print(" ", oid, "=", value)
        if attempt < 3:
            await asyncio.sleep(2)
    print("\nNo values have been written. Compare with freshly refreshed HP EWS counter.")


if __name__ == "__main__":
    asyncio.run(main())
