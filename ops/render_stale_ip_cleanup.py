#!/usr/bin/env python3
"""Fail-closed cleanup for TALVOA ephemeral Render IP rules.
Default: read-only report. --apply removes only exact TALVOA-owned entries.
No DB connection, no backup, no production resources.
"""
import argparse
import json
import os
import urllib.request

DB = "dpg-db7rsb25b2lc739g0img-a"
URL = f"https://api.render.com/v1/postgres/{DB}"
LABEL = "talvoa-ephemeral-gh-backup"

def request(method, payload=None):
    token = os.environ["RENDER_API_KEY"]
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode()
    req = urllib.request.Request(URL, headers=headers, data=data, method=method)
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.load(resp)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    rows = request("GET")["ipAllowList"]
    owned = [r for r in rows if r.get("description") == LABEL]
    print(f"Temporary TALVOA rules found: {len(owned)}")
    if not owned:
        return
    if len(owned) != 1 or not owned[0].get("cidrBlock", "").endswith("/32"):
        raise SystemExit("REFUSED: unexpected owned rules; manual review required")
    if not args.apply:
        print("DRY RUN: no network changes; use --apply with reviewed environment approval.")
        return
    if os.environ.get("TALVOA_CLEANUP_APPROVED") != "yes":
        raise SystemExit("REFUSED: explicit cleanup approval missing")
    remaining = [{"cidrBlock": r["cidrBlock"], "description": r.get("description", "")}
                 for r in rows if r.get("description") != LABEL]
    request("PATCH", {"ipAllowList": remaining})
    after = request("GET")["ipAllowList"]
    if any(r.get("description") == LABEL for r in after):
        raise SystemExit("FAILED: stale access rule still present; inspect Render Networking")
    print("Temporary access removed and verified; other CIDRs preserved.")

if __name__ == "__main__":
    main()
