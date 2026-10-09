"""Build a fixed release line using a disposable clone of the local official source."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

from build_cache import task_directory
from build_integration import ROOT, build


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--blender", type=Path, required=True)
    parser.add_argument("--python", type=Path, default=Path(sys.executable))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--platform", choices=("windows-x64", "linux-x64", "macos-arm64"))
    parser.add_argument("--wheelhouse", type=Path)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    args.lock = args.lock.resolve()
    lock = json.loads(args.lock.read_text(encoding="utf-8"))
    with task_directory("locked-source") as work:
        args.upstream = work / "source"
        subprocess.run(["git", "clone", "--quiet", "--shared", "--no-checkout",
                        str(ROOT / "submodules/blender_mcp"), str(args.upstream)], check=True)
        # Only this disposable clone receives the official origin identity.
        subprocess.run(["git", "-C", str(args.upstream), "remote", "set-url", "origin", lock["repository"]], check=True)
        subprocess.run(["git", "-C", str(args.upstream), "checkout", "--quiet", "--detach", lock["commit"]], check=True)
        build(args)


if __name__ == "__main__":
    main()
