"""Export compact, shareable official split-test evidence without local paths."""

import argparse
import json
from pathlib import Path

KEY_FILES = (
    "mcp/blmcp/tools/render_thumbnail_to_path_toolcode.py",
    "mcp/blmcp/tools/get_python_api_docs.py",
    "mcp/blmcp/tools_helpers/rst_parse_docs.py",
)


def export(report):
    assert report["execution_status"] == "Passed", "Incomplete runs cannot confirm an upstream issue"
    source = report["source"]
    result = {
        "transport": report["transport"], "source_commit": source["commit"],
        "source_repository": source["repository"], "extension_version": source["extension_version"],
        "server_version": source["server_version"], "extension_package": report["extension_package"],
        "source_hashes": {name: source["server_key_hashes"][name] for name in KEY_FILES},
        "extension_source_unchanged": all(row["host"]["installed_source_hashes"] == source["addon_hashes"]
                                          for row in report["sessions"]),
        "external_environment": report["external_environment"],
        "repository_issue_templates": source["repository_issue_templates"],
        "reproduction": report["reproduction"], "sessions": [],
    }
    for row in report["sessions"]:
        host = row["host"]
        session = {"session": row["session"], "connection": row["connection"],
                   "host": {key: host[key] for key in ("version", "python", "platform", "background", "graphics")},
                   "host_exit_code": row["host_exit_code"], "checks": []}
        for entry in row["checks"]:
            item = {key: entry[key] for key in ("case", "tool", "status", "seconds")}
            if "png" in entry:
                item.update(png=entry["png"], pixels=entry["pixels"],
                            settings_restored=entry["settings_after"] == row["render_settings_before"],
                            response={**entry["response"], "filepath": "<MCP temporary directory>/" + entry["png"]["name"]})
            else:
                item["arguments"] = entry["arguments"]
                item["response"] = {key: value for key, value in entry["response"].items()
                                    if key in {"kind", "found", "identifier", "parent", "available", "submodules"}}
            session["checks"].append(item)
        result["sessions"].append(session)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    data = export(json.loads(args.report.read_text(encoding="utf-8")))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(args.output)


if __name__ == "__main__":
    main()
