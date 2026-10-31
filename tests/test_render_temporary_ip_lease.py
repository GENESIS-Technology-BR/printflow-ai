"""Offline tests for Render temporary IP lease: no network, no secrets."""
import importlib.util
import os
import pathlib
import unittest
from unittest.mock import patch

p = pathlib.Path(__file__).resolve().parents[1] / "ops" / "render_temporary_ip_lease.py"
spec = importlib.util.spec_from_file_location("lease", p)
lease = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lease)

class LeaseTests(unittest.TestCase):
    def test_add_and_revoke_preserves_existing_cidrs(self):
        original = [{"cidrBlock": "201.72.238.194/32", "description": "preexisting"}]
        current = list(original)
        def entries(): return list(current)
        def patch_rows(rows): current[:] = rows
        with patch.object(lease, "entries", side_effect=entries), patch.object(lease, "patch", side_effect=patch_rows), patch.dict(os.environ, {"TALVOA_RUNNER_IPV4":"8.8.8.8", "TALVOA_LEASE_ONLY":"yes"}):
            lease.main()
        self.assertEqual(current, original)

    def test_patch_response_lost_still_reverts(self):
        original = [{"cidrBlock": "201.72.238.194/32", "description": "preexisting"}]
        current = list(original)
        calls = 0
        def patch_rows(rows):
            nonlocal calls
            calls += 1
            current[:] = rows
            if calls == 1: raise ConnectionError("response lost")
        with patch.object(lease, "entries", side_effect=lambda: list(current)), patch.object(lease, "patch", side_effect=patch_rows), patch.dict(os.environ, {"TALVOA_RUNNER_IPV4":"8.8.8.8", "TALVOA_LEASE_ONLY":"yes"}):
            with self.assertRaises(ConnectionError):
                lease.main()
        self.assertEqual(current, original)

    def test_existing_access_is_not_owned(self):
        original = [{"cidrBlock": "8.8.8.8/32", "description": "external operator"}]
        with patch.object(lease, "entries", return_value=original), patch.object(lease, "patch") as change, patch.dict(os.environ, {"TALVOA_RUNNER_IPV4":"8.8.8.8", "TALVOA_LEASE_ONLY":"yes"}):
            with self.assertRaises(RuntimeError): lease.main()
            change.assert_not_called()

    def test_no_broad_cidr(self):
        with patch.dict(os.environ, {"TALVOA_RUNNER_IPV4":"0.0.0.0", "TALVOA_LEASE_ONLY":"yes"}):
            with self.assertRaises(ValueError): lease.main()

if __name__ == "__main__":
    unittest.main()
