"""Generate an Extensions index only after validating and reading back its ZIP."""

import argparse
import hashlib
import html
import json
import re
import shutil
import subprocess
import tempfile
import tomllib
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path
from upstream_source import release_channel, channel_path


ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def version_key(record):
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", record["version"]):
        raise ValueError("Only stable upstream versions may be published")
    revision = record["integration_revision"]
    if type(revision) is not int or revision < 0:
        raise ValueError("integration_revision must be a non-negative integer")
    channel = release_channel(record)
    preview = record.get("preview_revision", 0)
    if type(preview) is not int or (channel == "preview" and preview < 1) or (channel == "stable" and preview != 0):
        raise ValueError("Preview sequence must match the release channel")
    return (*map(int, record["version"].split(".")), int(channel == "stable"), preview, revision)


def extension_version(record):
    version_key(record)
    preview = f"-dev.{record['preview_revision']}" if release_channel(record) == "preview" else ""
    return f"{record['version']}{preview}+integration.{record['integration_revision']}"


def publication_identity(source):
    return {"channel": release_channel(source), "preview_revision": source.get("preview_revision", 0),
            "source_ref": source.get("source_ref", source.get("tag")),
            "blender_min": source["blender_min"], "blender_max": source["blender_max"]}


def check_forward(current, candidate):
    if current is None:
        return
    if channel_path(current) != channel_path(candidate):
        raise ValueError("Refusing to replace another release channel or Blender line")
    before, after = version_key(current), version_key(candidate)
    if after < before:
        raise ValueError("Refusing to replace the index with an older integration")
    def hashes(record):
        if "packages" in record:
            return {key: item["sha256"] for key, item in record["packages"].items()}
        return {record.get("platform", "single"): record["sha256"]}
    if after == before and hashes(current) != hashes(candidate):
        raise ValueError("A published version is immutable; increase integration_revision")
    if release_channel(candidate) == "preview" and current["version"] == candidate["version"] and current.get("preview_revision") == candidate["preview_revision"] and hashes(current) != hashes(candidate):
        raise ValueError("Changed preview content requires the next dev.N sequence")


def read_current(url):
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise


def verify_download(url, expected_hash, expected_size, allow_local_http=False, headers=None):
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" and not (
        allow_local_http and parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "localhost"}
    ):
        raise ValueError("Archive readback requires HTTPS (loopback HTTP is test-only)")
    checksum, size = hashlib.sha256(), 0
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({})) if allow_local_http else urllib.request.build_opener()
    request = urllib.request.Request(url)
    for name, value in (headers or {}).items():
        request.add_unredirected_header(name, value)
    with opener.open(request, timeout=30) as response:
        while block := response.read(1024 * 1024):
            checksum.update(block)
            size += len(block)
    if checksum.hexdigest() != expected_hash or size != expected_size:
        raise ValueError("Published archive size or SHA-256 differs from the validated ZIP")


def prepare_repository(blender, package, output, archive_url=None, current=None, allow_local_http=False):
    package, output = Path(package).resolve(), Path(output).resolve()
    if output.exists():
        raise FileExistsError(f"Use a new index output directory: {output}")
    with zipfile.ZipFile(package) as archive:
        manifest = tomllib.loads(archive.read("blender_manifest.toml").decode())
        source = json.loads(archive.read("provenance.json"))
    version = extension_version(source)
    if manifest["id"] != "blender_mcp_integration" or manifest["version"] != version:
        raise ValueError("Manifest and provenance version do not agree")
    if manifest["platforms"] != [source["platform"]] or (
        manifest["blender_version_min"], manifest["blender_version_max"]
    ) != (source["blender_min"], source["blender_max"]):
        raise ValueError("Manifest compatibility differs from provenance")
    candidate = {
        **publication_identity(source),
        "version": source["version"], "integration_revision": source["integration_revision"],
        "extension_version": version, "commit": source["commit"], "platform": source["platform"],
        "sha256": digest(package), "size": package.stat().st_size,
        "archive_url": archive_url or f"./{package.name}",
    }
    check_forward(current, candidate)
    subprocess.run([str(blender), "--command", "extension", "validate", str(package)], check=True)
    if archive_url:
        verify_download(archive_url, candidate["sha256"], candidate["size"], allow_local_http)
    work = ROOT / "build/work"
    work.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="index-", dir=work) as temporary:
        stage = Path(temporary) / "repository"
        stage.mkdir()
        shutil.copyfile(package, stage / package.name)
        subprocess.run([str(blender), "--command", "extension", "server-generate", "--repo-dir", str(stage)], check=True)
        index_path = stage / "index.json"
        index = json.loads(index_path.read_text(encoding="utf-8"))
        if len(index["data"]) != 1:
            raise ValueError("The current index must contain exactly one compatible package")
        item = index["data"][0]
        if item["archive_hash"] != f"sha256:{candidate['sha256']}" or item["archive_size"] != candidate["size"]:
            raise ValueError("Official index does not describe the validated archive")
        item["archive_url"] = candidate["archive_url"]
        index_path.write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")
        (stage / "publication.json").write_text(json.dumps(candidate, indent=2) + "\n", encoding="utf-8")
        (stage / "index.html").write_text(
            '<!doctype html><html lang="en"><meta charset="utf-8"><title>Blender MCP Integrated</title>'
            f'<h1>Blender MCP Integrated</h1><p>{source["blender_min"]} ≤ Blender &lt; {source["blender_max"]}</p>'
            f'<p><a href="{html.escape(candidate["archive_url"], quote=True)}">Download {html.escape(version)}</a></p>'
            '<p>Add this site\'s index.json URL to Blender Extensions repositories.</p></html>\n', encoding="utf-8",
        )
        if archive_url:
            (stage / package.name).unlink()
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(stage, output)
    return candidate


