from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

from backend.modules.intelligence.service import build_intelligence


def printer(**overrides):
    data = {
        "id": 1,
        "uuid": "printer-001",
        "ip": "10.0.0.10",
        "name": "Printer",
        "hostname": "PRN-01",
        "custom_name": "Financeiro",
        "unit_name": "Matriz",
        "sector_name": "Financeiro",
        "status": "online",
        "active": True,
        "health_score": 100,
        "health_reasons": ["Nenhum risco crítico identificado."],
        "last_seen": datetime(2026, 9, 2, 12, tzinfo=timezone.utc).isoformat(),
    }
    data.update(overrides)
    return data


def usage(day, pages, anomaly_count=0):
    return SimpleNamespace(
        printer_uuid="printer-001",
        usage_date=day,
        pages_printed=pages,
        anomaly_count=anomaly_count,
    )


def test_intelligence_flags_offline_printer_as_critical():
    result = build_intelligence(
        [printer(status="offline", health_score=45)],
        [],
        today=date(2026, 9, 2),
        now=datetime(2026, 9, 2, 13, tzinfo=timezone.utc),
    )

    assert result["counts"]["critical"] == 1
    assert result["findings"][0]["category"] == "availability"
    assert result["findings"][0]["recommendation"]


def test_intelligence_detects_counter_anomaly_and_underuse():
    today = date(2026, 9, 2)
    history = [
        usage(today - timedelta(days=offset), 3, anomaly_count=1 if offset == 2 else 0)
        for offset in range(8)
    ]

    result = build_intelligence(
        [printer()],
        history,
        today=today,
        now=datetime(2026, 9, 2, 13, tzinfo=timezone.utc),
    )

    categories = {item["category"] for item in result["findings"]}
    assert "counter" in categories
    assert "optimization" in categories


def test_intelligence_detects_volume_spike():
    today = date(2026, 9, 2)
    pages = [20, 20, 20, 20, 20, 100, 110, 120]
    history = [
        usage(today - timedelta(days=(len(pages) - 1 - index)), value)
        for index, value in enumerate(pages)
    ]

    result = build_intelligence(
        [printer()],
        history,
        today=today,
        now=datetime(2026, 9, 2, 13, tzinfo=timezone.utc),
    )

    spike = next(item for item in result["findings"] if item["category"] == "usage")
    assert spike["severity"] == "warning"
    assert spike["evidence"]["growth_percent"] >= 50


def test_intelligence_returns_stable_headline_without_findings():
    result = build_intelligence(
        [printer()],
        [],
        today=date(2026, 9, 2),
        now=datetime(2026, 9, 2, 13, tzinfo=timezone.utc),
    )

    assert result["score"] == 100
    assert result["attention_count"] == 0
    assert result["findings"] == []
    assert "Nenhum desvio" in result["headline"]
