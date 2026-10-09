"""Wait for canonical public metadata to match the deployed artifact before installing."""

import argparse
import hashlib
import json
import time
import urllib.error
from pathlib import Path

from build_cache import LATEST
from check_reports import preserve_failure, write_json
from pages_site import read_bytes


def wait_metadata(base, site, timeout=660, interval=15):
    expected = {path.relative_to(site).as_posix(): path.read_bytes()
                for path in sorted(site.rglob('*.json')) if path.name in {'index.json', 'publication.json'}}
    if not {'index.json', 'publication.json'} <= expected.keys():
        raise ValueError('Deployment artifact must contain root index and publication metadata')
    if timeout < 0 or interval <= 0:
        raise ValueError('Timeout must be nonnegative and interval must be positive')
    started = time.monotonic()
    observations = []
    while True:
        pending, errors = [], {}
        for name, content in expected.items():
            try:
                actual = read_bytes(base, name)
            except urllib.error.HTTPError as error:
                if error.code not in {404, 429, 500, 502, 503, 504}:
                    raise
                actual = None
                errors[name] = str(error)
            except urllib.error.URLError as error:
                actual = None
                errors[name] = str(error)
            if actual != content:
                pending.append(name)
        elapsed = time.monotonic() - started
        observations.append({'elapsed_seconds': round(elapsed, 3), 'pending': pending, 'errors': errors})
        report = {'status': 'Passed' if not pending else 'Not Run', 'base_url': base,
                  'expected_metadata': {name: hashlib.sha256(content).hexdigest() for name, content in expected.items()},
                  'observations': observations}
        if not pending:
            return report
        if elapsed >= timeout:
            report.update(status='Failed', error='Public metadata did not match the deployed artifact before the deadline')
            return report
        time.sleep(min(interval, timeout - elapsed))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', required=True)
    parser.add_argument('--site', type=Path, required=True)
    parser.add_argument('--timeout', type=float, default=660)
    parser.add_argument('--interval', type=float, default=15)
    parser.add_argument('--output', type=Path, default=LATEST / 'deployment-readiness-tests.json')
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    preserve_failure(args.output.name.removesuffix('-tests.json'), args.output)
    try:
        report = wait_metadata(args.base_url, args.site, args.timeout, args.interval)
    except Exception as error:
        write_json(args.output, {'status': 'Failed', 'base_url': args.base_url, 'error': f'{type(error).__name__}: {error}'})
        raise
    write_json(args.output, report)
    print(json.dumps(report, indent=2))
    if report['status'] != 'Passed':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
