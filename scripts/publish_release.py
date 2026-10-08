"""Upload immutable validated CI assets; verify every asset before producing an index URL."""

import argparse
import json
import os
import re
import subprocess
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

from prepare_release import validate_collection
from publication import ROOT, digest, extension_version, verify_download, prepare_collection, read_current, check_forward
from upstream_source import release_channel, verify_source


def github_json(repository, endpoint, token, allow_missing=False):
    request = urllib.request.Request(
        f"https://api.github.com/repos/{repository}/{endpoint}",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json", "User-Agent": "BlenderMCPIntegration"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        if allow_missing and error.code == 404:
            return None
        raise


def verify_tag(repository, tag, expected_commit, token):
    reference = github_json(repository, f"git/ref/tags/{urllib.parse.quote(tag, safe='')}", token)["object"]
    for _ in range(5):
        if reference["type"] == "commit":
            if reference["sha"] != expected_commit:
                raise ValueError("Remote release tag does not reference the validated CI commit")
            return
        if reference["type"] != "tag":
            raise ValueError("Release ref does not identify a commit or annotated tag")
        reference = github_json(repository, f"git/tags/{reference['sha']}", token)["object"]
    raise ValueError("Release tag nesting exceeds the expected limit")


def find_release(repository, tag, token):
    published = github_json(repository, f"releases/tags/{urllib.parse.quote(tag, safe='')}", token, allow_missing=True)
    if published is not None:
        return published
    page = 1
    while True:
        releases = github_json(repository, f"releases?per_page=100&page={page}", token)
        for release in releases:
            if release["tag_name"] == tag:
                return release
        if len(releases) < 100:
            return None
        page += 1


def prepare_release_assets(collection, artifacts, output, version):
    """Keep installers visible and preserve validated records in one reproducible archive."""
    output.mkdir(parents=True, exist_ok=True)
    evidence = output / f"blender_mcp_integration-{version}-evidence.zip"
    assets, entries = [], []
    for identifier, (package, checksum, provenance) in collection.items():
        assets.extend((package, checksum))
        entries.append((provenance.name, provenance))
        entries.extend((f"{identifier}-{report.name}", report)
                       for report in sorted((artifacts / identifier).glob("*-tests.json")))
    with zipfile.ZipFile(evidence, "w", compression=zipfile.ZIP_STORED) as archive:
        for name, path in sorted(entries):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes())
    return [*assets, evidence]


