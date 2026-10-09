"""Finalize all four diagrams from one pinned Archify input in a disposable workspace."""

import json
import os
import shutil
import subprocess
from pathlib import Path

from build_cache import ROOT, LATEST, task_directory, promote, file_digest


def main():
    reference = json.loads((ROOT / 'docs/references/website-sources.lock.json').read_text())['archify']
    source = ROOT / reference['source_directory']
    if not source.is_dir():
        raise FileNotFoundError(f'Restore the pinned Archify input {reference["commit"]}: {source}')
    patch = ROOT / reference['local_patch']['path']
    if file_digest(patch) != reference['local_patch']['sha256']:
        raise ValueError('Update the reference lock after reviewing an Archify patch change')
    with task_directory('diagrams') as run:
        tools = run / 'tools'
        shutil.copytree(source, tools)
        subprocess.run(['git', '-C', str(ROOT), 'apply', '--directory=' + tools.relative_to(ROOT).as_posix(),
            '--ignore-space-change', str(patch)], check=True)
        output = run / 'diagrams'
        environment = {**os.environ, 'TEMP': str(run), 'TMP': str(run), 'ARCHIFY_UPDATE_CHECK_DISABLED': '1'}
        for mode in ('stdio', 'http'):
            for language in ('zh', 'en'):
                name = f'{mode}.{language}'
                directory = output / name
                directory.mkdir(parents=True)
                specification = json.loads((ROOT / 'web/diagrams' / (name + '.json')).read_text(encoding='utf-8'))
                target = directory / (name + '.html')
                specification['meta']['output'] = target.relative_to(ROOT).as_posix()
                candidate = directory / (name + '.json')
                candidate.write_text(json.dumps(specification, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
                with (directory / 'blender.log').open('w', encoding='utf-8') as log:
                    subprocess.run(['node', str(tools / 'archify/bin/archify.mjs'), 'finalize', 'architecture',
                        str(candidate), str(target), '--repo-root', str(ROOT), '--quality', 'showcase',
                        '--out-dir', str(directory / 'review'), '--json'], cwd=ROOT, env=environment,
                        stdout=log, stderr=subprocess.STDOUT, check=True)
        promote(output, LATEST / 'diagrams')


if __name__ == '__main__':
    main()
