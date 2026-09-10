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
