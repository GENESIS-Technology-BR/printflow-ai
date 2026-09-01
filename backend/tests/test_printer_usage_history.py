from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from backend.app.config.settings import settings
from backend.modules.usage.service import (
    calculate_counter_delta,
    reporting_date,
)


ROOT = Path(__file__).resolve().parents[2]


def source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_counter_delta_accumulates_only_positive_usage():
    result = calculate_counter_delta(1000, 1125)
    assert result.pages == 125
    assert result.anomaly_type is None


def test_counter_decrease_never_generates_negative_usage():
    result = calculate_counter_delta(52000, 350)
    assert result.pages == 0
    assert result.anomaly_type == "counter_decrease"


def test_negative_counter_is_rejected():
    with pytest.raises(ValueError):
        calculate_counter_delta(-1, 10)


def test_reporting_date_uses_configured_offset():
    moment = datetime(2026, 9, 1, 1, 30, tzinfo=timezone.utc)
    expected = (
        moment + timedelta(hours=settings.report_utc_offset_hours)
    ).date()
    assert reporting_date(moment) == expected


def test_agent_ingest_records_history_after_trusted_page_update():
    router = source("backend/modules/printers/router.py")
    assert "record_daily_printer_usage" in router
    assert "if page_updated and printer.page_count is not None:" in router
    assert "db.flush()" in router


def test_daily_usage_model_is_registered_before_create_all():
    models = source("backend/app/database/models.py")
    assert "PrinterUsageDaily" in models


def test_daily_usage_endpoint_is_company_scoped():
    router = source("backend/modules/usage/router.py")
    assert "current_user.company_id" in router
    assert "PrinterUsageDaily.company_id" in router
    assert '"/daily"' in router