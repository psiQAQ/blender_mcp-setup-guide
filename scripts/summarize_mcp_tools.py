"""Consolidate tool attempts without replacing earlier failures with retries."""

import json
from collections import Counter

from build_cache import LATEST
from check_reports import write_json
from publication import digest


def main():
    runs, attempts = [], []
    paths = sorted(LATEST.glob("mcp-tools-*-tests.json"))
    paths += [LATEST / "live-mcp-tools-tests.json"]
    for path in paths:
        if not path.is_file():
            continue
        report = json.loads(path.read_text(encoding="utf-8"))
        tests = report.get("tests", [])
        runs.append({"report": path.name, "sha256": digest(path), "status": report["status"],
                     "package_sha256": report.get("package_sha256"),
                     "tool_counts": dict(Counter(row["status"] for row in tests))})
        if report.get("error"):
            attempts.append({"report": path.name, "kind": "setup", "error": report["error"]})
        for row in tests:
            if row.get("status") == "Failed" or row.get("error"):
                attempts.append({"report": path.name, "kind": "tool", "tool": row.get("tool"),
                                 "final_status": row["status"], "arguments": row.get("arguments"),
                                 "error": row.get("error"), "traceback": row.get("traceback")})
        for row in report.get("probes", []):
            if row.get("status") == "Failed":
                attempts.append({"report": path.name, "kind": "probe", "probe": row["name"],
                                 "identifier": row.get("identifier"), "response": row.get("response"),
                                 "traceback": row.get("traceback")})
    write_json(LATEST / "mcp-tool-failures.json", {"runs": runs, "failed_attempts": attempts})
    print(json.dumps({"runs": len(runs), "failed_attempts": len(attempts)}, indent=2))


if __name__ == "__main__":
    main()
