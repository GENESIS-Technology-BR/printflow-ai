"""Offline unit tests: no Render credentials and no HTTP requests."""
import importlib.util
import pathlib
import unittest
from unittest.mock import patch
import sys

path = pathlib.Path(__file__).resolve().parents[1] / 'ops/render_stale_ip_cleanup.py'
spec = importlib.util.spec_from_file_location('cleanup', path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class CleanupTests(unittest.TestCase):
    def test_dry_run_never_patches(self):
        rows = [{'cidrBlock':'8.8.8.8/32','description':mod.LABEL}]
        with patch.object(mod,'request',return_value={'ipAllowList':rows}) as req, patch.object(sys,'argv',['script']):
            mod.main()
        self.assertEqual(req.call_count,1)
        self.assertEqual(req.call_args.args[0],'GET')

    def test_preserve_existing(self):
        current = [{'cidrBlock':'8.8.8.8/32','description':mod.LABEL},{'cidrBlock':'201.72.238.194/32','description':'operator'}]
        def fake(method, payload=None):
            nonlocal current
            if method == 'PATCH':
                current = payload['ipAllowList']
            return {'ipAllowList':list(current)}
        with patch.object(mod,'request',side_effect=fake), patch.dict('os.environ', {'TALVOA_CLEANUP_APPROVED':'yes'}), patch.object(sys,'argv',['script','--apply']):
            mod.main()
        self.assertEqual(current,[{'cidrBlock':'201.72.238.194/32','description':'operator'}])

    def test_reject_multiple_owned(self):
        rows = [{'cidrBlock':f'8.8.8.{i}/32','description':mod.LABEL} for i in (8,9)]
        with patch.object(mod,'request',return_value={'ipAllowList':rows}) as req, patch.object(sys,'argv',['script','--apply']):
            with self.assertRaises(SystemExit): mod.main()
        self.assertEqual(req.call_count,1)

if __name__ == '__main__':
    unittest.main()
