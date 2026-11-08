"""Failure cleanup checks; no Docker process, network or real DB is used."""
import importlib.util
from pathlib import Path
import subprocess
import sys
import unittest
from unittest import mock

OPS = Path(__file__).resolve().parents[1] / 'ops'
sys.path.insert(0, str(OPS))
spec = importlib.util.spec_from_file_location('m99_cloud', OPS / 'talvoa_m99_cloud_synthetic.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class CloudCleanupTests(unittest.TestCase):
    def test_start_failure_removes_created_container(self):
        with mock.patch.object(module, 'docker') as docker:
            docker.side_effect = [b'synthetic-container-id\n',
                                  subprocess.CalledProcessError(1, ['synthetic-start']), b'']
            with self.assertRaises(subprocess.CalledProcessError):
                module.rehearse()
        self.assertEqual(docker.call_args, mock.call('rm', '-f', '-v', 'synthetic-container-id'))
        create = docker.call_args_list[0].args
        self.assertIn('--network=none', create)
        self.assertIn('--pull=never', create)
        self.assertIn('--read-only', create)

    def test_unready_cluster_removed_without_attempting_dump(self):
        calls = []
        def fake_docker(*args, **kwargs):
            calls.append(args)
            if args[0] == 'create':
                return b'synthetic-container-id'
            if args[0] == 'exec':
                raise subprocess.CalledProcessError(1, ['synthetic-psql'])
            return b''
        with mock.patch.object(module, 'docker', side_effect=fake_docker), mock.patch.object(module.time, 'sleep'):
            with self.assertRaisesRegex(RuntimeError, 'did not become ready'):
                module.rehearse()
        self.assertEqual(calls[-1], ('rm', '-f', '-v', 'synthetic-container-id'))
        self.assertFalse(any('pg_dump' in call for call in calls))


if __name__ == '__main__':
    unittest.main()
