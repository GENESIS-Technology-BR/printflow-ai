"""Static regression checks for portable homologation startup settings.

These checks intentionally avoid importing the application or touching a database.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PortableHomologationChecks(unittest.TestCase):
    def test_gateway_uses_configurable_https_origin(self):
        source = (ROOT / "homolog-gateway.mjs").read_text(encoding="utf-8")
        self.assertIn("process.env.TALVOA_API_UPSTREAM", source)
        self.assertIn('upstreamUrl.protocol !== "https:"', source)
        self.assertIn("upstreamUrl.username", source)
        self.assertIn("upstreamUrl.password", source)
        self.assertIn("upstreamUrl.pathname", source)

    def test_gateway_does_not_log_credentials(self):
        source = (ROOT / "homolog-gateway.mjs").read_text(encoding="utf-8")
        self.assertIn('headers.set("cookie", req.headers.cookie)', source)
        self.assertNotRegex(source, r"console\\.(?:log|info|warn|error)\\([^\\n]*(?:req\\.headers\\.cookie|headers\\.get\\(\\s*['\\\"]authorization)")

    def test_staging_can_skip_legacy_startup_migrations(self):
        source = (ROOT / "backend/main.py").read_text(encoding="utf-8")
        self.assertIn('os.getenv("TALVOA_SKIP_STARTUP_MIGRATIONS", "").lower() == "true"', source)
        self.assertRegex(source, r"if not skip_startup_migrations and .*:")
        self.assertIn("Base.metadata.create_all(bind=engine)", source)

    def test_staging_bootstrap_remains_opt_in(self):
        source = (ROOT / "backend/main.py").read_text(encoding="utf-8")
        self.assertIn('os.getenv("TALVOA_ALLOW_STAGING_BOOTSTRAP") == "true"', source)


if __name__ == "__main__":
    unittest.main()
