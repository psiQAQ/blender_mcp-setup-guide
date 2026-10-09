"""Reproduce MCP issues with an official Extension and an external uv stdio server."""

import argparse
import asyncio
import hashlib
import importlib.metadata
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tarfile
import time
import tomllib
import traceback
from pathlib import Path

from build_cache import LATEST, current_work
from check_reports import run_check, write_json
from mcp_checks import SDK_READ_TIMEOUT, unwrap

ROOT = Path(__file__).resolve().parents[1]
OFFICIAL = "https://projects.blender.org/lab/blender_mcp.git"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def free_port():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def checked_command(command, run, environment=None):
    with (run / "service.log").open("a", encoding="utf-8") as log:
        result = subprocess.run(command, env=environment, stdout=log, stderr=subprocess.STDOUT,
                                stdin=subprocess.DEVNULL)
    if result.returncode:
        raise RuntimeError(f"{Path(command[0]).name} exited {result.returncode}; see service.log")


def prepare(args, run, report):
    if not re.fullmatch(r"[0-9a-f]{40}", args.upstream_ref):
        raise ValueError("--upstream-ref must be a complete lowercase commit SHA")
    source_repo = ROOT / "submodules/blender_mcp"
    remote = subprocess.check_output(["git", "-C", str(source_repo), "remote", "get-url", "origin"], text=True).strip()
    if remote.rstrip("/") != OFFICIAL:
        raise ValueError(f"Unexpected upstream remote: {remote}")
    source = run / "source"
    source.mkdir()
    archive = run / "source.tar"
    with archive.open("wb") as output:
        subprocess.run(["git", "-C", str(source_repo), "archive", "--format=tar", args.upstream_ref],
                       stdout=output, check=True)
    with tarfile.open(archive) as package:
        package.extractall(source, filter="data")
    archive.unlink()
    addon = source / "addon/blender_mcp_addon"
    manifest = tomllib.loads((addon / "blender_manifest.toml").read_text(encoding="utf-8"))
    server = tomllib.loads((source / "mcp/pyproject.toml").read_text(encoding="utf-8"))["project"]
    expected = {str(path.relative_to(addon)).replace("\\", "/"): sha256(path)
                for path in sorted(addon.rglob("*")) if path.is_file() and path.suffix in {".py", ".toml"}}
    report.update(source={"repository": OFFICIAL, "commit": args.upstream_ref,
        "extension_id": manifest["id"], "extension_version": manifest["version"],
        "server_version": server["version"], "addon_hashes": expected,
        "server_key_hashes": {str(p.relative_to(source)).replace("\\", "/"): sha256(p)
                              for p in sorted((source / "mcp/blmcp").rglob("*.py"))},
        "repository_issue_templates": [str(p.relative_to(source)).replace("\\", "/")
            for prefix in (".github", ".gitea", ".forgejo") for p in sorted((source / prefix).rglob("*"))
            if p.is_file() and "issue_template" in str(p).lower()]})
    assert manifest["id"] == "mcp"
    output = run / "package"
    output.mkdir()
    checked_command([str(args.blender), "--background", "--factory-startup", "--command", "extension", "build",
                     "--source-dir", str(addon), "--output-dir", str(output)], run)
    packages = list(output.glob("*.zip"))
    assert len(packages) == 1, packages
    report["extension_package"] = {"name": packages[0].name, "sha256": sha256(packages[0]),
                                   "size": packages[0].stat().st_size}
    checked_command([str(args.blender), "--background", "--factory-startup", "--command", "extension", "validate",
                     str(packages[0])], run)
    uv = shutil.which("uv")
    if not uv:
        raise RuntimeError("uv is required for the external official tool environment")
    environment = {**os.environ, "UV_TOOL_DIR": str(run / "tools"), "UV_TOOL_BIN_DIR": str(run / "tool-bin"),
                   "UV_CACHE_DIR": str(run / "uv-cache"), "UV_PYTHON_INSTALL_DIR": str(run / "uv-python"),
                   "UV_PYTHON_DOWNLOADS": "never"}
    checked_command([uv, "tool", "install", "--python", sys.executable, str(source / "mcp")], run, environment)
    python = run / "tools/blender-mcp" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    assert python.is_file(), python
    report["external_environment"] = {"installer": subprocess.check_output([uv, "--version"], text=True).strip(),
                                       "isolation": "project-local uv tool environment; no integrated Extension or _vendor"}
    return python, environment


