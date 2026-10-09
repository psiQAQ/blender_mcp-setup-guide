"""Retain timed file and filter evidence around known native directory renames."""

import argparse
import json
from pathlib import Path

from check_reports import write_json
from publication import digest

FILE_IO = "{90CBDC39-4A3E-11D1-84F4-0000F80464E3}"
PROCESS = "{3D6FA8D0-FE05-11D0-9DDA-00C04FD7BA7C}"
IMAGE = "{2CB15D1D-5FC1-11D2-ABE1-00A0C911F518}"


def number(value):
    return int.from_bytes(bytes.fromhex(value.removeprefix("hex:")), "little")


def process_at(processes, pid, timestamp):
    candidates = [row for row in processes.get(pid, ()) if row["filetime"] <= timestamp]
    if not candidates:
        return {}
    return max(candidates, key=lambda row: row["filetime"])["properties"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("export", type=Path)
    parser.add_argument("--findings", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    findings = json.loads(args.findings.read_text())
    renames = [rename for case in findings["cases"] for rename in case["rename_events"]]
    processes, images = {}, []
    with args.metadata.open(encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            props = row["properties"]
            if row["provider"] == PROCESS and "ImageFileName" in props and "ProcessId" in props:
                if row["opcode"] in (1, 3):
                    processes.setdefault(number(props["ProcessId"]), []).append(row)
            elif row["provider"] == IMAGE and "ImageBase" in props and "ImageSize" in props:
                images.append(props)
    result = []
    for rename in renames:
        result.append({"case": rename["case"], "status": rename.get("caller_status", rename["status"]),
                       "event_status": rename["status"],
                       "filetime": rename["filetime"], "end_filetime": rename["end_filetime"],
                       "irp": rename["irp"], "pid": rename["pid"], "events": []})
    with args.export.open(encoding="utf-8") as stream:
        for line in stream:
            timestamp = int(line.split('"filetime":', 1)[1].split(',', 1)[0])
            windows = [case for case in result
                       if case["filetime"] - 200_000 <= timestamp <= case["end_filetime"] + 200_000]
            if not windows:
                continue
            row = json.loads(line)
            props = row["properties"]
            if row["provider"] == FILE_IO:
                # Retain creates in the same staging directory and callbacks
                # for this rename, rather than unrelated reused IRP pointers.
                for case in windows:
                    fragment = f"\\case-{case['case']}\\profile\\extensions\\integration_test\\blender_mcp_integration@"
                    path = props.get("OpenPath", "")
                    create = row["opcode"] == 64 and (path.endswith(fragment) or fragment + "\\" in path)
                    callback = 96 <= row["opcode"] <= 101 and case["filetime"] <= timestamp <= case["end_filetime"] and case["irp"] in (props.get("IrpPtr"), props.get("CallbackDataPtr"))
                    if not (create or callback):
                        continue
                    item = dict(row)
                    item["relative_microseconds"] = (timestamp - case["filetime"]) / 10
                    if create:
                        item["process"] = process_at(processes, row["pid"], timestamp)
                    if "RoutineAddr" in props:
                        address = number(props["RoutineAddr"])
                        item["routine_images"] = [image for image in images
                                                  if number(image["ImageBase"]) <= address < number(image["ImageBase"]) + number(image["ImageSize"])]
                    case["events"].append(item)
    write_json(args.output, {"export_sha256": digest(args.export), "findings_sha256": digest(args.findings),
                             "metadata_sha256": digest(args.metadata), "cases": result,
                             "trace_loss": findings.get("trace_loss", {"events": None, "buffers": None}),
                             "limitation": "An overlapping open or a filter callback alone does not establish which component returned ACCESS_DENIED; recorded providers do not expose every kernel state."})
    print(json.dumps([{"case": case["case"], "status": case["status"],
                       "events": len(case["events"]),
                       "external_pids": sorted({row["pid"] for row in case["events"] if row["opcode"] == 64 and row["pid"] != case["pid"]})}
                      for case in result]))


if __name__ == "__main__":
    main()
