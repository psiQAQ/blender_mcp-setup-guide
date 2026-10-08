"""Compose all published channels and verify retained indexes before and after deployment."""

import argparse
import hashlib
import json
import shutil
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from publication import verify_download
from pages_render import render_site
from upstream_source import channel_path


CHANNELS = ("", "blender-5.2/preview", "blender-5.2/stable")
IMMUTABLE_FILES = ("index.json", "publication.json")


def read_bytes(base, relative, optional=False):
    url = f"{base.rstrip('/')}/{relative}"
    if urllib.parse.urlsplit(url).scheme != "https":
        raise ValueError("Published channels require HTTPS")
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"Cache-Control": "no-cache"}), timeout=30) as response:
            return response.read()
    except urllib.error.HTTPError as error:
        if optional and error.code == 404:
            return None
        raise


def validate_index(index_bytes, publication_bytes, path):
    index, record = json.loads(index_bytes), json.loads(publication_bytes)
    if channel_path(record) != path or len(index["data"]) != 3:
        raise ValueError("Published index has the wrong channel or platform set")
    found = set()
    for item in index["data"]:
        platform, = item["platforms"]
        if platform in found:
            raise ValueError("Published index repeats a platform")
        found.add(platform)
        package = record["packages"][platform]
        if (item["version"], item["archive_hash"], item["archive_size"], item["archive_url"]) != (
            record["extension_version"], f"sha256:{package['sha256']}", package["size"], package["archive_url"]
        ):
            raise ValueError("Published index differs from its immutable publication record")
        if item["blender_version_min"] != record.get("blender_min", "5.1.0") or item["blender_version_max"] != record.get("blender_max", "5.2.0"):
            raise ValueError("Published index has the wrong Blender compatibility")
    if found != {"windows-x64", "linux-x64", "macos-arm64"}:
        raise ValueError("Published index requires all three platforms")
    return record


def retain_channel(base, output, path, preserved, optional=False):
    """Retain install metadata byte-for-byte; HTML and assets are regenerated."""
    prefix = path + "/" if path else ""
    metadata = read_bytes(base, prefix + "publication.json", optional=optional)
    if metadata is None:
        # A channel must be entirely absent, never half-published.
        if read_bytes(base, prefix + "index.json", optional=True) is not None:
            raise ValueError(f"Published channel has an index but no publication record: {path}")
        return None
    index = read_bytes(base, prefix + "index.json")
    record = validate_index(index, metadata, path)
    for package in record["packages"].values():
        verify_download(package["archive_url"], package["sha256"], package["size"])
    for name, content in (("index.json", index), ("publication.json", metadata)):
        destination = output / prefix / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
        preserved[prefix + name] = hashlib.sha256(content).hexdigest()
    return record


def finish_site(base, output, preserved):
    records = {}
    for path in CHANNELS:
        directory = output / path
        if (directory / "publication.json").exists():
            records[path] = validate_index((directory / "index.json").read_bytes(),
                                           (directory / "publication.json").read_bytes(), path)
    render_site(output, records, base)
    (output / "preserved-channels.json").write_text(json.dumps(preserved, indent=2) + "\n", encoding="utf-8")


def refresh(base, output):
    """Refresh only the website, using the existing public installation metadata."""
    if output.exists():
        raise FileExistsError("Use a new composed site directory")
    preserved = {}
    for path in CHANNELS:
        retain_channel(base, output, path, preserved, optional=bool(path))
    finish_site(base, output, preserved)
    return preserved


def compose(base, candidate, output):
    if output.exists():
        raise FileExistsError("Use a new composed site directory")
    publication = (candidate / "publication.json").read_bytes()
    path = channel_path(json.loads(publication))
    validate_index((candidate / "index.json").read_bytes(), publication, path)
    preserved = {}
    for other in CHANNELS:
        if other == path:
            continue
        retain_channel(base, output, other, preserved, optional=bool(other) or not path)
    shutil.copytree(candidate, output / path, dirs_exist_ok=True)
    finish_site(base, output, preserved)
    return preserved


def verify_retained(base, site):
    saved = json.loads((site / "preserved-channels.json").read_text())
    for name, expected in saved.items():
        if name not in {f"{path}/" + filename if path else filename for path in CHANNELS for filename in IMMUTABLE_FILES}:
            raise ValueError(f"Unexpected retained metadata path: {name}")
        if hashlib.sha256(read_bytes(base, name)).hexdigest() != expected:
            raise ValueError(f"Retained channel changed: {name}")
    for path in CHANNELS:
        prefix = path + "/" if path else ""
        if prefix + "publication.json" in saved:
            record = validate_index(read_bytes(base, prefix + "index.json"), read_bytes(base, prefix + "publication.json"), path)
            for package in record["packages"].values():
                verify_download(package["archive_url"], package["sha256"], package["size"])
    print(json.dumps({"status": "Passed", "retained_files": saved}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    operation = parser.add_mutually_exclusive_group()
    operation.add_argument("--candidate", type=Path)
    operation.add_argument("--refresh", action="store_true", help="Refresh presentation from existing verified public channels")
    parser.add_argument("--site", type=Path, required=True)
    args = parser.parse_args()
    if args.refresh:
        refresh(args.base_url, args.site)
    elif args.candidate:
        compose(args.base_url, args.candidate, args.site)
    else:
        verify_retained(args.base_url, args.site)


if __name__ == "__main__":
    main()
