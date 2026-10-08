"""Validate stable tags and preview branch snapshots without floating build inputs."""

import re
import subprocess


def release_channel(record):
    channel = record.get("channel", "stable")
    if channel not in {"stable", "preview"}:
        raise ValueError("Unknown release channel")
    return channel


def verify_source(record, remote=False):
    channel = release_channel(record)
    if not re.fullmatch(r"[0-9a-f]{40}", record["commit"]):
        raise ValueError("Upstream source requires an exact commit")
    if channel == "stable":
        if record.get("tag") != f"v{record['version']}" or record.get("source_ref", record["tag"]) != record["tag"] or record.get("preview_revision", 0):
            raise ValueError("Stable publication requires an official version tag")
        references = [f"refs/tags/{record['tag']}", f"refs/tags/{record['tag']}^{{}}"]
    else:
        if record.get("tag") is not None or record.get("source_ref") != "main":
            raise ValueError("Preview publication requires a pinned main snapshot")
        if type(record.get("preview_revision")) is not int or record["preview_revision"] < 1:
            raise ValueError("Preview revision must be a positive integer")
        references = ["refs/heads/main"]
    if remote:
        output = subprocess.check_output(["git", "ls-remote", record["repository"], *references], text=True)
        refs = dict(line.split()[::-1] for line in output.splitlines())
        actual = refs.get(references[-1], refs.get(references[0]))
        if actual != record["commit"]:
            raise ValueError("Official upstream ref moved; update and revalidate the candidate")


def channel_path(record):
    channel = release_channel(record)
    line = ".".join(record.get("blender_min", "5.1.0").split(".")[:2])
    if line not in {"5.1", "5.2"}:
        raise ValueError("Unsupported Blender release line")
    if line == "5.1" and channel == "stable":
        return ""
    return f"blender-{line}/{channel}"
