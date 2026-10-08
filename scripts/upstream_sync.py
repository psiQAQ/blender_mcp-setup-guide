"""Inspect Blender Lab stable Releases and emit a reviewable pinned-source proposal."""

import argparse
import difflib
import json
import re
import subprocess
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
API = "https://projects.blender.org/api/v1/repos/lab/blender_mcp/releases"


def fetch_releases():
    releases = []
    for page in range(1, 101):
        request = urllib.request.Request(f"{API}?limit=50&page={page}", headers={"User-Agent": "BlenderMCPIntegration"})
        with urllib.request.urlopen(request, timeout=30) as response:
            entries = json.load(response)
        releases.extend(entries)
        if len(entries) < 50:
            return releases
    raise RuntimeError("Release API pagination exceeded the expected limit")


def latest_stable(releases):
    stable = [release for release in releases if not release["draft"] and not release["prerelease"]
              and re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+", release["tag_name"])]
    if not stable:
        raise ValueError("Official API returned no stable Release")
    return max(stable, key=lambda release: tuple(map(int, release["tag_name"][1:].split("."))))


def resolve_tag(repository, tag):
    lines = subprocess.check_output(["git", "ls-remote", "--tags", repository, f"refs/tags/{tag}", f"refs/tags/{tag}^{{}}"], text=True).splitlines()
    references = dict(line.split(maxsplit=1)[::-1] for line in lines)
    commit = references.get(f"refs/tags/{tag}^{{}}", references.get(f"refs/tags/{tag}"))
    if commit is None or not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError(f"Cannot resolve official stable tag {tag}")
    return commit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "build/upstream-review")
    args = parser.parse_args()
    path = ROOT / "packaging/upstream.json"
    previous_text = path.read_text(encoding="utf-8")
    pinned = json.loads(previous_text)
    release = latest_stable(fetch_releases())
    commit = resolve_tag(pinned["repository"], release["tag_name"])
    changed = (release["tag_name"], commit) != (pinned["tag"], pinned["commit"])
    if release["tag_name"] == pinned["tag"] and commit != pinned["commit"]:
        raise ValueError("The pinned official tag moved; investigate before updating")
    proposal = {**pinned, "version": release["tag_name"][1:], "tag": release["tag_name"], "commit": commit}
    if changed:
        proposal["integration_revision"] = 1
    args.output.mkdir(parents=True, exist_ok=True)
    proposed_text = json.dumps(proposal, indent=2) + "\n"
    (args.output / "upstream.json").write_text(proposed_text, encoding="utf-8")
    patch = "".join(difflib.unified_diff(previous_text.splitlines(True), proposed_text.splitlines(True),
                                       fromfile="a/packaging/upstream.json", tofile="b/packaging/upstream.json"))
    (args.output / "upstream.patch").write_text(patch, encoding="utf-8")
    report = {"changed": changed, "current": pinned["tag"], "stable": release["tag_name"], "commit": commit,
              "official_release": release["html_url"], "published_at": release["published_at"]}
    (args.output / "release.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (args.output / "review.md").write_text(
        f"# Official upstream review\n\nPinned: {pinned['tag']} / {pinned['commit']}\n\n"
        f"Stable Release: [{release['tag_name']}]({release['html_url']}) / {commit}\n\n"
        f"Source change: {'available' if changed else 'none'}\n\n"
        "Before accepting a source update, review the official bridge and tools diff, refresh both requirements and wheel locks, "
        "recheck Blender/Python compatibility, then run the complete final-ZIP validation and upgrade suite. "
        "The proposal does not modify tracked files or publish a release.\n", encoding="utf-8",
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
