from datetime import date, datetime, timedelta, timezone

from backend.modules.intelligence.service import build_intelligence


def test_intelligence_prefers_business_context_over_technical_hostname():
    today = date(2026, 9, 9)
    printer = {
        "id": 1,
        "uuid": "printer-001",
        "ip": "10.2.0.124",
        "name": "HP Laser",
        "hostname": "320F-7D89EF",
        "custom_name": None,
        "model": "Laser MFP 432",
        "unit_name": "Matriz",
        "sector_name": "Financeiro",
        "status": "online",
        "active": True,
        "health_score": 100,
        "health_reasons": [],
        "last_seen": datetime(2026, 9, 9, 12, tzinfo=timezone.utc).isoformat(),
    }

    history = [
        type("Usage", (), {
            "printer_uuid": "printer-001",
            "usage_date": today - timedelta(days=offset),
            "pages_printed": 3,
            "anomaly_count": 0,
        })()
        for offset in range(8)
    ]

    result = build_intelligence(
        [printer],
        history,
        today=today,
        now=datetime(2026, 9, 9, 13, tzinfo=timezone.utc),
    )

    finding = next(item for item in result["findings"] if item["category"] == "optimization")
    assert finding["printer_name"] == "Financeiro · Laser MFP 432"
    assert "320F-7D89EF" not in finding["title"]
    assert "Financeiro · Laser MFP 432" in finding["title"]
