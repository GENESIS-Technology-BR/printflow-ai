"""Offline tests for the read-only migration inventory tool."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

path = Path(__file__).resolve().parents[1] / "scripts" / "talvoa_supritech_inventory.py"
spec = importlib.util.spec_from_file_location("talvoa_inventory", path)
inventory = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inventory)

class InventoryTests(unittest.TestCase):
    def test_inventory_parses_json(self):
        class Result:
            stdout = '{"database":"neondb","tables":0,"sequences":0,"constraints":0,"relations":[]}'
        with patch.object(inventory.subprocess, "run", return_value=Result()) as execute:
            data = inventory.inventory("postgresql://user:pass@ep-example.neon.tech/neondb?sslmode=require")
            self.assertEqual(data["tables"], 0)
            args, kwargs = execute.call_args
            self.assertEqual(args[0][0], "psql")
            self.assertTrue(kwargs["check"])
            self.assertNotIn("pass", " ".join(args[0]))

    def test_requires_exactly_one_database_selection(self):
        import sys
        with patch.object(sys, "argv", ["inventory"]):
            with self.assertRaises(SystemExit):
                inventory.main()

if __name__ == "__main__":
    unittest.main()