async def exercise(command, environment, control, report, report_path, row):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    with (control / "service.log").open("w", encoding="utf-8") as log:
        async with stdio_client(StdioServerParameters(command=str(command), env=environment), errlog=log) as (read, write):
            async with ClientSession(read, write, read_timeout_seconds=SDK_READ_TIMEOUT) as session:
                initialized = await session.initialize()
                row["server"] = initialized.serverInfo.model_dump(mode="json")
                row["tool_count"] = len((await session.list_tools()).tools)
                row["scene"] = unwrap(await session.call_tool("get_objects_summary", {}))
                assert "Cube" in json.dumps(row["scene"]), row["scene"]
                row["connection"] = "Passed"

                async def case(name, tool, arguments, verify):
                    entry = {"case": name, "tool": tool, "arguments": arguments, "status": "Not Run"}
                    row["checks"].append(entry)
                    started = time.monotonic()
                    try:
                        value = unwrap(await session.call_tool(tool, arguments))
                        entry["response"] = value
                        await verify(value, entry)
                        entry["status"] = "Passed"
                    except Exception as error:
                        entry.update(status="Failed", error=f"{type(error).__name__}: {error}")
                    finally:
                        entry["seconds"] = round(time.monotonic() - started, 3)
                        write_json(report_path, report)
                        print(f"session {row['session']} {name}: {entry['status']}", flush=True)

                async def docs(value, entry):
                    assert value["found"], value

                for identifier in ("bpy.types.Object.location", "bpy.ops.mesh.primitive_cube_add", "bpy.types.Object.Object.location"):
                    await case(identifier, "get_python_api_docs", {"identifier": identifier}, docs)

                settings_code = (
                    "import bpy\nr = bpy.context.scene.render\nresult = "
                    "{'x':r.resolution_x, 'y':r.resolution_y, 'percentage':r.resolution_percentage, "
                    "'filepath':r.filepath, 'format':r.image_settings.file_format, 'engine':r.engine, "
                    "'samples':bpy.context.scene.cycles.samples}"
                )
                before = unwrap(await session.call_tool("execute_blender_code", {"code": settings_code}))
                row["render_settings_before"] = before

                async def thumbnail(value, entry):
                    path = Path(value["filepath"])
                    assert path.is_file(), value
                    png = path.read_bytes()
                    assert png[:8] == b"\x89PNG\r\n\x1a\n", "Not a PNG"
                    entry["png"] = {"name": path.name, "bytes": len(png), "sha256": sha256(path),
                                    "width": int.from_bytes(png[16:20], "big"),
                                    "height": int.from_bytes(png[20:24], "big")}
                    code = (
                        f"import bpy\ni=bpy.data.images.load({str(path)!r}, check_existing=False)\n"
                        "try:\n    values=[v for j,v in enumerate(i.pixels) if j%4!=3]\n"
                        "    result={'minimum':min(values),'maximum':max(values)}\n"
                        "finally:\n    bpy.data.images.remove(i)"
                    )
                    entry["pixels"] = unwrap(await session.call_tool("execute_blender_code", {"code": code}))
                    entry["settings_after"] = unwrap(await session.call_tool("execute_blender_code", {"code": settings_code}))
                    assert entry["settings_after"] == before, entry["settings_after"]
                    assert entry["pixels"]["maximum"] - entry["pixels"]["minimum"] > 0.1, entry["pixels"]
                    assert max(entry["png"]["width"], entry["png"]["height"]) <= 320, entry["png"]

                for index in range(1, 4):
                    await case(f"thumbnail-{index}", "render_thumbnail_to_path",
                               {"output_path": str(control / f"thumbnail-{index}.png")}, thumbnail)


