#!/usr/bin/env python3
"""Read-only Neon Free usage monitor. No credentials printed."""
import json, os, sys, urllib.request, urllib.error
from datetime import datetime, timezone

BASE = "https://console.neon.tech/api/v2"
PROJECTS = {"printflow-production": "proud-union-87295556",
            "talvoa-supritech-homolog": "red-hat-77865204"}
LIMITS = {"Compute CU-hours": ("compute_time_seconds", 100 * 3600),
          "Storage GB": ("logical_size", 1_000_000_000),
          "Transfer GB": ("data_transfer_bytes", 5_000_000_000)}
THRESHOLDS = (70, 85, 95)

def get(path, token):
    req = urllib.request.Request(BASE + path, headers={
        "Authorization": "Bearer " + token, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=25) as response:
        return json.load(response)

def main():
    token = os.getenv("NEON_API_KEY")
    if not token:
        print("::error::Missing NEON_API_KEY")
        return 2
    report = ["# TALVOA Neon Free monitoring", "",
              "UTC: " + datetime.now(timezone.utc).isoformat(), ""]
    alerts, errors = [], []
    for name, project_id in PROJECTS.items():
        report.append("## " + name)
        try:
            project = get("/projects/" + project_id, token)["project"]
            if project.get("id") != project_id or project.get("owner", {}).get("subscription_type") != "free_v3":
                raise ValueError("Project identity or plan mismatch")
            start, end = project.get("consumption_period_start"), project.get("consumption_period_end")
            if not start or not end:
                raise ValueError("Missing billing period")
            report.append("- Billing period: " + start + " / " + end)
            branches = get("/projects/" + project_id + "/branches", token)["branches"]
            if not branches:
                raise ValueError("No branches")
            for label, (field, limit) in LIMITS.items():
                if field == "logical_size":
                    # Sum all branches; never assume project synthetic_storage_size is live size.
                    vals = [b.get("logical_size") for b in branches]
                    if any(not isinstance(v, (int, float)) or isinstance(v, bool) or v < 0 for v in vals):
                        errors.append(name + ": logical_size unavailable on one or more branches")
                        report.append("- Storage GB: unavailable")
                        continue
                    value = sum(vals)
                else:
                    value = project.get(field)
                if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
                    errors.append(name + ": " + field + " unavailable")
                    report.append("- " + label + ": unavailable")
                    continue
                percent = 100 * value / limit
                report.append(f"- {label}: {percent:.2f}% ({value:,.0f} / {limit:,.0f} raw units)")
                threshold = next((t for t in reversed(THRESHOLDS) if percent >= t), None)
                if threshold:
                    alerts.append(f"{name}: {label} at {percent:.1f}% (threshold {threshold}%)")
        except (urllib.error.URLError, ValueError, KeyError, TypeError) as exc:
            errors.append(name + ": API check failed (" + type(exc).__name__ + ")")
        report.append("")
    report += ["## Alerts"] + (["- " + a for a in alerts] or ["- None"])
    report += ["", "## Monitoring errors"] + (["- " + e for e in errors] or ["- None"])
    result = "\n".join(report) + "\n"
    print(result)
    if os.getenv("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(result)
    if alerts or errors:
        print("::error::Neon quota alert or monitoring error")
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
