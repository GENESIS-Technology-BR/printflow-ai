"""Regression guard: web startup must never mutate database or create admin accounts."""
import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class TestSafeStartup(unittest.TestCase):
    def test_lifespan_has_no_schema_or_bootstrap_calls(self):
        tree = ast.parse((ROOT / "backend" / "main.py").read_text(encoding="utf-8"))
        lifespan = next(n for n in ast.walk(tree) if isinstance(n, ast.AsyncFunctionDef) and n.name == "lifespan")
        calls = [ast.unparse(n.func) for n in ast.walk(lifespan) if isinstance(n, ast.Call)]
        forbidden = ("create_all", "bootstrap_staging_admin", "ensure_", "configure_guerra_pilot_financials", "clean_descriptive_printer_serials")
        self.assertFalse([c for c in calls if any(x in c for x in forbidden)], calls)

if __name__ == "__main__":
    unittest.main()
