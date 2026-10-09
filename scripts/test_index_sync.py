"""Sync an aggregate index with the actual Blender Extensions client in isolation."""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def host(url, destination):
    import bpy
    bpy.context.preferences.system.use_online_access = True
    repo = bpy.context.preferences.extensions.repos.new(name='Unified index validation', module='unified_test', remote_url=url)
    repo.use_sync_on_startup = False
    position = list(bpy.context.preferences.extensions.repos).index(repo)
    assert bpy.ops.extensions.repo_sync(repo_index=position) == {'FINISHED'}
    cached = Path(repo.directory) / '.blender_ext/index.json'
    index = json.loads(cached.read_bytes())
    sys.path.insert(0, str(Path(bpy.utils.system_resource('SCRIPTS')) / 'addons_core/bl_pkg/cli'))
    import blender_ext
    manifests = [blender_ext.pkg_manifest_from_dict_and_validate(item, from_repo=True, strict=False) for item in index['data']]
    assert all(not isinstance(item, str) for item in manifests), manifests
    assert blender_ext.pkg_manifest_detect_duplicates([(manifest, '', []) for manifest in manifests]) is None
    errors = []
    selected = [item for item in index['data'] if not blender_ext.repository_filter_skip(item,
        filter_blender_version=bpy.app.version, filter_platform='windows-x64',
        filter_python_version=sys.version_info[:3], skip_message_fn=None, error_fn=errors.append)]
    assert not errors, errors
    assert len(selected) == 1, selected
    expected_min = f'{bpy.app.version[0]}.{bpy.app.version[1]}.0'
    assert selected[0]['blender_version_min'] == expected_min
    destination.write_text(json.dumps({'status': 'Passed', 'blender': bpy.app.version_string,
        'index_url': url, 'entries': len(index['data']), 'selected': selected[0],
        'official_manifest_validation': 'Passed', 'official_duplicate_detection': 'Passed',
        'actual_repository_sync': 'Passed'}, indent=2) + '\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--blender', type=Path, required=True)
    parser.add_argument('--index-url', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    from build_cache import task_directory
    with task_directory(args.output.stem) as run:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        env = {**os.environ, 'BLENDER_USER_RESOURCES': str(run / 'profile'), 'PYTHONDONTWRITEBYTECODE': '1'}
        with (run / 'blender.log').open('w', encoding='utf-8') as log:
            subprocess.run([str(args.blender), '--background', '--factory-startup', '--python-exit-code', '1',
                '--python', str(Path(__file__).resolve()), '--', args.index_url, str(args.output.resolve())],
                env=env, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=120)
    print(args.output.read_text(encoding='utf-8'))


if __name__ == '__main__':
    if '--' in sys.argv:
        url, destination = sys.argv[sys.argv.index('--') + 1:]
        host(url, Path(destination))
    else:
        main()
