"""Require a successful CI run for this exact commit before reusing its artifacts."""

import argparse
import json
import os
import re
import urllib.request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9]+", args.run_id):
        raise ValueError("CI run ID must be numeric")
    request = urllib.request.Request(
        f"https://api.github.com/repos/{os.environ['GITHUB_REPOSITORY']}/actions/runs/{args.run_id}",
        headers={"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}", "Accept": "application/vnd.github+json", "User-Agent": "BlenderMCPIntegration"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        run = json.load(response)
    if run["status"] != "completed" or run["conclusion"] != "success" or run["head_sha"] != os.environ["GITHUB_SHA"]:
        raise ValueError("Select a successful CI run for the exact current commit")
    if run["path"] != ".github/workflows/ci.yml":
        raise ValueError("Selected run is not the Extension validation workflow")
    print(json.dumps({"run_id": run["id"], "head_sha": run["head_sha"], "conclusion": run["conclusion"]}))


if __name__ == "__main__":
    main()
