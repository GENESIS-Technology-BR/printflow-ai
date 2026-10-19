"""Static safety regression tests for the SupriTech structural migration runner.

Run: python -m unittest discover -s tests -p 'test_homolog_migration_safety.py'
No database credentials or network are required.
"""
import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "backend/scripts/migrate_supritech_homolog_structure.py"


class MigrationSafetyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = RUNNER.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)

    def test_syntax(self):
        compile(self.source, str(RUNNER), "exec")

    def test_no_data_migration_imports(self):
        imports = [alias.name for node in ast.walk(self.tree)
                   if isinstance(node, ast.ImportFrom)
                   for alias in node.names]
        self.assertNotIn("clean_descriptive_printer_serials", imports)
        self.assertNotIn("configure_guerra_pilot_financials", imports)

    def test_exact_homologation_guard(self):
        self.assertIn('db_name != "talvoa_supritech_homolog_db"', self.source)
        self.assertIn('engine.dialect.name != "postgresql"', self.source)

    def test_target_confirmation_required(self):
        self.assertIn('os.getenv("TALVOA_MIGRATION_TARGET") != "supritech-homolog"', self.source)
        self.assertIn('if args.apply and', self.source)

    def test_explicit_apply_required(self):
        self.assertIn('parser.add_argument("--apply", action="store_true"', self.source)
        self.assertIn('if not args.apply:', self.source)

    def test_no_fastapi_app_import(self):
        self.assertNotIn("from backend.main import", self.source)

    def test_guard_precedes_database_operations(self):
        guard = self.source.index('db_name != "talvoa-supritech-homolog-db"')
        create = self.source.index("Base.metadata.create_all(bind=engine)")
        self.assertLess(guard, create)


if __name__ == "__main__":
    unittest.main()
