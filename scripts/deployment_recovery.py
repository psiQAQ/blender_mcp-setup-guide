"""Verify an already published site before redeploying it under a fresh commit."""

import argparse
import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path

from check_reports import preserve_failure, write_json
from pages_site import CHANNELS, channel_directory, unified_index, validate_index
from publication import verify_download


def github_json(path):
    request = urllib.request.Request('https://api.github.com/' + path, headers={
        'Authorization': 'Bearer ' + os.environ['GH_TOKEN'],
        'Accept': 'application/vnd.github+json', 'Cache-Control': 'no-cache',
        'User-Agent': 'BlenderMCPIntegration',
    })
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def verify_recovery(repository, run_id, deployment_commit, site, reports):
    if not re.fullmatch(r'[0-9]+', run_id):
        raise ValueError('Publication run ID must be numeric')
    if not re.fullmatch(r'[0-9a-f]{40}', deployment_commit):
        raise ValueError('Deployment requires a complete Git commit')
    base = f'repos/{repository}'
    run = github_json(f'{base}/actions/runs/{run_id}')
    if (run['event'] != 'workflow_dispatch' or run['path'] != '.github/workflows/release.yml'
            or run['head_repository']['full_name'] != repository or run['status'] != 'completed'
            or run['conclusion'] != 'failure'
            or run['head_branch'] not in {'release/blender-5.1', 'release/blender-5.2'}):
        raise ValueError('Select a failed trusted publication from a maintenance branch')
    if deployment_commit == run['head_sha']:
        raise ValueError('Recovery must deploy under a fresh commit')
    jobs = github_json(f'{base}/actions/runs/{run_id}/jobs?per_page=100')['jobs']
    completed = {job['name']: job['conclusion'] for job in jobs}
    if any(completed.get(name) != 'success' for name in ('publish-assets', 'deploy-index')):
        raise ValueError('Publication assets and initial deployment must already have succeeded')

    channels, records = {}, {}
    for path in CHANNELS:
        directory = site / channel_directory(path)
        if not (directory / 'publication.json').exists():
            continue
        records[path] = validate_index((directory / 'index.json').read_bytes(),
                                       (directory / 'publication.json').read_bytes(), path)
        channels[path] = json.loads((directory / 'index.json').read_bytes())
    if json.loads((site / 'index.json').read_bytes()) != unified_index(channels):
        raise ValueError('Recovery unified index differs from its channel metadata')
    if '' in records and (site / 'publication.json').read_bytes() != (
            site / 'blender-5.1/stable/publication.json').read_bytes():
        raise ValueError('Recovery legacy publication must mirror 5.1 stable')
    path = '' if run['head_branch'].endswith('5.1') else 'blender-5.2/preview'
    record = records[path]
    if record['integration_commit'] != run['head_sha']:
        raise ValueError('Recovery channel differs from the original publication commit')
    found = set()
    for report_path in reports.glob('publication-*/published-tests.json'):
        report = json.loads(report_path.read_bytes())
        platform = report['platform']
        if (platform in found or report['status'] != 'Failed'
                or report.get('error') != 'ValueError: Selected public package differs from the validated candidate'
                or report.get('package_sha256') != record['packages'][platform]['sha256']
                or set(report) != {'status', 'platform', 'package_sha256', 'error'}):
            raise ValueError('Recovery is limited to preinstallation metadata mismatches')
        found.add(platform)
    if found != set(record['packages']):
        raise ValueError('Recovery requires the original failure evidence for all three platforms')

    packages = {}
    for channel, publication in records.items():
        tag = 'v' + publication['extension_version']
        release = github_json(f'{base}/releases/tags/{urllib.parse.quote(tag, safe="")}')
        if (release['draft'] or release['tag_name'] != tag
                or release['target_commitish'] != publication['integration_commit']
                or release['prerelease'] != (publication.get('channel', 'stable') == 'preview')):
            raise ValueError('Recovery requires the matching already published Release')
        assets = {item['name']: item for item in release['assets']}
        for platform, package in publication['packages'].items():
            url = urllib.parse.unquote(package['archive_url'])
            prefix = f'https://github.com/{repository}/releases/download/{tag}/'
            if not url.startswith(prefix) or '/' in url[len(prefix):]:
                raise ValueError('Recovery archive URL must identify a repository Release asset')
            asset = assets[url[len(prefix):]]
            if (asset['size'] != package['size'] or asset['digest'] != 'sha256:' + package['sha256']
                    or urllib.parse.unquote(asset['browser_download_url']) != url):
                raise ValueError('Release asset differs from verified publication metadata')
            verify_download(package['archive_url'], package['sha256'], package['size'])
            packages[f'{channel_directory(channel)}/{platform}'] = package
    return dict(status='Passed', publication_run_id=int(run_id), publication_commit=run['head_sha'],
                deployment_commit=deployment_commit, packages=packages)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--site', type=Path, required=True)
    parser.add_argument('--reports', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=Path('build/latest/deployment-recovery-tests.json'))
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    preserve_failure('deployment-recovery', args.output)
    try:
        report = verify_recovery(os.environ['GITHUB_REPOSITORY'], args.run_id, os.environ['GITHUB_SHA'],
                                 args.site, args.reports)
    except Exception as error:
        write_json(args.output, dict(status='Failed', publication_run_id=args.run_id,
                                    error=f'{type(error).__name__}: {error}'))
        raise
    write_json(args.output, report)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
