import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from deployment_recovery import verify_recovery


class DeploymentRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(dir=ROOT / 'build/.working')
        self.addCleanup(self.temporary.cleanup)
        self.site = Path(self.temporary.name) / 'site'
        self.reports = Path(self.temporary.name) / 'reports'
        self.site.mkdir()
        self.sha = 'a' * 40
        self.repository = 'owner/repo'
        self.record = dict(channel='preview', blender_min='5.2.0', blender_max='5.3.0',
                           extension_version='1.0.2-dev.2+integration.1', integration_commit=self.sha,
                           packages={})
        self.index = dict(version='v1', blocklist=[], data=[])
        assets = []
        for platform in ('windows-x64', 'linux-x64', 'macos-arm64'):
            name = f'extension-{platform}.zip'
            url = f'https://github.com/{self.repository}/releases/download/v{self.record["extension_version"]}/{name}'
            self.record['packages'][platform] = dict(sha256='b' * 64, size=123, archive_url=url)
            self.index['data'].append(dict(platforms=[platform], version=self.record['extension_version'],
                archive_hash='sha256:' + 'b' * 64, archive_size=123, archive_url=url,
                blender_version_min='5.2.0', blender_version_max='5.3.0'))
            report = self.reports / f'publication-{platform}' / 'published-tests.json'
            report.parent.mkdir(parents=True)
            report.write_text(json.dumps(dict(status='Failed', platform=platform, package_sha256='b' * 64,
                error='ValueError: Selected public package differs from the validated candidate')), encoding='utf-8')
            assets.append(dict(name=name, size=123, digest='sha256:' + 'b' * 64, browser_download_url=url))
        directory = self.site / 'blender-5.2/preview'
        directory.mkdir(parents=True)
        (directory / 'publication.json').write_text(json.dumps(self.record), encoding='utf-8')
        (directory / 'index.json').write_text(json.dumps(self.index), encoding='utf-8')
        (self.site / 'index.json').write_text(json.dumps(self.index), encoding='utf-8')
        self.run = dict(id=12, event='workflow_dispatch', path='.github/workflows/release.yml',
                        head_sha=self.sha, head_branch='release/blender-5.2', status='completed', conclusion='failure',
                        head_repository=dict(full_name=self.repository))
        self.release = dict(tag_name='v' + self.record['extension_version'], target_commitish=self.sha,
                            draft=False, prerelease=True, assets=assets)

    def github(self, path):
        if path.endswith('/actions/runs/12'):
            return self.run
        if '/actions/runs/12/jobs' in path:
            return dict(jobs=[dict(name='publish-assets', conclusion='success'),
                             dict(name='deploy-index', conclusion='success')])
        if '/releases/tags/' in path:
            return self.release
        raise AssertionError(path)

    def verify(self):
        with patch('deployment_recovery.github_json', side_effect=self.github), \
                patch('deployment_recovery.verify_download') as download:
            result = verify_recovery(self.repository, '12', 'c' * 40, self.site, self.reports)
        return result, download

    def test_only_preinstallation_metadata_mismatch_can_redeploy_published_packages(self):
        result, download = self.verify()
        self.assertEqual(result['status'], 'Passed')
        self.assertEqual(download.call_count, 3)
        self.assertEqual(result['publication_commit'], self.sha)

    def test_installation_failure_is_never_treated_as_deployment_staleness(self):
        path = self.reports / 'publication-windows-x64/published-tests.json'
        report = json.loads(path.read_text())
        report['error'] = 'PermissionError: [WinError 5] Access denied'
        path.write_text(json.dumps(report), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'preinstallation'):
            self.verify()

    def test_published_asset_must_match_the_verified_candidate_hash(self):
        self.release['assets'][0]['digest'] = 'sha256:' + 'd' * 64
        with self.assertRaisesRegex(ValueError, 'Release asset'):
            self.verify()

    def test_new_deployment_must_not_reuse_the_publication_commit(self):
        with patch('deployment_recovery.github_json', side_effect=self.github):
            with self.assertRaisesRegex(ValueError, 'fresh commit'):
                verify_recovery(self.repository, '12', self.sha, self.site, self.reports)

    def test_unified_index_cannot_silently_differ_from_channel_metadata(self):
        aggregate = copy.deepcopy(self.index)
        aggregate['data'][0]['archive_hash'] = 'sha256:' + 'e' * 64
        (self.site / 'index.json').write_text(json.dumps(aggregate), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'unified index'):
            self.verify()

    def test_untrusted_workflow_is_rejected_before_reading_artifacts(self):
        self.run['head_repository']['full_name'] = 'someone/fork'
        with self.assertRaisesRegex(ValueError, 'trusted publication'):
            self.verify()