def publish_assets(repository, tag, expected_commit, assets, notes, marker, token, finalize=True, channel="stable"):
    if channel not in {"stable", "preview"}:
        raise ValueError("Unknown publication channel")
    existing = find_release(repository, tag, token)
    base = f"https://github.com/{repository}/releases/download/{urllib.parse.quote(tag, safe='')}"

    def require_release_source(release):
        if release["prerelease"] != (channel == "preview"):
            raise ValueError("The matching Release has a different publication channel")
        if release["draft"] and (
            marker not in (release.get("body") or "") or release["target_commitish"] != expected_commit
        ):
            raise ValueError("The matching draft does not belong to this validated CI publication")

    def readback(path, release):
        if release["draft"]:
            asset = next(item for item in release["assets"] if item["name"] == path.name)
            verify_download(
                f"https://api.github.com/repos/{repository}/releases/assets/{asset['id']}",
                digest(path), path.stat().st_size,
                headers={"Authorization": f"Bearer {token}", "Accept": "application/octet-stream"},
            )
        else:
            verify_download(f"{base}/{urllib.parse.quote(path.name, safe='')}", digest(path), path.stat().st_size)

    if existing is None:
        subprocess.run([
            "gh", "release", "create", tag, "--repo", repository, "--verify-tag", "--draft",
            "--target", expected_commit, "--title", tag.removeprefix("v"), "--notes-file", str(notes),
        ] + (["--prerelease", "--latest=false"] if channel == "preview" else []), check=True)
        existing = find_release(repository, tag, token)
        if existing is None:
            raise ValueError("Created draft Release was not returned by the authenticated API")
    require_release_source(existing)
    if set(asset["name"] for asset in existing["assets"]) - {path.name for path in assets}:
        raise ValueError("The matching Release contains unexpected assets")
    present = {asset["name"] for asset in existing["assets"]}
    for path in assets:
        if path.name in present:
            readback(path, existing)
    missing = [path for path in assets if path.name not in present]
    if missing:
        subprocess.run(["gh", "release", "upload", tag, "--repo", repository, *map(str, missing)], check=True)
        existing = github_json(repository, f"releases/{existing['id']}", token)
        require_release_source(existing)
    for path in assets:
        readback(path, existing)
    if not finalize:
        return f"{base}/{urllib.parse.quote(assets[0].name, safe='')}"
    if existing["draft"]:
        subprocess.run(["gh", "release", "edit", tag, "--repo", repository, "--draft=false"] +
                       (["--prerelease", "--latest=false"] if channel == "preview" else []), check=True)
        for path in assets:
            verify_download(f"{base}/{urllib.parse.quote(path.name, safe='')}", digest(path), path.stat().st_size)
    return f"{base}/{urllib.parse.quote(assets[0].name, safe='')}"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--expected-commit", required=True)
    parser.add_argument("--artifacts", required=True, type=Path)
    parser.add_argument("--phase", choices=("stage", "finalize"), required=True)
    parser.add_argument("--blender", type=Path)
    parser.add_argument("--index-output", required=True, type=Path)
    parser.add_argument("--current-url", required=True)
    parser.add_argument("--channel", choices=("stable", "preview"), required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", args.repository):
        raise ValueError("Invalid GitHub repository")
    collection = validate_collection(args.artifacts, args.expected_commit)
    source = json.loads(next(iter(collection.values()))[2].read_text())
    if args.channel != release_channel(source):
        raise ValueError("Requested channel differs from the validated source")
    verify_source(source, remote=True)
    version = extension_version(source)
    if args.tag != f"v{version}":
        raise ValueError("Release tag must match the validated integration version")
    token = os.environ["GH_TOKEN"]
    verify_tag(args.repository, args.tag, args.expected_commit, token)
    asset_directory = ROOT / "build/release-assets"
    import hashlib
    package_hashes = {identifier: digest(item[0]) for identifier, item in collection.items()}
    set_hash = hashlib.sha256(json.dumps(package_hashes, sort_keys=True).encode()).hexdigest()
    marker = f"<!-- blender-mcp-integration {args.expected_commit} {version} {set_hash} -->"
    assets = prepare_release_assets(collection, args.artifacts, asset_directory, version)
    notes = ROOT / "build/release-notes.md"
    notes.parent.mkdir(parents=True, exist_ok=True)
    notes.write_text(
        f"Blender MCP Integrated {version}: Windows x64, Linux x64, macOS Apple Silicon.\n\n"
        f"Channel: {args.channel}. Requires {source['blender_min']} <= Blender < {source['blender_max']} / CPython 3.13.\n\n"
        f"Official upstream: {source.get('source_ref', source['tag'])} ({source['commit']}).\n\n"
        "Validated final ZIP: two generated templates, authenticated MCP scene calls, lifecycle, "
        "HTTP repository upgrade and GUI timer checks. Human GUI and client acceptance remains separate.\n\n"
        "Install the ZIP matching your platform. The evidence ZIP contains provenance and validation reports; "
        "it is for auditing and is not a Blender extension.\n\n"
        f"{marker}\n", encoding="utf-8",
    )
    current = read_current(args.current_url)
    if args.phase == "stage":
        if args.blender is None:
            raise ValueError("Index staging requires --blender")
        # Every remote draft asset is read back before any index is bound to its future public URL.
        archive_url = publish_assets(args.repository, args.tag, args.expected_commit, assets, notes, marker, token, finalize=False, channel=args.channel)
        candidate = prepare_collection(args.blender, {identifier: item[0] for identifier, item in collection.items()}, args.index_output, current=current)
        base = archive_url.rsplit("/", 1)[0]
        index_path = args.index_output / "index.json"
        index = json.loads(index_path.read_text())
        for item in index["data"]:
            identifier, = item["platforms"]
            item["archive_url"] = f"{base}/{urllib.parse.quote(collection[identifier][0].name, safe='')}"
            candidate["packages"][identifier]["archive_url"] = item["archive_url"]
        index_path.write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")
        (args.index_output / "publication.json").write_text(json.dumps(candidate, indent=2) + "\n", encoding="utf-8")
        for package, _, _ in collection.values():
            (args.index_output / package.name).unlink()
        import html
        links = "".join(f'<li><a href="{html.escape(entry["archive_url"], quote=True)}">{identifier}</a></li>' for identifier, entry in candidate["packages"].items())
        (args.index_output / "index.html").write_text(f'<!doctype html><html lang="en"><meta charset="utf-8"><title>Blender MCP Integrated</title><h1>{version}</h1><p>{args.channel}: {source["blender_min"]} ≤ Blender &lt; {source["blender_max"]} / CPython 3.13</p><ul>{links}</ul><p>Add index.json to Blender Extensions repositories.</p></html>\n', encoding="utf-8")
    else:
        candidate = json.loads((args.index_output / "publication.json").read_text())
        if candidate["integration_commit"] != args.expected_commit or candidate["extension_version"] != version or {key: item["sha256"] for key, item in candidate["packages"].items()} != package_hashes:
            raise ValueError("Staged index does not describe this validated asset set")
        check_forward(current, candidate)
        archive_url = publish_assets(args.repository, args.tag, args.expected_commit, assets, notes, marker, token, channel=args.channel)
    if output := os.environ.get("GITHUB_OUTPUT"):
        with open(output, "a", encoding="utf-8", newline="\n") as stream:
            stream.write(f"archive_url={archive_url}\n")
    print(json.dumps({"tag": args.tag, "archive_url": archive_url, "packages": package_hashes, "phase": args.phase}))


if __name__ == "__main__":
    main()
