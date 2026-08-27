from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from backend.modules.dashboard.router import serialize_printer
from backend.modules.printers.model import Printer
from backend.modules.printers.schema import (
    PrinterCustomNameUpdate,
    PrinterUpsert,
)


def test_printer_model_has_identity_fields():
    assert "hostname" in Printer.__table__.columns
    assert "custom_name" in Printer.__table__.columns


def test_agent_accepts_hostname():
    payload = PrinterUpsert(
        agent_token="A" * 43,
        ip="10.2.0.101",
        hostname="PRN-FISCAL-01",
    )

    assert payload.hostname == "PRN-FISCAL-01"


def test_custom_name_accepts_null_to_clear():
    payload = PrinterCustomNameUpdate(
        custom_name=None,
    )

    assert payload.custom_name is None


def test_custom_name_rejects_more_than_150_characters():
    with pytest.raises(ValidationError):
        PrinterCustomNameUpdate(
            custom_name="X" * 151,
        )


def test_dashboard_exposes_hostname_and_custom_name():
    printer = SimpleNamespace(
        id=1,
        uuid="printer-1",
        ip="10.2.0.101",
        name="Kyocera ECOSYS M3145idn",
        hostname="PRN-FISCAL-01",
        custom_name="Fiscal - Administracao",
        status="online",
        active=True,
        page_count=81360,
        last_seen=None,
        created_at=None,
    )

    result = serialize_printer(printer)

    assert result["hostname"] == "PRN-FISCAL-01"
    assert result["custom_name"] == "Fiscal - Administracao"
