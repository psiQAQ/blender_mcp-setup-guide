"""Prepare a validated release bundle without writing to any external service."""

import argparse
import json
import shutil
import zipfile
import tomllib
from pathlib import Path

from publication import ROOT, digest, extension_version, prepare_repository, prepare_collection, read_current
from platforms import resolve, records, package_name
from upstream_source import verify_source


def validate_artifacts(artifacts, expected_commit=None, identifier=None):
    identifier, target = resolve(identifier)
    record = json.loads((ROOT / "packaging/upstream.json").read_text())
    verify_source(record)
    version = extension_version(record)
    package = artifacts / "dist" / package_name(version, identifier)
    package_hash = digest(package)
    for name in ("unit-tests", "template-tests", "integration-tests", "upgrade-tests", "gui-tests", "minimum-tests", "repository-tests"):
        report = json.loads((artifacts / f"{name}.json").read_text())
        if report["status"] != "Passed":
            raise ValueError(f"Required validation did not pass: {name}")
        if report.get("platform") != identifier:
            raise ValueError(f"Validation report refers to another platform: {name}")
        if report.get("package_sha256") != package_hash:
            raise ValueError(f"Validation report refers to another ZIP: {name}")
        if name not in {"unit-tests", "template-tests"}:
            expected = target["minimum_blender" if name == "minimum-tests" else "blender"]["version"]
            if report.get("details", {}).get("blender", "").split(" ")[0] != expected or not report.get("details", {}).get("python", "").startswith("3.13."):
                raise ValueError(f"Validation report used the wrong Blender/Python environment: {name}")
    checksum = package.with_name(package.name + ".sha256")
    if checksum.read_text().split()[0] != digest(package):
        raise ValueError("Validated artifact checksum differs")
    provenance = artifacts / "dist" / f"provenance-{identifier}.json"
    with zipfile.ZipFile(package) as archive:
        source = json.loads(archive.read("provenance.json"))
        manifest = tomllib.loads(archive.read("blender_manifest.toml").decode())
    if manifest.get("id") != "blender_mcp_integration" or manifest.get("version") != version or manifest.get("platforms") != [identifier]:
        raise ValueError("Artifact manifest does not match the required platform and version")
    if (manifest.get("blender_version_min"), manifest.get("blender_version_max")) != (record["blender_min"], record["blender_max"]):
        raise ValueError("Artifact manifest compatibility differs from pinned source")
    if source != json.loads(provenance.read_text()) or any(source[key] != value for key, value in record.items()):
        raise ValueError("Artifact provenance differs from the current pinned source")
    if source.get("upstream_submodule_commit", source["commit"]) != record["commit"]:
        raise ValueError("Artifact submodule pointer differs from its source")
    if source["platform"] != identifier or source["wheels"] != json.loads((ROOT / "packaging" / target["wheel_lock"]).read_text()):
        raise ValueError("Artifact platform or wheel ABI differs from its lock")
    if source["requirements_sha256"] != digest(ROOT / "packaging" / target["requirements"]) or source["wheel_lock_sha256"] != digest(ROOT / "packaging" / target["wheel_lock"]):
        raise ValueError("Artifact dependency lock hashes differ")
    if expected_commit and (source.get("integration_commit") != expected_commit or source.get("integration_dirty") is not False):
        raise ValueError("The artifact was not built from the exact clean CI commit")
    return package, checksum, provenance


def validate_collection(artifacts, expected_commit):
    return {identifier: validate_artifacts(artifacts / identifier, expected_commit, identifier) for identifier in records()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blender", required=True, type=Path)
    parser.add_argument("--artifacts", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--archive-url", default="")
    parser.add_argument("--current-url", default="")
    parser.add_argument("--expected-commit")
    args = parser.parse_args()
    if all((args.artifacts / identifier).is_dir() for identifier in records()):
        artifacts = validate_collection(args.artifacts, args.expected_commit)
        current = read_current(args.current_url) if args.current_url else None
        result = prepare_collection(args.blender, {identifier: item[0] for identifier, item in artifacts.items()}, args.output, current=current)
        print(json.dumps(result, indent=2))
        return
    package, checksum, provenance = validate_artifacts(args.artifacts, args.expected_commit)
    record = json.loads(provenance.read_text())
    version = extension_version(record)
    current = read_current(args.current_url) if args.current_url else None
    result = prepare_repository(args.blender, package, args.output, args.archive_url or None, current)
    for path in (checksum, provenance, *sorted(args.artifacts.glob("*-tests.json"))):
        shutil.copyfile(path, args.output / path.name)
    (args.output / "release-notes.md").write_text(
        f"Blender MCP Integrated {version}: Windows x64 / {record['blender_min']} <= Blender < {record['blender_max']}.\n\n"
        f"Official upstream: {record.get('source_ref', record['tag'])} ({record['commit']}).\n\n"
        "Validated final ZIP: templates, authenticated MCP scene calls, lifecycle, HTTP repository upgrade and GUI timers. "
        "Human GUI and client acceptance is recorded separately.\n", encoding="utf-8",
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
