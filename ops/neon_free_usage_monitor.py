#!/usr/bin/env python3
"""TALVOA Neon Free monitor. Read-only, fail closed on unverified units."""
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

BASE = "https://console.neon.tech/api/v2"
PROJECTS = {
    "printflow-production": "proud-union-87295556",
    "talvoa-supritech-homolog": "red-hat-77865204",
}
THRESHOLDS = (70, 85, 95)
# Confirmed in Neon console: 1 GB and 100 compute hours per project.
STORAGE_LIMIT_BYTES = 1024 ** 3
COMPUTE_LIMIT_SECONDS = 100 * 3600


def fetch(path, token):
    request = urllib.request.Request(
        BASE + path,
        headers={"Authorization": "Bearer " + token, "Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=25) as response:
        return json.load(response)


def check_metric(name, value, limit, unit, alerts, gaps):
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
        gaps.append(name + ": missing or invalid API counter")
        return "- " + name + ": unavailable (no fabricated zero)"
    pct = value / limit * 100
    level = next((threshold for threshold in reversed(THRESHOLDS) if pct >= threshold), None)
    if level is not None:
        alerts.append(f"{name}: {pct:.1f}% (threshold {level}%)")
    return f"- {name}: {value:,.0f} {unit} / {limit:,.0f} {unit} ({pct:.2f}%)"


def main():
    token = os.environ.get("NEON_API_KEY")
    if not token:
        print("::error::Missing NEON_API_KEY GitHub Actions secret")
        return 2

    lines = ["# TALVOA Neon Free monitoring", "",
             "UTC: " + datetime.now(timezone.utc).isoformat(), ""]
    alerts, gaps = [], []
    for name, project_id in PROJECTS.items():
        lines.extend(["## " + name])
        try:
            result = fetch("/projects/" + project_id, token)
            project = result.get("project", {})
            if project.get("id") != project_id:
                raise ValueError("Project ID mismatch")

            # This endpoint exposes project metadata, not guaranteed monthly usage.
            # Do NOT interpret cumulative lifetime counters as monthly quota consumption.
            lines.append("- API access: OK (project metadata verified)")
            lines.append("- Compute monthly consumption: unverified (requires billing usage API)")
            lines.append("- Storage monthly/current usage: unverified (requires verified API source)")
            lines.append("- Network transfer: unverified (requires free-tier quota confirmation)")
            gaps.append(name + ": usage counters not yet validated; no thresholds calculated")
        except (urllib.error.URLError, ValueError, KeyError, TypeError) as exc:
            lines.append("- API access: FAILED (" + type(exc).__name__ + ")")
            gaps.append(name + ": API access failed")
        lines.append("")

    lines += ["## Threshold alerts"]
    lines += ["- " + a for a in alerts] if alerts else ["- None; metrics not yet validated"]
    lines += ["", "## Blocking monitoring gaps"]
    lines += ["- " + gap for gap in gaps]
    report = "\n".join(lines) + "\n"
    print(report)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as handle:
            handle.write(report)
    if gaps:
        print("::error::Neon quota monitoring not ready: consumption API validation required")
        return 1
    if alerts:
        print("::error::Neon free quota threshold exceeded")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
