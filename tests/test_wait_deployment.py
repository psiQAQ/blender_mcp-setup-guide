import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from wait_deployment import wait_metadata


class DeploymentReadinessTests(unittest.TestCase):
    def setUp(self):
        working = ROOT / 'build/.working'
        working.mkdir(parents=True, exist_ok=True)
        temporary = tempfile.TemporaryDirectory(dir=working)
        self.addCleanup(temporary.cleanup)
        self.site = Path(temporary.name)
        for name in ('index.json', 'publication.json'):
            (self.site / name).write_bytes(b'new public metadata')
        self.clock = 0

    def sleep(self, seconds):
        self.clock += seconds

    def test_stale_metadata_is_recorded_before_canonical_urls_become_current(self):
        def read(base, name):
            return b'old' if name == 'index.json' and self.clock == 0 else b'new public metadata'
        with patch('wait_deployment.read_bytes', side_effect=read), \
                patch('wait_deployment.time.monotonic', side_effect=lambda: self.clock), \
                patch('wait_deployment.time.sleep', side_effect=self.sleep):
            report = wait_metadata('https://example.com', self.site, timeout=2, interval=1)
        self.assertEqual(report['status'], 'Passed')
        self.assertEqual([item['pending'] for item in report['observations']], [['index.json'], []])

    def test_permanent_mismatch_fails_at_deadline_and_keeps_observations(self):
        with patch('wait_deployment.read_bytes', return_value=b'wrong metadata'), \
                patch('wait_deployment.time.monotonic', side_effect=lambda: self.clock), \
                patch('wait_deployment.time.sleep', side_effect=self.sleep):
            report = wait_metadata('https://example.com', self.site, timeout=2, interval=1)
        self.assertEqual(report['status'], 'Failed')
        self.assertEqual(len(report['observations']), 3)
        self.assertEqual(report['observations'][-1]['elapsed_seconds'], 2)

    def test_forbidden_public_access_is_not_retried_as_propagation(self):
        with patch('wait_deployment.read_bytes', side_effect=urllib.error.HTTPError('https://example.com', 403, 'Forbidden', {}, None)), \
                patch('wait_deployment.time.sleep') as sleep:
            with self.assertRaises(urllib.error.HTTPError):
                wait_metadata('https://example.com', self.site)
        sleep.assert_not_called()
