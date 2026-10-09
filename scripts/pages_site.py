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
from build_cache import LATEST, task_directory, promote, mark


CHANNELS = ("", "blender-5.2/preview", "blender-5.2/stable")
IMMUTABLE_FILES = ("index.json", "publication.json")


def channel_directory(path):
    """Keep the legacy 5.1 channel key while giving it a canonical URL."""
    return path or "blender-5.1/stable"


def version_tuple(value):
    return tuple(int(part) for part in value.split("."))


def unified_index(channels):
    """Select stable before preview within each Blender line, then reject overlap."""
    selected = {}
    for path, index in channels.items():
        if index.get("version", "v1") != "v1":
            raise ValueError("Unsupported Blender index format")
        line, channel = channel_directory(path).split("/")
        if line not in selected or channel == "stable":
            selected[line] = (channel, index)
    data, blocklist = [], []
    for line in sorted(selected):
        index = selected[line][1]
        data.extend(index["data"])
        for blocked in index.get("blocklist", []):
            if blocked not in blocklist:
                blocklist.append(blocked)
    for position, left in enumerate(data):
        for right in data[position + 1:]:
            if left.get("id") != right.get("id") or not set(left["platforms"]) & set(right["platforms"]):
                continue
            if max(version_tuple(left["blender_version_min"]), version_tuple(right["blender_version_min"])) < min(version_tuple(left["blender_version_max"]), version_tuple(right["blender_version_max"])):
                raise ValueError("Unified index has overlapping Blender compatibility")
    return {"version": "v1", "blocklist": blocklist, "data": data}


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
    prefix = channel_directory(path) + "/"
    source_prefix = prefix
    metadata = read_bytes(base, prefix + "publication.json", optional=True)
    if metadata is None and not path:
        if read_bytes(base, prefix + "index.json", optional=True) is not None:
            raise ValueError("Published channel has an index but no publication record")
        source_prefix = ""
        metadata = read_bytes(base, "publication.json", optional=optional)
    if metadata is None:
        # A channel must be entirely absent, never half-published.
        if read_bytes(base, prefix + "index.json", optional=True) is not None:
            raise ValueError(f"Published channel has an index but no publication record: {path}")
        return None
    index = read_bytes(base, source_prefix + "index.json")
    record = validate_index(index, metadata, path)
    for package in record["packages"].values():
        verify_download(package["archive_url"], package["sha256"], package["size"])
    for name, content in (("index.json", index), ("publication.json", metadata)):
        destination = output / prefix / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
        preserved[prefix + name] = {"sha256": hashlib.sha256(content).hexdigest(), "source": source_prefix + name}
    return record


def finish_site(base, output, preserved):
    records, channels = {}, {}
    for path in CHANNELS:
        directory = output / channel_directory(path)
        if (directory / "publication.json").exists():
            records[path] = validate_index((directory / "index.json").read_bytes(),
                                           (directory / "publication.json").read_bytes(), path)
            channels[path] = json.loads((directory / "index.json").read_bytes())
    aggregate = unified_index(channels)
    (output / "index.json").write_text(json.dumps(aggregate, indent=2) + "\n", encoding="utf-8", newline="\n")
    if "" in records:
        shutil.copyfile(output / channel_directory("") / "publication.json", output / "publication.json")
    render_site(output, records, base)
    (output / "preserved-channels.json").write_text(json.dumps(preserved, indent=2) + "\n", encoding="utf-8")


def refresh(base, output):
    """Refresh only the website, using the existing public installation metadata."""
    if output.exists():
        raise FileExistsError("Use a new composed site directory")
    preserved = {}
    for path in CHANNELS:
        retain_channel(base, output, path, preserved, optional=True)
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
    shutil.copytree(candidate, output / channel_directory(path), dirs_exist_ok=True)
    finish_site(base, output, preserved)
    return preserved


def verify_retained(base, site, deployed=False):
    saved = json.loads((site / "preserved-channels.json").read_text())
    for name, entry in saved.items():
        if name not in {f"{channel_directory(path)}/" + filename for path in CHANNELS for filename in IMMUTABLE_FILES}:
            raise ValueError(f"Unexpected retained metadata path: {name}")
        source = name if deployed else entry["source"]
        if hashlib.sha256(read_bytes(base, source)).hexdigest() != entry["sha256"]:
            raise ValueError(f"Retained channel changed: {name}")
    channels = {}
    for path in CHANNELS:
        prefix = channel_directory(path) + "/"
        if (site / prefix / "publication.json").exists() or prefix + "publication.json" in saved:
            def content(name):
                if deployed:
                    return read_bytes(base, prefix + name)
                return (site / prefix / name).read_bytes()
            index, publication = content("index.json"), content("publication.json")
            record = validate_index(index, publication, path)
            channels[path] = json.loads(index)
            if deployed or prefix + "publication.json" in saved:
                for package in record["packages"].values():
                    verify_download(package["archive_url"], package["sha256"], package["size"])
    if deployed:
        if json.loads(read_bytes(base, "index.json")) != unified_index(channels):
            raise ValueError("Public unified index differs from channel records")
        if "" in channels and read_bytes(base, "publication.json") != read_bytes(base, "blender-5.1/stable/publication.json"):
            raise ValueError("Legacy publication record differs from 5.1 stable")
    print(json.dumps({"status": "Passed", "retained_files": saved}, indent=2))


def build_site(base, output, candidate=None):
    """Replace a managed site only after a complete successful composition."""
    output = output.resolve()
    if not output.is_relative_to(LATEST.resolve()):
        return compose(base, candidate, output) if candidate else refresh(base, output)
    with task_directory('site') as temporary:
        try:
            staged = temporary / 'site'
            result = compose(base, candidate, staged) if candidate else refresh(base, staged)
            promote(staged, output)
            return result
        except Exception as error:
            mark(output.name, 'Failed', error=str(error))
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    operation = parser.add_mutually_exclusive_group()
    operation.add_argument("--candidate", type=Path)
    operation.add_argument("--refresh", action="store_true", help="Refresh presentation from existing verified public channels")
    parser.add_argument("--site", type=Path, default=LATEST / 'site')
    parser.add_argument("--deployed", action="store_true", help="Verify destination channels and the public unified index")
    args = parser.parse_args()
    if args.refresh:
        build_site(args.base_url, args.site)
    elif args.candidate:
        build_site(args.base_url, args.site, args.candidate)
    else:
        verify_retained(args.base_url, args.site, args.deployed)


if __name__ == "__main__":
    main()
