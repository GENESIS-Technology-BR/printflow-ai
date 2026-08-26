from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_naive_api_datetimes_are_treated_as_utc():
    utility = (
        ROOT
        / "frontend"
        / "src"
        / "utils"
        / "dateTime.ts"
    ).read_text(encoding="utf-8")

    assert "parseApiDate" in utility
    assert "hasTimezone" in utility
    assert "`${normalized}Z`" in utility


def test_datetime_policy_is_used_in_portal_components():
    files = (
        "PrinterTable.tsx",
        "AgentMonitor.tsx",
        "Dashboard.tsx",
        "AlertCenter.tsx",
    )

    for filename in files:
        content = (
            ROOT
            / "frontend"
            / "src"
            / "components"
            / filename
        ).read_text(encoding="utf-8")

        assert "parseApiDate" in content


def test_agent_elapsed_uses_normalized_timestamp():
    content = (
        ROOT
        / "frontend"
        / "src"
        / "components"
        / "AgentMonitor.tsx"
    ).read_text(encoding="utf-8")

    assert (
        "Date.now() - parseApiDate(value).getTime()"
        in content
    )
