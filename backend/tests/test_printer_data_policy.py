from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from backend.modules.dashboard.router import serialize_printer
from backend.modules.printers.router import (
    _merge_optional,
    _reconcile_inventory,
    _should_persist_heartbeat,
    _merge_trusted,
    _valid_serial,
    list_printers,
)
from backend.modules.printers.model import Printer
from backend.modules.printers.schema import PrinterUpsert
from backend.modules.printers.schema import AgentHeartbeat
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_zebra_description_is_not_accepted_as_serial():
    assert _valid_serial("ZTC ZT230-203dpi ZPL") is None
    assert _valid_serial("ZTC ZD230-203dpi ZPL") is None


def test_real_zebra_serial_is_accepted():
    assert _valid_serial("52N212401393") == "52N212401393"
    assert _valid_serial("D5N224001157") == "D5N224001157"


def test_power_state_is_not_accepted_as_serial():
    assert _valid_serial("Energy Saver Mode 2") is None
    assert _valid_serial("Sleep Mode") is None


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

        def first(self):
            return None

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
        "agent_token": "A" * 43,
        "ip": "10.2.0.122",
        field: value,
    }

    with pytest.raises(ValidationError):
        PrinterUpsert(**payload)


def test_heartbeat_status_is_restricted():
    with pytest.raises(ValidationError):
        AgentHeartbeat(
            agent_token="A" * 43,
            agent_name="Agent",
            agent_version="0.1.0",
            status="invented",
        )


def test_slow_heartbeat_is_accepted():
    payload = AgentHeartbeat(
        agent_token="A" * 43,
        agent_name="Agent",
        agent_version="0.4.4",
        status="slow",
        inventory_complete=True,
    )
    assert payload.status == "slow"
    assert payload.inventory_complete is True


@pytest.mark.parametrize("length", [10, 42, 44, 100, 199])
def test_agent_token_wrong_length_is_rejected(length):
    with pytest.raises(ValidationError):
        AgentHeartbeat(
            agent_token="A" * length,
            agent_name="Agent",
            agent_version="0.2.4",
            status="starting",
        )


def test_canonical_agent_token_is_accepted():
    payload = AgentHeartbeat(
        agent_token="A" * 43,
        agent_name="Agent",
        agent_version="0.2.4",
        status="starting",
    )
    assert len(payload.agent_token) == 43


def test_completed_inventory_keeps_history_but_deactivates_missing_printers():
    printers = [
        SimpleNamespace(ip="10.2.0.122", active=True),
        SimpleNamespace(ip="10.2.128.27", active=True),
        SimpleNamespace(ip="10.2.99.10", active=True),
    ]

    active, inactive = _reconcile_inventory(
        printers,
        ["10.2.0.122", "10.2.128.27"],
    )

    assert (active, inactive) == (2, 1)
    assert [printer.active for printer in printers] == [True, True, False]


def test_heartbeat_accepts_authoritative_inventory_snapshot():
    payload = AgentHeartbeat(
        agent_token="A" * 43,
        agent_name="Agent",
        agent_version="0.2.7",
        status="healthy",
        inventory_complete=True,
        observed_printer_ips=["10.2.0.122", "10.2.128.27"],
    )

    assert payload.inventory_complete is True
    assert payload.observed_printer_ips == ["10.2.0.122", "10.2.128.27"]


def _heartbeat_company(now):
    return SimpleNamespace(
        agent_last_seen=now - timedelta(seconds=60),
        agent_status="healthy",
        agent_name="Agent",
        agent_version="0.4.4",
        agent_last_error=None,
    )


def _heartbeat_payload(**overrides):
    data = dict(
        agent_token="A" * 43,
        agent_name="Agent",
        agent_version="0.4.4",
        status="healthy",
        inventory_complete=False,
    )
    data.update(overrides)
    return AgentHeartbeat(**data)


def test_free_mode_suppresses_redundant_heartbeat_write():
    now = datetime.now(timezone.utc)
    assert _should_persist_heartbeat(
        _heartbeat_company(now), _heartbeat_payload(), now
    ) is False


def test_heartbeat_status_change_is_persisted_immediately():
    now = datetime.now(timezone.utc)
    assert _should_persist_heartbeat(
        _heartbeat_company(now), _heartbeat_payload(status="slow"), now
    ) is True


def test_complete_inventory_is_persisted_immediately():
    now = datetime.now(timezone.utc)
    assert _should_persist_heartbeat(
        _heartbeat_company(now),
        _heartbeat_payload(inventory_complete=True, observed_printer_ips=["10.2.0.122"]),
        now,
    ) is True


def test_heartbeat_after_write_interval_is_persisted():
    now = datetime.now(timezone.utc)
    company = _heartbeat_company(now)
    company.agent_last_seen = now - timedelta(seconds=301)
    assert _should_persist_heartbeat(company, _heartbeat_payload(), now) is True


def test_heartbeat_handles_naive_postgres_timestamp():
    now = datetime.now(timezone.utc)
    company = _heartbeat_company(now)
    company.agent_last_seen = (
        now - timedelta(seconds=301)
    ).replace(tzinfo=None)

    assert _should_persist_heartbeat(
        company,
        _heartbeat_payload(),
        now,
    ) is True


def test_dashboard_serializes_fixed_monthly_cost_without_page_rate():
    printer = SimpleNamespace(
        id=109, uuid="canon-fixed", ip="10.2.0.109", name="Canon iPF-770",
        hostname=None, custom_name="PLOTTER CANON IPF-770",
        unit_name=None, sector_name=None, unit_id=None, sector_id=None,
        manufacturer="Canon", model="iPF-770", status="online", source="agent",
        page_count=99999, page_count_source="snmp", page_count_confidence=100,
        page_count_confirmed=True, cost_per_page=None, cost_model="fixed_monthly",
        fixed_monthly_cost=1500.0, serial="BACG3815", serial_source="manual",
        serial_confidence=100, serial_confirmed=True, toner_percent=None,
        active=True, last_seen=None, created_at=None,
    )
    result = serialize_printer(printer)
    assert result["cost_model"] == "fixed_monthly"
    assert result["fixed_monthly_cost"] == 1500.0
    assert result["cost_per_page"] is None


def test_guerra_visibility_policy_does_not_depend_on_fixed_company_id():
    router = source("backend/modules/printers/router.py")
    assert "GUERRA_COMPANY_ID" not in router
    assert '"guerra" in (company.name or "").strip().lower()' in router
    assert "Printer.custom_name" in router
    assert "%zt230%" in router
    assert "%zpl%" in router
