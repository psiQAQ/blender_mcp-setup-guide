"""Archive and optionally upload an immutable receipt of three public installations."""

import argparse
import json
import os
import re
import subprocess
import urllib.parse
import zipfile
from pathlib import Path

from publication import digest, verify_download
from publish_release import find_release, verify_tag

PLATFORMS = {"windows-x64", "linux-x64", "macos-arm64"}


def receipt_name(version, run_id):
    if not re.fullmatch(r"[1-9][0-9]*", str(run_id)):
        raise ValueError("A publication receipt requires a positive workflow run ID")
    return f"blender_mcp_integration-{version}-publication-{run_id}.zip"


def prepare_receipt(publication, reports, output, repository, commit, run_id):
    record = json.loads(publication.read_text(encoding="utf-8"))
    if set(record["packages"]) != PLATFORMS:
        raise ValueError("A publication receipt requires all three packages")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository) or not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("Invalid receipt repository or integration commit")
    if record.get("integration_commit") != commit:
        raise ValueError("Publication record belongs to another integration commit")
    entries = {"publication.json": publication.read_bytes()}
    receipt = {
        "schema_version": 1, "status": "Passed", "repository": repository,
        "integration_commit": commit, "publication_run_id": str(run_id),
        "extension_version": record["extension_version"], "channel": record.get("channel", "stable"),
        "publication_sha256": digest(publication), "packages": {},
    }
    for platform in sorted(PLATFORMS):
        path = reports / f"publication-{platform}" / "published-tests.json"
        report = json.loads(path.read_text(encoding="utf-8"))
        package = record["packages"][platform]
        if report.get("status") != "Passed" or report.get("platform") != platform or report.get("package_sha256") != package["sha256"]:
            raise ValueError(f"Public installation report does not match the package: {platform}")
        if report.get("publication_run_id") != str(run_id) or report.get("integration_commit") != commit:
            raise ValueError(f"Public installation report belongs to another workflow or commit: {platform}")
        entries[f"{platform}-published-tests.json"] = path.read_bytes()
        receipt["packages"][platform] = {"package_sha256": package["sha256"], "report_sha256": digest(path)}
    entries["receipt.json"] = (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode()
    output.mkdir(parents=True, exist_ok=True)
    destination = output / receipt_name(record["extension_version"], run_id)
    # Reproducible bytes permit retries without replacing an existing receipt.
    import io
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_STORED) as archive:
        for name, content in sorted(entries.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, content)
    content = buffer.getvalue()
    if destination.exists():
        if destination.read_bytes() != content:
            raise ValueError("The publication receipt is immutable")
    else:
        with destination.open("xb") as stream:
            stream.write(content)
    return destination


def upload_receipt(repository, tag, commit, receipt, token):
    verify_tag(repository, tag, commit, token)
    release = find_release(repository, tag, token)
    if release is None or release["draft"]:
        raise ValueError("Publication receipts require an existing public Release")
    existing = [asset for asset in release["assets"] if asset["name"] == receipt.name]
    if len(existing) > 1:
        raise ValueError("Release repeats the receipt asset name")
    if not existing:
        subprocess.run(["gh", "release", "upload", tag, "--repo", repository, str(receipt)], check=True)
    url = f"https://github.com/{repository}/releases/download/{urllib.parse.quote(tag, safe='')}/{urllib.parse.quote(receipt.name, safe='')}"
    verify_download(url, digest(receipt), receipt.stat().st_size)
    return url


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--publication", required=True, type=Path)
    parser.add_argument("--reports", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--upload", action="store_true")
    args = parser.parse_args()
    receipt = prepare_receipt(args.publication, args.reports, args.output, args.repository, args.commit, args.run_id)
    result = {"status": "Passed", "receipt": str(receipt), "sha256": digest(receipt)}
    if args.upload:
        version = json.loads(args.publication.read_text())["extension_version"]
        result["archive_url"] = upload_receipt(args.repository, f"v{version}", args.commit, receipt, os.environ["GH_TOKEN"])
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
