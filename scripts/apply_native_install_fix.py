"""Apply or restore a locally validated Blender installer patch by exact hash."""

import argparse
import hashlib
import json
from pathlib import Path

from build_cache import LATEST
from prepare_native_install_fix import BASELINES


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", choices=BASELINES, required=True)
    parser.add_argument("--action", choices=("check", "apply", "restore"), default="check")
    args = parser.parse_args()
    bundle = LATEST / "native-install-fix" / f"blender-{args.version}"
    manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    original = (bundle / "blender_ext.original.py").read_bytes()
    patched = (bundle / "blender_ext.py").read_bytes()
    if sha256(original) != BASELINES[args.version] or sha256(original) != manifest["original_sha256"]:
        raise ValueError("Original installer backup does not match the supported baseline")
    if sha256(patched) != manifest["patched_sha256"]:
        raise ValueError("Patched installer changed after preparation")
    target = Path(manifest["system_installer"]).resolve(strict=True)
    current = target.read_bytes()
    current_hash = sha256(current)
    if current_hash not in (sha256(original), sha256(patched)):
        raise ValueError(f"System installer changed; refusing to replace it: {target}")
    result = {
        "action": args.action, "blender_version": args.version, "target": str(target),
        "current_sha256": current_hash, "original_sha256": sha256(original), "patched_sha256": sha256(patched),
    }
    if args.action == "apply":
        report = json.loads((LATEST / f"native-install-fix-{args.version}-tests.json").read_text(encoding="utf-8"))
        if report.get("status") != "Passed" or report.get("installer_sha256") != sha256(patched):
            raise ValueError("A Passed validation report for these exact patched bytes is required")
    if args.action != "check":
        replacement = patched if args.action == "apply" else original
        if current != replacement:
            # Write the existing file to preserve its Windows ACL and ownership.
            # The byte-verified original is retained in the workspace for restoration.
            with target.open("r+b") as stream:
                if stream.read() != current:
                    raise ValueError("Installer changed between validation and opening for write")
                try:
                    stream.seek(0)
                    stream.write(replacement)
                    stream.truncate()
                    stream.flush()
                    stream.seek(0)
                    if stream.read() != replacement:
                        raise OSError("Written installer does not match the validated patch")
                except OSError:
                    stream.seek(0)
                    stream.write(current)
                    stream.truncate()
                    stream.flush()
                    raise
        result["result_sha256"] = sha256(target.read_bytes())
        if result["result_sha256"] != sha256(replacement):
            raise OSError("Installer changed before final deployment verification")
        result["status"] = "Passed"
        (bundle / "deployment.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    else:
        result["status"] = "Passed"
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
