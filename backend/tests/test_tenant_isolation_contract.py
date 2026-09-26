from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_customer_endpoints_are_tenant_scoped():
    routers = {
        "dashboard": source("backend/modules/dashboard/router.py"),
        "companies": source("backend/modules/companies/router.py"),
        "organization": source("backend/modules/organization/router.py"),
        "usage": source("backend/modules/usage/router.py"),
        "alerts": source("backend/modules/alerts/router.py"),
        "intelligence": source("backend/modules/intelligence/router.py"),
        "printers": source("backend/modules/printers/router.py"),
    }

    for name, router in routers.items():
        assert "current_user.company_id" in router, (
            f"{name} precisa manter escopo por empresa"
        )


def test_agent_ingestion_is_resolved_by_company_token():
    printers = source("backend/modules/printers/router.py")

    assert "Company.agent_token == payload.agent_token" in printers
    assert "Printer.company_id == company.id" in printers


def test_control_center_cross_tenant_access_is_admin_only():
    control_center = source(
        "backend/modules/control_center/router.py"
    )

    assert "get_platform_admin" in control_center
    assert 'prefix="/control-center"' in control_center


def test_guerra_policy_is_consistent_across_public_application_surfaces():
    integration = source("backend/modules/integration/router.py")
    intelligence = source("backend/modules/intelligence/router.py")
    usage = source("backend/modules/usage/router.py")
    dashboard = source("backend/modules/dashboard/router.py")

    assert "_exclude_label_printers_for_company" in integration
    assert "_apply_cost_models" in integration
    assert "_exclude_label_printers_for_company" in intelligence
    assert "_active_history" in intelligence
    assert "_exclude_commercial_printers_for_company" in usage
    assert "_is_guerra_excluded_printer" in dashboard


def test_guerra_policy_covers_alerts_control_center_and_integration_snapshots():
    alerts = source("backend/modules/alerts/service.py")
    control_center = source("backend/modules/control_center/router.py")
    integration = source("backend/modules/integration/router.py")

    assert "_exclude_label_printers_for_company(company, printers)" in alerts
    assert "commercial_printers = _exclude_label_printers_for_company" in control_center
    assert integration.count("_exclude_label_printers_for_company") >= 4
