"""Retain compact rename/scan evidence from this task's ETW JSONL export."""

import argparse
import json
from collections import Counter
from pathlib import Path

from check_reports import write_json
from publication import digest


FILE_IO = "{90CBDC39-4A3E-11D1-84F4-0000F80464E3}"
PROCESS = "{3D6FA8D0-FE05-11D0-9DDA-00C04FD7BA7C}"
ENGINE = "{0A002690-3839-4E3A-B3B6-96D8DF868D99}"


def number(value):
    return int.from_bytes(bytes.fromhex(value.removeprefix("hex:")), "little")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    workers, renames, ends, scans, counts = {}, [], {}, [], Counter()
    # IRP values are reused. Match each rename with its following end event.
    pending = {}
    with args.input.open(encoding="utf-8") as source:
        for line in source:
            if not any(marker in line for marker in ('"opcode":71,', '"opcode":80,', '"opcode":76,',
                                                     '"ImageFileName":"python.exe"', '"event_id":64,',
                                                     '"event_id":5,', '"event_id":6,')):
                continue
            event = json.loads(line)
            properties = event["properties"]
            if event["provider"] == PROCESS and properties.get("ImageFileName") == "python.exe":
                if "native_install_probe.py" in properties.get("CommandLine", ""):
                    workers[number(properties["ProcessId"])] = properties["CommandLine"]
            elif event["provider"] == FILE_IO:
                if event["opcode"] == 71:
                    row = {key: event[key] for key in ("pid", "tid", "filetime", "properties")}
                    pending[properties["IrpPtr"]] = row
                elif event["opcode"] == 76:
                    if row := pending.pop(properties.get("IrpPtr"), None):
                        row["end"] = event["properties"]
                        row["end_filetime"] = event["filetime"]
                        renames.append(row)
                elif event["opcode"] == 80:
                    ends.setdefault(event["pid"], []).append(properties)
            elif event["provider"] == ENGINE and properties.get("Path", "").endswith("blender_manifest.toml"):
                counts[event["event_id"]] += 1
                if len(scans) < 20:
                    scans.append({key: event[key] for key in ("pid", "filetime", "event_id", "properties")})
    rows = [row for row in renames if row["pid"] in workers]
    result = {"input_sha256": digest(args.input), "worker_processes": workers,
              "native_worker_renames": rows,
              "rename_paths": {pid: paths for pid, paths in ends.items() if pid in workers},
              "manifest_scan_event_counts": dict(counts), "manifest_scan_samples": scans,
              "failed_native_renames": sum(number(row["end"]["NtStatus"]) != 0 for row in rows),
              "scanner_attribution": "Not Run: successful renames cannot establish the cause of a different failure"}
    write_json(args.output, result)
    print(json.dumps({"workers": len(workers), "renames": len(rows), "failed_renames": result["failed_native_renames"]}))


if __name__ == "__main__":
    main()
