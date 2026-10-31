#!/usr/bin/env python3
"""One-shot Render allowlist lease; always attempts cleanup, without DB access.
Requires RENDER_API_KEY and TALVOA_RUNNER_IPV4 env vars. Never logs secrets.
Preserves existing CIDRs. Use only on dedicated SupriTech homolog PG.
"""
import ipaddress
import json
import os
import sys
import urllib.error
import urllib.request

DB_ID = "dpg-db7rsb25b2lc739g0img-a"
BASE = f"https://api.render.com/v1/postgres/{DB_ID}"
LABEL = "talvoa-ephemeral-gh-backup"

def api(method, body=None):
    headers = {"Authorization": "Bearer " + os.environ["RENDER_API_KEY"],
               "Accept": "application/json"}
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode()
    req = urllib.request.Request(BASE, method=method, headers=headers, data=data)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())

def entries():
    obj = api("GET")
    return obj["ipAllowList"]

def patch(rows):
    return api("PATCH", {"ipAllowList": rows})

def main():
    ip = ipaddress.ip_address(os.environ["TALVOA_RUNNER_IPV4"])
    if ip.version != 4 or not ip.is_global:
        raise ValueError("Expected public IPv4")
    cidr = f"{ip}/32"
    before = entries()
    if any(row["cidrBlock"] == cidr for row in before):
        raise RuntimeError("Runner address already permitted: refuse to take ownership of existing rule")
    if any(row.get("description") == LABEL for row in before):
        raise RuntimeError("Prior ephemeral access rule exists; investigate before continuing")
    added = False
    try:
        patched = [{"cidrBlock": r["cidrBlock"], "description": r.get("description", "")} for r in before]
        patched.append({"cidrBlock": cidr, "description": LABEL})
        patch(patched)
        added = True
        print("Temporary /32 access added; other existing CIDRs preserved.")
        if os.environ.get("TALVOA_LEASE_ONLY") != "yes":
            raise RuntimeError("Lease-only mode required; backup execution not yet configured")
    finally:
        if added:
            current = entries()
            owned = [r for r in current if r.get("description") == LABEL and r.get("cidrBlock") == cidr]
            if len(owned) != 1:
                raise RuntimeError("Cannot safely remove lease; manually inspect Render Networking IMMEDIATELY")
            remaining = [{"cidrBlock": r["cidrBlock"], "description": r.get("description", "")}
                         for r in current if not (r.get("cidrBlock") == cidr and r.get("description") == LABEL)]
            patch(remaining)
            assert not any(r.get("description") == LABEL for r in entries()), "Cleanup not verified"
            print("Lease removed and verified.")
if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("FAILED; inspect database Networking immediately:", type(exc).__name__, file=sys.stderr)
        raise
