"""Verify the installed Extension through a real MCP session and Blender process."""

import argparse
import asyncio
import ctypes
import json
import os
import site
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

from check_reports import run_check
from publication import digest
from platforms import process_options


ROOT = Path(__file__).resolve().parents[1]


def free_port():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def assert_ports_released(ports):
    for port in ports:
        with socket.socket() as probe:
            if os.name != "nt":
                probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            probe.bind(("127.0.0.1", port))


def initialize_client_runtime(package, directory):
    with zipfile.ZipFile(package) as archive:
        for name in archive.namelist():
            if name.startswith("_vendor/runtime/"):
                archive.extract(name, directory)
    runtime = Path(directory) / "_vendor/runtime"
    sys.path.insert(0, str(runtime))
    site.addsitedir(str(runtime))


def wait_file(path, process, timeout=45):
    deadline = time.monotonic() + timeout
    while not path.exists():
        if process.poll() is not None:
            raise RuntimeError(f"Blender exited with code {process.returncode}; see {path.parent / 'blender.log'}")
        if time.monotonic() >= deadline:
            raise TimeoutError(f"Timed out waiting for {path}")
        time.sleep(0.05)


async def check_session(connection):
    import httpx
    from mcp import ClientSession
    from mcp.client.streamable_http import streamable_http_client

    async with httpx.AsyncClient(headers={"Authorization": f"Bearer {connection['token']}"}, trust_env=False) as http:
        async with streamable_http_client(f"http://127.0.0.1:{connection['http_port']}/", http_client=http) as (read, write, _):
            async with ClientSession(read, write) as session:
                initialized = await session.initialize()
                tools = await session.list_tools()
                names = {tool.name for tool in tools.tools}
                assert "execute_blender_code" in names
                response = await session.call_tool("execute_blender_code", {"code": "import bpy\nresult = {'version': bpy.app.version_string, 'count': len(bpy.data.objects)}"})
                assert not response.isError, response
                structured = response.structuredContent or json.loads(response.content[0].text)
                assert structured["status"] == "ok", structured
                original_count = structured["result"]["count"]
                edited = await session.call_tool("execute_blender_code", {"code": (
                    "import bpy\n"
                    "bpy.ops.mesh.primitive_cube_add()\n"
                    "created = bpy.context.object\n"
                    "created.name = 'MCP_Integration_Test'\n"
                    "created.location.x = 2.5\n"
                    "result = {'x': created.location.x, 'count': len(bpy.data.objects)}\n"
                    "bpy.data.objects.remove(created, do_unlink=True)\n"
                )})
                assert not edited.isError, edited
                data = edited.structuredContent or json.loads(edited.content[0].text)
                assert data["status"] == "ok" and data["result"]["x"] == 2.5
                restored = await session.call_tool("execute_blender_code", {"code": "import bpy\nresult = {'count': len(bpy.data.objects)}"})
                after = restored.structuredContent or json.loads(restored.content[0].text)
                assert after["result"]["count"] == original_count
                return {"server": initialized.serverInfo.name, "tools": len(names), "blender": structured["result"]["version"]}


def request_status(connection, headers):
    request = urllib.request.Request(f"http://127.0.0.1:{connection['http_port']}/health", headers=headers)
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(request, timeout=3) as response:
            return response.status
    except urllib.error.HTTPError as error:
        return error.code


def check_bridge_auth(connection):
    with socket.create_connection(("127.0.0.1", connection["bridge_port"]), timeout=3) as bridge:
        bridge.sendall(json.dumps({"type": "execute", "code": "raise RuntimeError('Unauthenticated execution')", "strict_json": True}).encode() + b"\0")
        data = b""
        while b"\0" not in data:
            data += bridge.recv(65536)
        response = json.loads(data.split(b"\0")[0])
        assert response["status"] == "error" and "authentication" in response["message"]


