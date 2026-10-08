import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import build_cache as cache


class BuildCacheTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.build = Path(temporary.name) / 'build'
        self.latest = self.build / 'latest'
        for name, value in [('BUILD', self.build), ('LATEST', self.latest)]:
            patcher = patch.object(cache, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_repeated_runs_keep_only_latest_logs_and_remove_environments(self):
        previous_profile = os.environ.get('BLENDER_USER_RESOURCES')
        for sequence in (1, 2):
            with cache.task_directory('integration') as run:
                self.assertEqual(os.environ['BLENDER_USER_RESOURCES'], str(run / 'profile'))
                self.assertEqual(os.environ['BLENDER_USER_CONFIG'], str(run / 'profile/config'))
                (run / 'client').mkdir()
                (run / 'client/dependency.py').write_text('temporary runtime')
                (run / 'blender.log').write_text(str(sequence))
                self.latest.mkdir(parents=True, exist_ok=True)
                (self.latest / 'integration-tests.json').write_text(json.dumps({'status': 'Passed', 'log': str(run / 'blender.log')}))
            self.assertFalse(run.exists())
            self.assertEqual(os.environ.get('BLENDER_USER_RESOURCES'), previous_profile)
            self.assertEqual((self.latest / 'evidence/integration/blender.log').read_text(), str(sequence))
            self.assertFalse((self.latest / 'evidence/integration/client').exists())
        self.assertEqual(list((self.build / '.working').iterdir()), [])
        report = json.loads((self.latest / 'integration-tests.json').read_text())
        self.assertEqual(report['log'], str(self.latest / 'evidence/integration/blender.log'))

    def test_failure_preserves_artifact_source_and_latest_diagnostic(self):
        with cache.task_directory('site') as run:
            source = run / 'site'
            source.mkdir()
            (source / 'index.json').write_text('current artifact')
            cache.promote(source, self.latest / 'site')
        original = json.loads((self.latest / 'status.json').read_text())['site']['artifact_commit']
        with self.assertRaises(RuntimeError):
            with cache.task_directory('site') as run:
                (run / 'blender.log').write_text('failed attempt')
                cache.mark('site', 'Failed', error='network failure')
                raise RuntimeError('network failure')
        self.assertEqual((self.latest / 'site/index.json').read_text(), 'current artifact')
        report = json.loads((self.latest / 'status.json').read_text())['site']
        self.assertEqual(report['status'], 'Failed')
        self.assertEqual(report['artifact_commit'], original)
        self.assertEqual((self.latest / 'evidence/site/blender.log').read_text(), 'failed attempt')

    def test_input_replacement_retires_previous_lock(self):
        first = cache.pinned_input('wheels', 'windows', 'old-lock')
        (first / 'old.whl').write_text('old')
        current = cache.pinned_input('wheels', 'windows', 'current-lock')
        self.assertFalse(first.exists())
        self.assertEqual(list(current.parent.iterdir()), [current])

    def test_failed_promotion_restores_the_previous_complete_site(self):
        destination = self.latest / 'site'
        destination.mkdir(parents=True)
        (destination / 'index.html').write_text('previous complete site')
        with cache.task_directory('site') as run:
            staged = run / 'candidate'
            staged.mkdir()
            (staged / 'index.html').write_text('new site')
            move = shutil.move
            def fail_new_source(source, target):
                if Path(source) == staged:
                    raise OSError('replacement failed')
                return move(source, target)
            with patch('build_cache.shutil.move', side_effect=fail_new_source):
                with self.assertRaisesRegex(OSError, 'replacement failed'):
                    cache.promote(staged, destination)
            self.assertEqual((destination / 'index.html').read_text(), 'previous complete site')
            self.assertFalse((self.latest / '.previous-site').exists())

    def test_cleanup_refuses_outside_targets_and_retains_denied_objects(self):
        with self.assertRaises(ValueError):
            cache.remove_cache(self.build.parent / 'outside')
        with self.assertRaises(ValueError):
            cache.remove_cache(self.build)
        directory = self.build / 'in-use'
        directory.mkdir(parents=True)
        with patch('build_cache.shutil.rmtree', side_effect=PermissionError('in use')):
            self.assertFalse(cache.remove_cache(directory))
        self.assertTrue(directory.exists())
        self.assertEqual(json.loads((self.latest / 'status.json').read_text())['cleanup']['status'], 'Failed')
