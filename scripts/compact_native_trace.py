"""Archive a completed local ETL without changing any event bytes."""

import argparse
import json
import gzip
import hashlib
from pathlib import Path

from build_cache import checked_path, remove_cache
from check_reports import write_json
from publication import digest


def restored_digest(path):
    with gzip.open(path, "rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def archive_trace(source):
    source = checked_path(source)
    target = checked_path(source.with_suffix(source.suffix + ".gz"))
    pending = checked_path(target.with_suffix(target.suffix + ".pending"))
    if target.exists() or pending.exists():
        raise FileExistsError("Review the existing trace archive before replacing it")
    checksum = hashlib.sha256()
    with source.open("rb") as original, pending.open("xb") as destination:
        with gzip.GzipFile(filename="", fileobj=destination, mode="wb", compresslevel=1, mtime=0) as archived:
            while chunk := original.read(1024 * 1024):
                checksum.update(chunk)
                archived.write(chunk)
    expected = checksum.hexdigest()
    if restored_digest(pending) != expected:
        raise ValueError("Restored ETL hash differs; retain the original")
    pending.rename(target)
    return {"status": "Passed", "original_sha256": expected, "original_bytes": source.stat().st_size,
            "archive": str(target), "archive_sha256": digest(target), "archive_bytes": target.stat().st_size,
            "restored_bytes_verified": "Passed"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--retire-source", action="store_true")
    args = parser.parse_args()
    directory = checked_path(args.directory)
    control_path = directory / "trace-control.json"
    control = json.loads(control_path.read_text(encoding="utf-8-sig"))
    source = checked_path(directory / "native-install.etl")
    if control["status"] != "Captured" or Path(control["trace"]).resolve() != source.resolve():
        raise ValueError("Only this directory's completed recording can be archived")
    manifest = archive_trace(source)
    manifest["source_retired"] = False
    write_json(directory / "retention.json", manifest)
    if args.retire_source:
        manifest["source_retired"] = remove_cache(source)
        if not manifest["source_retired"]:
            manifest["status"] = "Failed"
        write_json(directory / "retention.json", manifest)
    control["retained_compressed_trace"] = manifest["archive"]
    control["original_trace_sha256"] = manifest["original_sha256"]
    control["archive_sha256"] = manifest["archive_sha256"]
    write_json(control_path, control)
    print(json.dumps({key: manifest[key] for key in ("status", "original_bytes", "archive_bytes", "source_retired")}))


if __name__ == "__main__":
    main()
