from datetime import date, datetime, timedelta, timezone

from backend.modules.intelligence.service import build_intelligence


def test_intelligence_never_exposes_opaque_hex_as_printer_name():
    opaque = "0x43414e4f4e204950520000000000000000000000000000000000000000000000"
    printer = {
        "id": 77,
        "uuid": "printer-hex",
        "ip": "10.2.0.124",
        "name": opaque,
        "hostname": opaque,
        "model": "Laser MFP 432",
        "custom_name": None,
        "unit_name": "Matriz",
        "sector_name": "TI",
        "status": "online",
        "active": True,
        "health_score": 100,
        "health_reasons": [],
        "last_seen": datetime(2026, 9, 9, 12, tzinfo=timezone.utc).isoformat(),
    }

    today = date(2026, 9, 9)
    history = [
        type("Usage", (), {
            "printer_uuid": "printer-hex",
            "usage_date": today - timedelta(days=offset),
            "pages_printed": 2,
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
    assert opaque not in finding["title"]
    assert finding["printer_name"] == "Laser MFP 432"
    assert "Laser MFP 432" in finding["title"]
