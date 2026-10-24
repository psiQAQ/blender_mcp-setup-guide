"""Reproduce a real Windows child-handle conflict in Blender's ZIP installer.

Uses only the standard library. Run with Blender's bundled Python, passing an
unmodified blender_ext.py and a NEW disposable work directory. No Blender GUI,
third-party add-on, editor, administrator rights, or system-file changes needed.
The work directory is retained for inspection; this script never deletes it.
"""

import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import runpy
import sys
import threading
import time
import zipfile


PACKAGE_ID = "rename_issue_fixture"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--installer", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--blender-version", required=True)
    parser.add_argument("--hold-child", action="store_true")
    args = parser.parse_args()
    if os.name != "nt":
        parser.error("This reproducer requires Windows")
    installer = args.installer.resolve(strict=True)
    work = args.work.resolve()
    work.mkdir(parents=True, exist_ok=False)
    repository = work / "repository"
    repository.mkdir()
    staging = repository / (PACKAGE_ID + "@")
    destination = repository / PACKAGE_ID
    manifest = ('schema_version = "1.0.0"\n'
                f'id = "{PACKAGE_ID}"\n'
                'version = "1.0.0"\nname = "Rename issue fixture"\n'
                'tagline = "Reproduce a native directory rename failure"\n'
                'maintainer = "Bug report fixture"\ntype = "add-on"\n'
                'blender_version_min = "4.2.0"\n'
                'license = ["SPDX:GPL-3.0-or-later"]\n')
    archive = work / "fixture.zip"
    with zipfile.ZipFile(archive, "w") as package:
        package.writestr("blender_manifest.toml", manifest)
        package.writestr("__init__.py", "def register():\n    pass\ndef unregister():\n    pass\n")
        package.writestr("child.txt", "A real reader opens this file briefly.\n")

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateFileW.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32,
                                   ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32,
                                   ctypes.c_void_p]
    kernel.CreateFileW.restype = ctypes.c_void_p
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    kernel.CloseHandle.restype = ctypes.c_int
    module = runpy.run_path(str(installer), run_name="installer_under_test")
    messages, attempts, close_errors = [], [], []
    real_rename = os.rename
    held = None
    release = None
    first_failure_at = None
    released_at = None

    def close_owned_handle():
        nonlocal held, released_at
        if held is not None:
            if not kernel.CloseHandle(held):
                close_errors.append(str(ctypes.WinError(ctypes.get_last_error())))
            else:
                released_at = time.monotonic()
            held = None

    def observed_rename(source, target, *positional, **keywords):
        nonlocal held, release, first_failure_at
        if Path(source) != staging or Path(target) != destination:
            return real_rename(source, target, *positional, **keywords)
        first = not attempts
        row = {"source_exists": staging.is_dir(), "destination_exists": destination.exists()}
        attempts.append(row)
        if first and args.hold_child:
            # READ access, READ | WRITE | DELETE sharing, OPEN_EXISTING.
            held = kernel.CreateFileW(str(staging / "child.txt"), 0x80000000, 7, None, 3, 0, None)
            if held == ctypes.c_void_p(-1).value:
                held = None
                raise ctypes.WinError(ctypes.get_last_error())
        try:
            result = real_rename(source, target, *positional, **keywords)
        except OSError as error:
            row.update(status="Failed", winerror=error.winerror)
            if first and held is not None:
                first_failure_at = time.monotonic()
                release = threading.Timer(0.02, close_owned_handle)
                release.start()
            raise
        else:
            row["status"] = "Passed"
            return result

    def log(kind, message):
        # Avoid including machine-specific directory paths in the shared summary.
        message = message.replace(str(work).replace("\\", "\\\\"), "<work>")
        messages.append({"kind": kind, "message": message.replace(str(work), "<work>")})
        return False

    os.rename = observed_rename
    try:
        installed = module["subcmd_client"]._install_package_from_file_impl(
            module["MessageLogger"](log), local_dir=str(repository),
            filepath_archive=str(archive),
            blender_version_tuple=tuple(map(int, args.blender_version.split("."))),
            python_version_tuple=tuple(sys.version_info[:3]), manifest_compare=None,
            temp_prefix_and_suffix=(".issue-", ".old"),
        )
    finally:
        os.rename = real_rename
        if release is not None:
            release.join()
        close_owned_handle()
    installed_manifest = destination / "blender_manifest.toml"
    report = {
        "installer_sha256": hashlib.sha256(installer.read_bytes()).hexdigest(),
        "blender_version": args.blender_version, "python_version": sys.version.split()[0],
        "hold_child": args.hold_child, "share_mask": 7 if args.hold_child else None,
        "installer_return": installed,
        "manifest_matches": installed_manifest.is_file() and
                            installed_manifest.read_text(encoding="utf-8") == manifest,
        "rename_attempts": attempts, "messages": messages, "close_errors": close_errors,
        "release_after_first_failure_seconds": None if first_failure_at is None or released_at is None
        else round(released_at - first_failure_at, 6),
    }
    (work / "result.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    if close_errors:
        raise RuntimeError("Could not close a handle owned by this reproducer")
    return 0 if installed and report["manifest_matches"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
