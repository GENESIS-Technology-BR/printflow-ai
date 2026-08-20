from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from backend.modules.dashboard.router import serialize_printer
from backend.modules.printers.router import (
    _merge_optional,
    _merge_trusted,
    _valid_serial,
    list_printers,
)
from backend.modules.printers.model import Printer
from backend.modules.printers.schema import PrinterUpsert
from backend.modules.printers.schema import AgentHeartbeat


def test_zebra_description_is_not_accepted_as_serial():
    assert _valid_serial("ZTC ZT230-203dpi ZPL") is None
    assert _valid_serial("ZTC ZD230-203dpi ZPL") is None


def test_real_zebra_serial_is_accepted():
    assert _valid_serial("52N212401393") == "52N212401393"
    assert _valid_serial("D5N224001157") == "D5N224001157"


def test_missing_value_does_not_replace_trusted_value():
    assert _merge_optional("KNDK09992", None) == "KNDK09992"
    assert _merge_optional(27377, None) == 27377


def test_lower_confidence_does_not_replace_trusted_value():
    assert _merge_trusted(
        "KNDK09992", 99, "OTHER123", 70
    ) == ("KNDK09992", 99, False)


def test_higher_confidence_replaces_previous_value():
    assert _merge_trusted(
        "CANDIDATE1", 60, "52N212401393", 99
    ) == ("52N212401393", 99, True)


def test_printer_list_applies_company_filter():
    class FakeQuery:
        def __init__(self):
            self.filters = []

        def filter(self, *conditions):
            self.filters.extend(conditions)
            return self

        def order_by(self, *_args):
            return self

        def all(self):
            return []

    query = FakeQuery()
    db = SimpleNamespace(query=lambda _model: query)
    user = SimpleNamespace(company_id=42)

    assert list_printers(db=db, current_user=user) == []
    assert query.filters
    assert "printers.company_id" in str(query.filters[0])


def test_private_ip_is_unique_only_inside_company():
    constraints = {
        constraint.name: tuple(column.name for column in constraint.columns)
        for constraint in Printer.__table__.constraints
        if constraint.name
    }

    assert constraints["uq_printers_company_ip"] == (
        "company_id",
        "ip",
    )


def test_unknown_counter_remains_unknown_in_dashboard():
    printer = SimpleNamespace(
        id=1,
        uuid="printer-1",
        ip="10.2.128.27",
        name="Zebra ZT230",
        manufacturer="Zebra",
        model="ZT230",
        status="online",
        source="agent",
        page_count=None,
        serial="52N212401393",
        toner_percent=None,
        page_count_source=None,
        page_count_confidence=None,
        page_count_confirmed=False,
        serial_source="zebra-enterprise-oid",
        serial_confidence=99,
        serial_confirmed=True,
        active=True,
        last_seen=None,
        created_at=None,
    )

    result = serialize_printer(printer)

    assert result["page_count"] is None
    assert result["serial"] == "52N212401393"
    assert result["serial_confidence"] == 99
    assert result["serial_confirmed"] is True
    assert result["toner_percent"] is None


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("page_count", -1),
        ("toner_percent", 101),
        ("health_score", 101),
    ],
)
def test_invalid_ranges_are_rejected(field, value):
    payload = {
        "agent_token": "0123456789",
        "ip": "10.2.0.122",
        field: value,
    }

    with pytest.raises(ValidationError):
        PrinterUpsert(**payload)


def test_heartbeat_status_is_restricted():
    with pytest.raises(ValidationError):
        AgentHeartbeat(
            agent_token="0123456789",
            agent_name="Agent",
            agent_version="0.1.0",
            status="invented",
        )