def check_parent_exit(args, directory):
    directory.mkdir()
    environment = os.environ.copy()
    environment["BLENDER_USER_RESOURCES"] = str(directory / "profile")
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    kernel = None
    if os.name == "nt":
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
        kernel.OpenProcess.restype = ctypes.c_void_p
        kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
        kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    handle = None
    with (directory / "blender.log").open("w", encoding="utf-8") as log:
        parent = subprocess.Popen([
            str(args.blender), "--background", "--factory-startup", "--python-exit-code", "1", "--python",
            str(ROOT / "tests/blender_integration_host.py"), "--", str(args.package.resolve()), str(directory),
            str(free_port()), str(free_port()),
        ], env=environment, stdout=log, stderr=subprocess.STDOUT, **process_options())
        try:
            wait_file(directory / "service.json", parent)
            connection = json.loads((directory / "service.json").read_text())
            if kernel:
                handle = kernel.OpenProcess(0x00100000, False, connection["pid"])
                if not handle:
                    raise OSError(ctypes.get_last_error(), "Cannot watch the test-owned service process")
            (directory / "action.json").write_text(json.dumps({"action": "parent-exit"}))
            parent.wait(timeout=10)
            assert parent.returncode == 0
            if kernel:
                assert kernel.WaitForSingleObject(handle, 15000) == 0, "Service survived abrupt Blender exit"
            else:
                deadline = time.monotonic() + 15
                while True:
                    try:
                        os.kill(connection["pid"], 0)
                    except ProcessLookupError:
                        break
                    if time.monotonic() > deadline:
                        raise AssertionError("Service survived abrupt Blender exit")
                    time.sleep(0.1)
            assert_ports_released((connection["http_port"], connection["bridge_port"]))
            assert not list(Path(connection["log"]).parent.glob("session-*.json"))
        finally:
            if handle:
                kernel.CloseHandle(handle)
            if parent.poll() is None:
                (directory / "stop").touch()
                parent.wait(timeout=10)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blender", required=True, type=Path)
    parser.add_argument("--package", required=True, type=Path)
    args = parser.parse_args()
    package_hash = digest(args.package)
    run = ROOT / "build/tests" / f"integration-{time.time_ns()}"
    run.mkdir(parents=True)
    initialize_client_runtime(args.package, run / "client")
    http_port, bridge_port = free_port(), free_port()
    environment = os.environ.copy()
    environment["BLENDER_USER_RESOURCES"] = str(run / "profile")
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    log = (run / "blender.log").open("w", encoding="utf-8")
    process = subprocess.Popen([
        str(args.blender), "--background", "--factory-startup", "--python-exit-code", "1",
        "--python", str(ROOT / "tests/blender_integration_host.py"), "--",
        str(args.package.resolve()), str(run), str(http_port), str(bridge_port),
    ], env=environment, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
        **process_options())
    checks = {}
    try:
        wait_file(run / "service.json", process)
        connection = json.loads((run / "service.json").read_text(encoding="utf-8"))
        assert request_status(connection, {}) == 401
        assert request_status(connection, {"Authorization": "Bearer incorrect"}) == 401
        assert request_status(connection, {"Authorization": f"Bearer {connection['token']}", "Origin": "http://untrusted.invalid"}) == 403
        assert request_status(connection, {"Authorization": f"Bearer {connection['token']}", "Host": "untrusted.invalid"}) == 403
        check_bridge_auth(connection)
        checks["authentication"] = "Passed"
        details = asyncio.run(check_session(connection))
        checks["mcp-session-scene-and-reversible-operation"] = "Passed"
        for action in ("duplicate-start", "port-conflict", "crash-recovery", "disable-enable", "cleanup-error"):
            (run / "action-result.json").unlink(missing_ok=True)
            (run / "action.json").write_text(json.dumps({"action": action}), encoding="utf-8")
            wait_file(run / "action-result.json", process)
            result = json.loads((run / "action-result.json").read_text(encoding="utf-8"))
            assert result == {"action": action, "status": "Passed"}
            connection = json.loads((run / "service.json").read_text(encoding="utf-8"))
            asyncio.run(check_session(connection))
            checks[action] = "Passed"
        (run / "stop").touch()
        process.wait(timeout=15)
        assert process.returncode == 0
        assert_ports_released((http_port, bridge_port))
        checks["stop-and-port-cleanup"] = "Passed"
        check_parent_exit(args, run / "parent-exit")
        checks["abrupt-parent-exit-and-session-cleanup"] = "Passed"
        if digest(args.package) != package_hash:
            raise RuntimeError("Package changed during integration validation")
        report = {"status": "Passed", "package_sha256": package_hash, "checks": checks, "details": details, "log": str(run / "blender.log"), "gui": "Not Run"}
        (ROOT / "build/integration-tests.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2))
    finally:
        (run / "stop").touch()
        if process.poll() is None:
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.terminate()
                process.wait(timeout=10)
        log.close()


if __name__ == "__main__":
    run_check("integration", main)
