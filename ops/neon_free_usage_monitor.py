#!/usr/bin/env python3
"""Read-only Neon Free quota monitor. Never logs credentials."""
import json, os, sys, urllib.request, urllib.error
from datetime import datetime, timezone

BASE = "https://console.neon.tech/api/v2"
PROJECTS = {"printflow-production": "proud-union-87295556",
            "talvoa-supritech-homolog": "red-hat-77865204"}
THRESHOLDS = (70, 85, 95)
# Free plan limits confirmed in Neon Billing on 2026-10-23; revalidate on plan change.
STORAGE_LIMIT = 1024 ** 3
COMPUTE_LIMIT_SECONDS = 100 * 3600

def get(path, token):
    req = urllib.request.Request(BASE + path, headers={"Authorization": "Bearer " + token,
                               "Accept": "application/json", "User-Agent": "talvoa-quota-monitor/1"})
    with urllib.request.urlopen(req, timeout=25) as resp:
        return json.load(resp)

def main():
    token = os.environ.get("NEON_API_KEY")
    if not token:
        print("ERROR: missing NEON_API_KEY GitHub Actions secret", file=sys.stderr)
        return 2
    report = ["# TALVOA Neon Free quota check", "", "UTC: " + datetime.now(timezone.utc).isoformat(), ""]
    alerts = []
    errors = []
    for name, project_id in PROJECTS.items():
        try:
            payload = get("/projects/" + project_id, token)
            project = payload.get("project", payload)
            if project.get("id") != project_id:
                raise ValueError("project identity mismatch")
            # API counters and per-branch storage vary by API version.
            # Never substitute missing metrics with zero.
            report += ["## " + name, "Plan: " + str(project.get("owner", {}).get("subscription_type", "unverified"))]
            metrics = [
                ("Compute time", project.get("compute_time_seconds"), COMPUTE_LIMIT_SECONDS, "seconds"),
                ("Storage", project.get("synthetic_storage_size"), STORAGE_LIMIT, "bytes"),
            ]
            for label, raw, limit, unit in metrics:
                if raw is None or not isinstance(raw, (int, float)):
                    report.append("- " + label + ": unavailable; needs API verification")
                    errors.append(name + " " + label + " metric unavailable")
                    continue
                pct = raw / limit * 100
                level = next((t for t in reversed(THRESHOLDS) if pct >= t), None)
                report.append(f"- {label}: {raw:,.0f} {unit} / {limit:,.0f} {unit} ({pct:.2f}%)")
                if level:
                    alerts.append(f"{name}: {label} {pct:.1f}% (threshold {level}%)")
            report.append("- Network transfer: quota not yet verified; no percentage calculated")
            report.append("")
        except (urllib.error.URLError, ValueError, KeyError, TypeError) as exc:
            errors.append(f"{name}: API check failed ({type(exc).__name__})")
    report += ["## Alerts", *(["- " + x for x in alerts] if alerts else ["- None detected on available metrics"])]
    report += ["", "## Monitoring gaps", *(["- " + x for x in errors] if errors else ["- Network quota requires validation"])]
    output = "\n".join(report) + "\n"
    print(output)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(output)
    if alerts:
        print("::error::Neon quota threshold reached")
    if errors:
        print("::error::Neon quota monitoring incomplete")
    return 1 if alerts or errors else 0

if __name__ == "__main__":
    sys.exit(main())
