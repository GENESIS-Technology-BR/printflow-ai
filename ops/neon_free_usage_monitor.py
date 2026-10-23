#!/usr/bin/env python3
"""TALVOA read-only Neon Free quota monitor."""
import json, os, sys, urllib.request, urllib.error
from datetime import datetime, timezone

BASE = "https://console.neon.tech/api/v2"
PROJECTS = {"printflow-production": "proud-union-87295556",
            "talvoa-supritech-homolog": "red-hat-77865204"}
LIMITS = {"Compute CU-h": (100 * 3600, "compute_time_seconds"),
          "Storage GB": (1_000_000_000, "synthetic_storage_size"),
          "Network GB": (5_000_000_000, "data_transfer_bytes")}
THRESHOLDS = (70, 85, 95)

def get(project_id, key):
    req = urllib.request.Request(BASE + "/projects/" + project_id,
        headers={"Authorization": "Bearer " + key, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=25) as response:
        return json.load(response)["project"]

def main():
    key = os.getenv("NEON_API_KEY")
    if not key:
        print("::error::NEON_API_KEY secret not configured")
        return 2
    lines = ["# TALVOA Neon Free quota monitor", "",
             "UTC: " + datetime.now(timezone.utc).isoformat(), ""]
    alerts, errors = [], []
    for name, project_id in PROJECTS.items():
        lines.append("## " + name)
        try:
            p = get(project_id, key)
            if p.get("id") != project_id or p.get("owner", {}).get("subscription_type") != "free_v3":
                raise ValueError("Project identity or free plan not verified")
            if not p.get("consumption_period_start") or not p.get("consumption_period_end"):
                raise ValueError("Billing period not available")
            lines.append("- Billing period: " + p["consumption_period_start"] + " to " + p["consumption_period_end"])
            for label, (limit, field) in LIMITS.items():
                value = p.get(field)
                if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
                    errors.append(name + ": " + field + " unavailable")
                    lines.append("- " + label + ": unavailable")
                    continue
                # synthetic_storage_size is a storage estimate; do not equate to branch
                # logical size limit without cross-checking the console.
                if field == "synthetic_storage_size":
                    lines.append(f"- Storage estimate: {value/1e9:.4f} GB (informational; not quota-verified)")
                    errors.append(name + ": storage quota metric needs branch logical-size verification")
                    continue
                pct = value / limit * 100
                lines.append(f"- {label}: {pct:.2f}% ({value:,.0f} / {limit:,.0f} raw units)")
                threshold = next((x for x in reversed(THRESHOLDS) if pct >= x), None)
                if threshold:
                    alerts.append(f"{name}: {label} {pct:.1f}% (level {threshold}%)")
        except (urllib.error.URLError, ValueError, KeyError, TypeError) as e:
            errors.append(name + ": API verification failed (" + type(e).__name__ + ")")
        lines.append("")
    lines += ["## Alerts"] + (["- " + x for x in alerts] or ["- None"])
    lines += ["", "## Validation gaps"] + (["- " + x for x in errors] or ["- None"])
    report = "\n".join(lines) + "\n"
    print(report)
    if os.getenv("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(report)
    if alerts or errors:
        print("::error::Neon quota alert or monitoring validation gap")
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
