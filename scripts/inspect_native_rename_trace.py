"""Correlate each observed native rename with child file-object lifetimes."""

import argparse
import json
import re
from collections import Counter
from pathlib import Path

from check_reports import write_json
from publication import digest


FILE_IO = "{90CBDC39-4A3E-11D1-84F4-0000F80464E3}"


def succeeded(status):
    if not status or not status.startswith("hex:"):
        return None
    return int.from_bytes(bytes.fromhex(status[4:]), "little") < 0x80000000


def summarize_children(snapshot):
    children = snapshot.pop("child_file_objects")
    active, cleaned, failed, unknown = [], [], [], []
    for child in children:
        success = succeeded(child["open_status"])
        if success is False:
            failed.append(child)
        elif success is None:
            unknown.append(child)
        elif child.get("cleanup_at", snapshot["filetime"] + 1) <= snapshot["filetime"]:
            cleaned.append(child)
        else:
            active.append(child)
    snapshot["uncleaned_child_file_objects"] = active
    snapshot["cleaned_not_closed_counts_by_pid"] = dict(Counter(child["pid"] for child in cleaned))
    snapshot["cleaned_not_closed_samples"] = cleaned[:8]
    snapshot["failed_open_count"] = len(failed)
    snapshot["unknown_open_count"] = len(unknown)
    snapshot["unknown_open_samples"] = unknown[:8]


def trace_loss_summary(path):
    if path is None:
        return {"events": None, "buffers": None}
    text = path.read_text(encoding="utf-8-sig")
    result = {"statistics_sha256": digest(path)}
    for name in ("Events", "Buffers"):
        found = re.search(r"Total\s+#\s+Lost " + name + r"\s*:\s*(\d+)", text)
        if found is None:
            raise ValueError(f"Missing total lost {name.lower()} in trace statistics")
        result[name.lower()] = int(found.group(1))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("export", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--trace-statistics", type=Path,
                        help="xperf tracestats for this ETL; omitted loss counts remain unknown")
    parser.add_argument("--partial", action="store_true", help="Analyze a stopped export prefix; not a complete trace inventory")
    args = parser.parse_args()
    report = json.loads(args.report.read_text())
    cases = {}
    for case in report["cases"]:
        rename = case["renames"][0]
        cases[rename["pid"]] = {"case": case["case"], "observed": rename, "rename_events": []}
    files, creates, pending, snapshots, counts = {}, {}, {}, [], Counter()
    with args.export.open(encoding="utf-8") as stream:
        for line in stream:
            if not any(marker in line for marker in ('"opcode":64,', '"opcode":65,', '"opcode":66,',
                                                     '"opcode":71,', '"opcode":76,')):
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                if args.partial and not stream.readline():
                    break
                raise
            if event["provider"] != FILE_IO:
                continue
            counts[event["opcode"]] += 1
            props, timestamp, pid = event["properties"], event["filetime"], event["pid"]
            irp, obj = props.get("IrpPtr"), props.get("FileObject")
            if event["opcode"] == 64 and obj and "OpenPath" in props:
                row = {"path": props["OpenPath"], "pid": pid, "opened_at": timestamp,
                       "file_object": obj, "properties": props, "open_status": None}
                files[obj] = row
                creates[irp] = row
                for snapshot in pending.values():
                    fragment = f"\\case-{snapshot['case']}\\profile\\extensions\\integration_test\\blender_mcp_integration@"
                    if row["path"].endswith(fragment) or fragment + "\\" in row["path"]:
                        snapshot["opens_during_rename"].append(row)
            elif event["opcode"] == 65 and obj in files:
                files[obj]["cleanup_at"] = timestamp
            elif event["opcode"] == 66 and obj in files:
                files[obj]["closed_at"] = timestamp
                files.pop(obj)
            elif event["opcode"] == 71 and pid in cases:
                case = cases[pid]
                fragment = f"\\case-{case['case']}\\profile\\extensions\\integration_test\\blender_mcp_integration@"
                # Keep this generation of the object so later Cleanup/Close and
                # OperationEnd events can complete its lifetime and open status.
                child_objects = [row for row in files.values()
                                 if row["path"].endswith(fragment) or fragment + "\\" in row["path"]]
                snapshot = {"pid": pid, "case": case["case"], "filetime": timestamp,
                            "irp": irp, "properties": props, "child_file_objects": child_objects,
                            "opens_during_rename": [], "caller_status": case["observed"]["status"],
                            "status": "Not Run"}
                case["rename_events"].append(snapshot)
                snapshots.append(snapshot)
                pending[(pid, irp)] = snapshot
            elif event["opcode"] == 76:
                if opened := creates.pop(irp, None):
                    opened["open_status"] = props.get("NtStatus")
                if renamed := pending.pop((pid, irp), None):
                    renamed["end_filetime"] = timestamp
                    renamed["ntstatus"] = props.get("NtStatus")
                    renamed["status"] = "Passed" if props.get("NtStatus") == "hex:00000000" else "Failed"
    for snapshot in snapshots:
        summarize_children(snapshot)
    result = {"export_sha256": digest(args.export), "installer_report_sha256": digest(args.report), "partial_export": args.partial,
              "trace_loss": trace_loss_summary(args.trace_statistics),
              "file_event_counts": dict(counts), "cases": list(cases.values()),
              "limitation": "Loss counts apply only to the recorded providers. Absence cannot rule out an unrecorded kernel or filter state; a live file object is not by itself proof of a live user handle."}
    write_json(args.output, result)
    print(json.dumps({"cases": len(cases), "captured_native_renames": len(snapshots),
                      "rename_ntstatus": [(row["case"], row.get("ntstatus"),
                                            len(row["uncleaned_child_file_objects"]),
                                            row["cleaned_not_closed_counts_by_pid"],
                                            row["failed_open_count"], row["unknown_open_count"])
                                           for row in snapshots]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