def prepare_collection(blender, packages, output, archive_urls=None, current=None):
    """Validate the complete platform set and generate one official Extensions index."""
    from platforms import records
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError(f"Use a new index output directory: {output}")
    if set(packages) != set(records()):
        raise ValueError("The publication requires all three platforms")
    sources, manifests, entries = {}, {}, {}
    for identifier, package in packages.items():
        package = Path(package)
        with zipfile.ZipFile(package) as archive:
            source = json.loads(archive.read("provenance.json"))
            manifest = tomllib.loads(archive.read("blender_manifest.toml").decode())
        if source["platform"] != identifier or manifest["platforms"] != [identifier]:
            raise ValueError("Package platform does not match the publication slot")
        if manifest["id"] != "blender_mcp_integration" or manifest["version"] != extension_version(source):
            raise ValueError("Manifest and provenance version do not agree")
        if (manifest["blender_version_min"], manifest["blender_version_max"]) != (source["blender_min"], source["blender_max"]):
            raise ValueError("Manifest compatibility differs from provenance")
        subprocess.run([str(blender), "--command", "extension", "validate", str(package)], check=True)
        entries[identifier] = {"sha256": digest(package), "size": package.stat().st_size, "archive_url": f"./{package.name}"}
        if archive_urls:
            verify_download(archive_urls[identifier], entries[identifier]["sha256"], entries[identifier]["size"])
            entries[identifier]["archive_url"] = archive_urls[identifier]
        sources[identifier], manifests[identifier] = source, manifest
    source = next(iter(sources.values()))
    for other in sources.values():
        if publication_identity(other) != publication_identity(source) or any(other.get(key) != source.get(key) for key in ("version", "integration_revision", "commit", "integration_commit", "integration_dirty", "python", "blender_min", "blender_max")):
            raise ValueError("Platform packages do not share the same source and compatibility")
    candidate = {"schema_version": 2, **publication_identity(source), **{key: source[key] for key in ("version", "integration_revision", "commit", "integration_commit")},
                 "extension_version": extension_version(source), "packages": entries}
    check_forward(current, candidate)
    output.mkdir(parents=True)
    for package in packages.values():
        shutil.copyfile(package, output / Path(package).name)
    subprocess.run([str(blender), "--command", "extension", "server-generate", "--repo-dir", str(output)], check=True)
    index_path = output / "index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    if len(index["data"]) != len(packages):
        raise ValueError("Official index does not contain exactly three platform packages")
    found = set()
    for item in index["data"]:
        identifier, = item["platforms"]
        if identifier in found or identifier not in entries:
            raise ValueError("Duplicate or unexpected platform in the index")
        found.add(identifier)
        entry = entries[identifier]
        if item["archive_hash"] != f"sha256:{entry['sha256']}" or item["archive_size"] != entry["size"]:
            raise ValueError("Official index does not describe the validated archive")
        item["archive_url"] = entry["archive_url"]
    index_path.write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")
    (output / "publication.json").write_text(json.dumps(candidate, indent=2) + "\n", encoding="utf-8")
    links = "".join(f'<li><a href="{html.escape(entry["archive_url"], quote=True)}">{identifier}</a></li>' for identifier, entry in entries.items())
    (output / "index.html").write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>Blender MCP Integrated</title>'
        f'<h1>Blender MCP Integrated {candidate["extension_version"]}</h1><p>{source["blender_min"]} ≤ Blender &lt; {source["blender_max"]} / CPython {source["python"]}</p><ul>{links}</ul>'
        '<p>Add this site\'s index.json URL to Blender Extensions repositories.</p></html>\n', encoding="utf-8")
    if archive_urls:
        for package in packages.values():
            (output / Path(package).name).unlink()
    return candidate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blender", required=True, type=Path)
    parser.add_argument("--package", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--archive-url")
    parser.add_argument("--current-url")
    parser.add_argument("--allow-local-http", action="store_true")
    args = parser.parse_args()
    current = read_current(args.current_url) if args.current_url else None
    result = prepare_repository(args.blender, args.package, args.output, args.archive_url, current, args.allow_local_http)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
