"""Prepare a hash-checked Blender installer patch without modifying the host."""

import argparse
import difflib
import hashlib
import json
from pathlib import Path

from build_cache import LATEST, checked_path


BASELINES = {
    "5.1.1": "3738e7660bdaa7493d756be3132274eef6eb748305a16cf957f5e324573e93da",
    "5.2.2": "246cb49882f6129340767023bdc28e98c8ea6e743f64ebbff8aec774f842e5e1",
}

ORIGINAL = '''            # While renaming should never fail, it's always possible file-system operations fail.
            # Unlike other actions, failure here causes the extension to be uninstalled.
            #
            # There is little that can be done about this, being able to create a temporary
            # directory and move it into the destination is required for installation.
            # When that fails - the best that can be done is to communicate the failure, see: #130211.
            try:
                os.rename(filepath_local_pkg_temp, filepath_local_pkg)
'''

REPLACEMENT = '''            # Windows directory rename can fail while a scanner holds a child open.
            # Retry only this staging move, with a bounded wait and no destination overwrite.
            try:
                rename_delays = (0.05, 0.1, 0.2, 0.4, 0.8)
                for rename_attempt in range(len(rename_delays) + 1):
                    try:
                        os.rename(filepath_local_pkg_temp, filepath_local_pkg)
                        break
                    except OSError as ex:
                        if (
                                os.name != "nt" or getattr(ex, "winerror", None) != 5 or
                                rename_attempt == len(rename_delays) or
                                not os.path.isdir(filepath_local_pkg_temp) or
                                os.path.lexists(filepath_local_pkg)
                        ):
                            raise
                        if msglog.status("Retrying directory rename for \\"{:s}\\": WinError 5 ({:d}/{:d})".format(
                                manifest.id, rename_attempt + 1, len(rename_delays),
                        )):
                            return False
                        import time
                        time.sleep(rename_delays[rename_attempt])
                        if REQUEST_EXIT:
                            return False
                        if (
                                not os.path.isdir(filepath_local_pkg_temp) or
                                os.path.lexists(filepath_local_pkg)
                        ):
                            raise
'''


def prepare(installer, version):
    installer = Path(installer).resolve(strict=True)
    original = installer.read_bytes()
    source_hash = hashlib.sha256(original).hexdigest()
    if source_hash != BASELINES[version]:
        raise ValueError(f"Unsupported installer SHA-256 for Blender {version}: {source_hash}")
    newline = b"\r\n" if b"\r\n" in original else b"\n"
    old = ORIGINAL.encode().replace(b"\n", newline)
    new = REPLACEMENT.encode().replace(b"\n", newline)
    if original.count(old) != 1:
        raise ValueError("Expected exactly one staging-directory rename block")
    patched = original.replace(old, new, 1)
    compile(patched, str(installer), "exec")
    output = checked_path(LATEST / "native-install-fix" / f"blender-{version}", LATEST)
    output.mkdir(parents=True, exist_ok=True)
    backup = output / "blender_ext.original.py"
    if backup.exists() and backup.read_bytes() != original:
        raise FileExistsError(f"Different original installer already retained: {backup}")
    backup.write_bytes(original)
    target = output / "blender_ext.py"
    target.write_bytes(patched)
    diff = "".join(difflib.unified_diff(
        original.decode().splitlines(keepends=True), patched.decode().splitlines(keepends=True),
        fromfile=f"blender-{version}/blender_ext.original.py", tofile=f"blender-{version}/blender_ext.py",
    ))
    (output / "rename-retry.patch").write_text(diff, encoding="utf-8", newline="")
    manifest = {
        "status": "Prepared", "blender_version": version, "system_installer": str(installer),
        "original": str(backup), "original_sha256": source_hash,
        "patched": str(target), "patched_sha256": hashlib.sha256(patched).hexdigest(),
        "retry_delays_seconds": [0.05, 0.1, 0.2, 0.4, 0.8],
        "system_deployment": "Not Run",
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--installer", type=Path, required=True)
    parser.add_argument("--version", choices=BASELINES, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.installer, args.version), indent=2))


if __name__ == "__main__":
    main()
