"""Pure offline regression suite: local DB must not target historical or cloud DBs."""
import unittest

from backend.app.config.local_guard import (
    validate_local_database_url,
    should_run_startup_migrations,
)


class LocalHomologationGuardTests(unittest.TestCase):
    def test_accepts_only_explicit_disposable_loopback_database(self):
        validate_local_database_url(
            "postgresql://owner:synthetic-password@127.0.0.1:60440/talvoa_local_work_20261116"
        )

    def test_rejects_inherited_production_and_historical_destinations(self):
        cases = [
            "",
            "sqlite:///./talvoa.db",
            "postgresql://owner:fake@127.0.0.1:60439/talvoa_recuperacao_20261116",
            "postgresql://owner:fake@127.0.0.1:5432/talvoa_local_work_20261116",
            "postgresql://owner:fake@db.example.org:60440/talvoa_local_work_20261116",
            "postgresql://owner:fake@0.0.0.0:60440/talvoa_local_work_20261116",
            "postgresql://owner:fake@127.0.0.1:60440/postgres",
            "postgresql://owner:fake@127.0.0.1:60440/talvoa_supritech_homolog_db",
            "postgresql://owner:fake@127.0.0.1:60440/talvoa_local_work_20261116?host=remote",
            "postgresql://owner@127.0.0.1:60440/talvoa_local_work_20261116",
        ]
        for value in cases:
            with self.subTest(value=value), self.assertRaises(RuntimeError):
                validate_local_database_url(value)

    def test_never_mutates_on_http_startup_in_local_mode(self):
        self.assertFalse(
            should_run_startup_migrations("local_homologation", "talvoa_local_work_20261116")
        )
        self.assertFalse(
            should_run_startup_migrations("local_homologation", "talvoa_recuperacao_20261116")
        )
        self.assertFalse(
            should_run_startup_migrations("staging", "talvoa_supritech_homolog_db")
        )
        self.assertTrue(
            should_run_startup_migrations("development", "legacy_development_db")
        )


if __name__ == "__main__":
    unittest.main()
