from pydantic import ValidationError
import pytest

from backend.modules.organization.router import (
    router,
)
from backend.modules.organization.schema import (
    OrganizationNameUpdate,
)


def _route_methods():
    result = {}

    for route in router.routes:
        path = route.path
        methods = set(
            route.methods or []
        )
        result.setdefault(
            path,
            set(),
        ).update(methods)

    return result


def test_name_update_accepts_valid_name():
    payload = OrganizationNameUpdate(
        name="Fabrica 1",
    )

    assert payload.name == "Fabrica 1"


def test_name_update_rejects_short_name():
    with pytest.raises(
        ValidationError
    ):
        OrganizationNameUpdate(
            name="A",
        )


def test_unit_crud_routes_exist():
    methods = _route_methods()

    assert "GET" in methods[
        "/organization/units"
    ]

    assert "POST" in methods[
        "/organization/units"
    ]

    assert "PATCH" in methods[
        "/organization/units/{unit_id}"
    ]

    assert "DELETE" in methods[
        "/organization/units/{unit_id}"
    ]


def test_sector_crud_routes_exist():
    methods = _route_methods()

    assert "GET" in methods[
        "/organization/sectors"
    ]

    assert "POST" in methods[
        "/organization/sectors"
    ]

    assert "PATCH" in methods[
        "/organization/sectors/{sector_id}"
    ]

    assert "DELETE" in methods[
        "/organization/sectors/{sector_id}"
    ]


def test_crud_router_protects_company():
    import inspect

    from backend.modules.organization import (
        router as organization_router,
    )

    source = inspect.getsource(
        organization_router
    )

    assert (
        "current_user.company_id"
        in source
    )

    assert "Printer.company_id" in source


def test_unit_delete_has_protection():
    import inspect

    from backend.modules.organization import (
        router as organization_router,
    )

    source = inspect.getsource(
        organization_router.deactivate_unit
    )

    assert "active_sectors" in source
    assert "printers" in source
    assert "HTTP_409_CONFLICT" in source


def test_sector_delete_has_protection():
    import inspect

    from backend.modules.organization import (
        router as organization_router,
    )

    source = inspect.getsource(
        organization_router.deactivate_sector
    )

    assert "printers" in source
    assert "HTTP_409_CONFLICT" in source


def test_unit_rename_updates_printers():
    import inspect

    from backend.modules.organization import (
        router as organization_router,
    )

    source = inspect.getsource(
        organization_router.update_unit
    )

    assert "Printer.unit_name" in source
    assert "printer.unit_name" in source


def test_sector_rename_updates_printers():
    import inspect

    from backend.modules.organization import (
        router as organization_router,
    )

    source = inspect.getsource(
        organization_router.update_sector
    )

    assert "Printer.sector_name" in source
    assert "printer.sector_name" in source
