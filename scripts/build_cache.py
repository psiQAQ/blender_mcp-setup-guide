"""Keep one current artifact set and dispose of project-local runtime environments."""

import contextvars
import functools
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / 'build'
LATEST = BUILD / 'latest'
_work = contextvars.ContextVar('build_work', default=None)


def checked_path(path, parent=None):
    parent = BUILD if parent is None else parent
    path, parent = Path(path).absolute(), Path(parent).resolve()
    if not path.resolve().is_relative_to(parent) or path.resolve() == parent:
        raise ValueError(f'Cache target must be inside {parent}: {path}')
    for component in (path, *path.parents):
        if component == parent:
            break
        if component.is_symlink() or (hasattr(component, 'is_junction') and component.is_junction()):
            raise ValueError(f'Cache target contains a link: {component}')
    return path


def remove_cache(path):
    path = checked_path(path)
    try:
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink(missing_ok=True)
    except OSError as error:
        # Retain denied/in-use objects and expose them in the current manifest.
        mark('cleanup', 'Failed', path=str(path), error=str(error))
        return False
    return True


def mark(name, status, **details):
    LATEST.mkdir(parents=True, exist_ok=True)
    path = LATEST / 'status.json'
    records = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    source = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip()
    previous = records.get(name, {})
    artifact = source if status == 'Passed' else previous.get('artifact_commit')
    records[name] = {'status': status, 'source_commit': source, 'artifact_commit': artifact, **details}
    if status != 'Passed' and previous.get('path'):
        backup = LATEST / ('.previous-' + name)
        records[name]['retained_path'] = str(backup) if backup.exists() else previous['path']
        records[name]['retained_package_sha256'] = previous.get('package_sha256')
    temporary = path.with_suffix('.pending')
    temporary.write_text(json.dumps(records, indent=2) + '\n', encoding='utf-8', newline='\n')
    temporary.replace(path)


def current_work(name):
    directory = _work.get()
    if directory is None:
        raise RuntimeError(f'{name} requires a managed task_directory')
    return directory


def retain_diagnostics(name, run):
    destination = LATEST / 'evidence' / name
    if destination.exists() and not remove_cache(destination):
        raise OSError(f'Cannot replace previous diagnostics: {destination}')
    destination.mkdir(parents=True, exist_ok=True)
    for source in sorted(run.rglob('*')):
        if source.is_file() and (source.name in {'blender.log', 'service.log', 'failure.txt', 'desktop.log'} or source.suffix == '.png'):
            relative = source.relative_to(run)
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
    report_path = LATEST / f'{name}-tests.json'
    if report_path.exists():
        report = json.loads(report_path.read_text(encoding='utf-8'))
        def relocate(value):
            if isinstance(value, str) and value.startswith(str(run)):
                return str(destination) + value[len(str(run)):]
            if isinstance(value, list):
                return [relocate(item) for item in value]
            if isinstance(value, dict):
                return {key: relocate(item) for key, item in value.items()}
            return value
        report_path.write_text(json.dumps(relocate(report), indent=2) + '\n', encoding='utf-8', newline='\n')


@contextmanager
def existing_work(path):
    """Bind a child check to the workspace owned by its waiting parent."""
    path = checked_path(path, BUILD / '.working')
    if not path.is_dir():
        raise FileNotFoundError(path)
    token = _work.set(path)
    previous_temp = tempfile.tempdir
    tempfile.tempdir = str(path)
    try:
        yield path
    finally:
        _work.reset(token)
        tempfile.tempdir = previous_temp


@contextmanager
def task_directory(name):
    LATEST.mkdir(parents=True, exist_ok=True)
    parent = BUILD / '.working'
    parent.mkdir(parents=True, exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix=name + '-', dir=parent))
    token = _work.set(run)
    previous_temp = tempfile.tempdir
    tempfile.tempdir = str(run)
    config = run / 'profile/config'
    config.mkdir(parents=True)
    previous_environment = {key: os.environ.get(key) for key in ('TMP', 'TEMP', 'BLENDER_USER_RESOURCES', 'BLENDER_USER_CONFIG')}
    os.environ.update(TMP=str(run), TEMP=str(run), BLENDER_USER_RESOURCES=str(run / 'profile'), BLENDER_USER_CONFIG=str(config))
    try:
        yield run
    finally:
        try:
            retain_diagnostics(name, run)
        finally:
            _work.reset(token)
            tempfile.tempdir = previous_temp
            for key, value in previous_environment.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
            remove_cache(run)


def cached_task(name):
    def decorate(operation):
        @functools.wraps(operation)
        def wrapped(*args, **kwargs):
            with task_directory(name):
                try:
                    result = operation(*args, **kwargs)
                    report = LATEST / f'{name}-tests.json'
                    status = json.loads(report.read_text(encoding='utf-8'))['status'] if report.exists() else 'Passed'
                    mark(name, status)
                    return result
                except Exception as error:
                    mark(name, 'Failed', error=str(error))
                    raise
        return wrapped
    return decorate


def promote(source, destination):
    source = checked_path(source)
    if not source.exists():
        raise FileNotFoundError(source)
    destination = checked_path(destination, LATEST)
    backup = checked_path(LATEST / ('.previous-' + destination.name), LATEST)
    if backup.exists():
        raise OSError(f'Previous artifact requires recovery before replacement: {backup}')
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        shutil.move(str(destination), str(backup))
    try:
        shutil.move(str(source), str(destination))
    except Exception:
        if destination.exists() and not remove_cache(destination):
            raise OSError(f'Previous artifact retained at {backup}; partial target cannot be removed')
        if backup.exists():
            shutil.move(str(backup), str(destination))
        raise
    if backup.exists():
        remove_cache(backup)
    mark(destination.name, 'Passed', path=str(destination))


def pinned_input(kind, key, identity):
    parent = checked_path(LATEST / 'inputs' / kind / key, LATEST)
    parent.mkdir(parents=True, exist_ok=True)
    for previous in parent.iterdir():
        if previous.name != identity and not remove_cache(previous):
            raise OSError(f'Cannot retire previous input: {previous}')
    path = parent / identity
    path.mkdir(exist_ok=True)
    return path


def file_digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()
