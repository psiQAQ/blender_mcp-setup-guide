"""Prepare hash-pinned Mesa software OpenGL for the isolated Windows CI Blender."""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import urllib.request
from pathlib import Path

from build_cache import LATEST, pinned_input

from platforms import ROOT, resolve


def prepare(blender):
    if resolve()[0] != "windows-x64":
        raise ValueError("Windows Mesa setup requires a native Windows x64 runner")
    blender = Path(blender).resolve(strict=True)
    if not blender.is_relative_to((LATEST / "inputs/toolchain").resolve()):
        raise ValueError("Mesa deployment is restricted to the isolated CI Blender toolchain")
    record = json.loads((ROOT / "packaging/gui-windows-x64.json").read_text())
    work = pinned_input("mesa", "windows-x64", record["version"])
    work.mkdir(parents=True, exist_ok=True)
    archive = work / Path(record["url"]).name
    if not archive.exists():
        request = urllib.request.Request(record["url"], headers={"User-Agent": "BlenderMCPIntegrationCI"})
        partial = archive.with_suffix(".partial")
        with urllib.request.urlopen(request, timeout=60) as response, partial.open("wb") as destination:
            shutil.copyfileobj(response, destination)
        partial.rename(archive)
    with archive.open("rb") as stream:
        actual = hashlib.file_digest(stream, "sha256").hexdigest()
    if actual != record["sha256"]:
        raise ValueError("Windows Mesa distribution SHA-256 mismatch")
    extractor = shutil.which("7z") or str(Path(os.environ["ProgramFiles"]) / "7-Zip/7z.exe")
    extracted = work / "extracted"
    subprocess.run([extractor, "x", str(archive), f"-o{extracted}", "-y", *[f"x64/{name}" for name in record["files"]]], check=True)
    for name in record["files"]:
        source, destination = extracted / "x64" / name, blender.parent / name
        if destination.exists() and destination.read_bytes() != source.read_bytes():
            raise ValueError(f"Refusing to replace a different graphics library: {destination}")
        shutil.copyfile(source, destination)
    if environment_file := os.environ.get("GITHUB_ENV"):
        with open(environment_file, "a", encoding="utf-8", newline="\n") as stream:
            stream.write("GALLIUM_DRIVER=llvmpipe\n")
    print(json.dumps({"mesa_version": record["version"], "sha256": actual, "driver": "llvmpipe", "blender": str(blender)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blender", required=True, type=Path)
    prepare(parser.parse_args().blender)
