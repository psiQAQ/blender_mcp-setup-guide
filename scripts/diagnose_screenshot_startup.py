"""Probe real Blender window pixels during startup and window context changes."""

import argparse
import json
import os
import subprocess
import traceback
from pathlib import Path

from build_cache import LATEST, current_work
from check_reports import run_check, write_json
from platforms import process_options
from publication import digest
from test_gui import wait_result


ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--blender', type=Path, required=True)
    parser.add_argument('--label', required=True)
    parser.add_argument('--gpu-backend', choices=('opengl', 'vulkan'), default='opengl')
    parser.add_argument('--early-minimized', action='store_true')
    args = parser.parse_args()
    run = current_work('screenshot-startup')
    path = LATEST / f'screenshot-startup-{args.label}-tests.json'
    host = ROOT / 'tests/blender_screenshot_probe.py'
    report = {'status': 'Not Run', 'gpu_backend_requested': args.gpu_backend,
              'blender': str(args.blender), 'probe_sha256': digest(host),
              'driver_sha256': digest(Path(__file__)), 'human_gui_acceptance': 'Not Run',
              'early_minimized_requested': args.early_minimized}
    write_json(path, report)
    with (run / 'blender.log').open('w', encoding='utf-8') as log:
        process = subprocess.Popen([
            str(args.blender), '--gpu-backend', args.gpu_backend, '--factory-startup',
            '--python-exit-code', '1', '--python', str(host), '--', str(run),
            *(['--early-minimized'] if args.early_minimized else []),
        ], env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'}, stdin=subprocess.DEVNULL,
            stdout=log, stderr=subprocess.STDOUT, **process_options(gui=True))
        try:
            wait_result(run / 'host-result.json', run, process)
            process.wait(timeout=90)
            report['probe'] = json.loads((run / 'host-result.json').read_text(encoding='utf-8'))
            report['status'] = report['probe']['status']
            if process.returncode:
                raise RuntimeError(f'Blender exited with code {process.returncode}')
        except Exception as error:
            report.update(status='Failed', error=f'{type(error).__name__}: {error}',
                          traceback=traceback.format_exc())
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=10)
            report['host_exit_code'] = process.returncode
            write_json(path, report)
    print(json.dumps({'status': report['status'], 'report': str(path)}), flush=True)
    if report['status'] != 'Passed':
        raise SystemExit(1)


if __name__ == '__main__':
    import sys
    label = sys.argv[sys.argv.index('--label') + 1]
    run_check(f'screenshot-startup-{label}', main)