def worker(args, run, report, path):
    import blmcp

    assert "_vendor" not in blmcp.__file__, blmcp.__file__
    report["external_environment"].update(python=sys.version, dependencies={
        dist.metadata["Name"]: dist.version for dist in sorted(importlib.metadata.distributions(),
                                                              key=lambda d: d.metadata["Name"].lower())})
    command = Path(sys.executable).with_name("blender-mcp.exe" if os.name == "nt" else "blender-mcp")
    assert command.is_file(), command
    package = next((run / "package").glob("*.zip"))
    for number in range(1, 4):
        control = run / f"session-{number}"
        control.mkdir()
        port = free_port()
        environment = {**os.environ, "BLENDER_USER_RESOURCES": str(control / "profile"),
                       "BLENDER_USER_CONFIG": str(control / "profile/config"),
                       "BLENDER_MCP_HOST": "127.0.0.1", "BLENDER_MCP_PORT": str(port),
                       "BLENDER_PATH": str(args.blender.resolve()), "PYTHONDONTWRITEBYTECODE": "1"}
        Path(environment["BLENDER_USER_CONFIG"]).mkdir(parents=True)
        row = {"session": number, "checks": [], "connection": "Not Run"}
        report["sessions"].append(row)
        with (control / "blender.log").open("w", encoding="utf-8") as log:
            process = subprocess.Popen([str(args.blender), "--factory-startup", "--python-exit-code", "1",
                "--python", str(ROOT / "tests/blender_upstream_host.py"), "--", str(package), str(control), str(port)],
                env=environment, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
            try:
                deadline = time.monotonic() + 90
                while not (control / "host.json").exists():
                    if process.poll() is not None:
                        raise RuntimeError(f"Official host exited {process.returncode}; see session-{number}/blender.log")
                    if time.monotonic() > deadline:
                        raise TimeoutError("Official GUI host did not become ready")
                    time.sleep(0.1)
                row["host"] = json.loads((control / "host.json").read_text(encoding="utf-8"))
                assert row["host"]["installed_source_hashes"] == report["source"]["addon_hashes"], "Installed official source was modified"
                asyncio.run(exercise(command, environment, control, report, path, row))
            finally:
                (control / "stop").touch()
                try:
                    process.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    process.terminate()
                    process.wait(timeout=10)
                row["host_exit_code"] = process.returncode
                if (control / "native-install.json").exists():
                    row["native_install"] = json.loads((control / "native-install.json").read_text(encoding="utf-8"))
                write_json(path, report)
        assert row["host_exit_code"] == 0, row["host_exit_code"]
    checks = [entry for row in report["sessions"] for entry in row["checks"]]
    assert len(checks) == 18
    report.update(execution_status="Passed", status="Failed" if any(c["status"] == "Failed" for c in checks) else "Passed",
                  reproduction={name: {"failed": sum(c["status"] == "Failed" for c in checks if c["case"].startswith(prefix)),
                                       "attempts": sum(c["case"].startswith(prefix) for c in checks)}
                                for name, prefix in (("thumbnail", "thumbnail-"), ("api_member", "bpy.types.Object.location"))})
    write_json(path, report)
    print(json.dumps({"status": report["status"], "execution_status": report["execution_status"],
                      "reproduction": report["reproduction"], "report": str(path)}), flush=True)
    return 1 if report["status"] == "Failed" else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blender", type=Path, required=True)
    parser.add_argument("--upstream-ref", required=True)
    parser.add_argument("--label", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[a-zA-Z0-9_-]+", args.label):
        raise ValueError("--label must use letters, digits, underscores or hyphens")
    run = current_work("upstream-split")
    path = LATEST / f"upstream-split-{args.label}-tests.json"
    if os.environ.get("BLENDER_MCP_UPSTREAM_WORKER") == "1":
        report = json.loads(path.read_text(encoding="utf-8"))
        raise SystemExit(worker(args, run, report, path))
    report = {"status": "Not Run", "execution_status": "Not Run", "transport": "stdio",
              "sdk_read_seconds": SDK_READ_TIMEOUT.total_seconds(), "sessions": []}
    write_json(path, report)
    try:
        python, environment = prepare(args, run, report)
        write_json(path, report)
        environment["BLENDER_MCP_UPSTREAM_WORKER"] = "1"
        result = subprocess.run([str(python), "-B", str(Path(__file__).resolve()), *sys.argv[1:]], env=environment)
        raise SystemExit(result.returncode)
    except Exception as error:
        report.update(status="Failed", error=f"{type(error).__name__}: {error}", traceback=traceback.format_exc())
        write_json(path, report)
        raise


if __name__ == "__main__":
    label = sys.argv[sys.argv.index("--label") + 1]
    run_check(f"upstream-split-{label}", main)
