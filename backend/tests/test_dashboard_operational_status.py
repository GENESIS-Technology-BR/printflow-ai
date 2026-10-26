"""Unit coverage for new read-only operational endpoint (no real database)."""
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from backend.modules.dashboard.router import dashboard_operational_status


class OperationalStatusEndpointTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime.now(timezone.utc)
        self.db = MagicMock()

    def test_fresh_printer_and_agent_are_online(self):
        self.db.query.return_value.filter.return_value.first.return_value = SimpleNamespace(
            agent_last_seen=self.now - timedelta(seconds=30)
        )
        rows = [{
            "id": 1, "uuid": "uuid-1", "name": "Printer", "ip": "10.2.0.1",
            "last_seen": (self.now - timedelta(seconds=30)).isoformat(),
            "status": "online", "active": True,
        }]
        with patch("backend.modules.dashboard.router._company_inventory", return_value=(rows, rows)) as inventory:
            result = dashboard_operational_status(
                db=self.db, current_user=SimpleNamespace(company_id=7)
            )
        inventory.assert_called_once_with(self.db, 7)
        self.assertEqual(result["cards"]["online"], 1)
        self.assertEqual(result["tenant_id"], 7)

    def test_offline_agent_overrides_printer(self):
        self.db.query.return_value.filter.return_value.first.return_value = SimpleNamespace(
            agent_last_seen=self.now - timedelta(minutes=20)
        )
        rows = [{
            "id": 1, "uuid": "uuid-1", "name": "Printer", "ip": "10.2.0.1",
            "last_seen": self.now.isoformat(), "status": "online", "active": True,
        }]
        with patch("backend.modules.dashboard.router._company_inventory", return_value=(rows, rows)):
            result = dashboard_operational_status(
                db=self.db, current_user=SimpleNamespace(company_id=7)
            )
        self.assertEqual(result["cards"]["critical"], 1)

    def test_missing_company_rejected(self):
        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as error:
            dashboard_operational_status(
                db=self.db, current_user=SimpleNamespace(company_id=None)
            )
        self.assertEqual(error.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()
