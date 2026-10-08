"""Download the hash-pinned official Blender build into the project build directory."""

import hashlib
import json
import os
import argparse
import shutil
import subprocess
import tarfile
import urllib.request
import zipfile
from pathlib import Path

from platforms import resolve


ROOT = Path(__file__).resolve().parents[1]


def prepare(identifier, minimum=False):
    _, target = resolve(identifier)
    record = target["minimum_blender" if minimum else "blender"]
    tools = ROOT / "build/toolchain" / identifier / record["version"]
    tools.mkdir(parents=True, exist_ok=True)
    archive = tools / Path(record["url"]).name
    if not archive.exists():
        request = urllib.request.Request(record["url"], headers={"User-Agent": "Mozilla/5.0 BlenderMCPIntegrationCI"})
        partial = archive.with_suffix(archive.suffix + ".partial")
        with urllib.request.urlopen(request, timeout=60) as response, partial.open("wb") as destination:
            while block := response.read(1024 * 1024):
                destination.write(block)
        partial.rename(archive)
    with archive.open("rb") as stream:
        actual = hashlib.file_digest(stream, "sha256").hexdigest()
    if actual != record["sha256"]:
        raise ValueError(f"Blender distribution SHA-256 mismatch: {archive}")
    if identifier == "macos-arm64":
        extracted = tools / "application"
        if not (extracted / record["binary"]).exists():
            mount = tools / "mount"
            mount.mkdir(exist_ok=True)
            subprocess.run(["hdiutil", "attach", "-nobrowse", "-readonly", "-mountpoint", str(mount), str(archive)], check=True)
            try:
                shutil.copytree(mount / "Blender.app", extracted / "Blender.app", symlinks=True)
            finally:
                subprocess.run(["hdiutil", "detach", str(mount)], check=True)
    else:
        extracted = tools / archive.name.removesuffix(".zip").removesuffix(".tar.xz")
        if not (extracted / record["binary"]).exists():
            if archive.suffix == ".zip":
                with zipfile.ZipFile(archive) as package:
                    package.extractall(tools)
            else:
                with tarfile.open(archive) as package:
                    package.extractall(tools, filter="data")
    blender = extracted / record["binary"]
    python = extracted / record["python_binary"]
    if not blender.is_file() or not python.is_file():
        raise FileNotFoundError("The locked Blender distribution has an unexpected layout")
    if environment_file := os.environ.get("GITHUB_ENV"):
        prefix = "MINIMUM_" if minimum else ""
        with open(environment_file, "a", encoding="utf-8", newline="\n") as stream:
            stream.write(f"{prefix}BLENDER={blender}\n{prefix}BLENDER_PYTHON={python}\n")
    print(json.dumps({"blender": str(blender), "python": str(python), "sha256": actual}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform", choices=("windows-x64", "linux-x64", "macos-arm64"))
    parser.add_argument("--minimum", action="store_true")
    args = parser.parse_args()
    identifier, _ = resolve(args.platform)
    prepare(identifier, args.minimum)


if __name__ == "__main__":
    main()
