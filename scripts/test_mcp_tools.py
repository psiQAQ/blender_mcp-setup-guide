"""Check every official MCP tool against a real isolated Blender GUI."""

import argparse
import asyncio
import base64
import json
import os
import shutil
import subprocess
import time
import traceback
from datetime import timedelta
from pathlib import Path

from build_cache import LATEST, current_work
from check_reports import run_check, write_json
from mcp_checks import HTTP_READ_SECONDS, SDK_READ_TIMEOUT
from platforms import process_options
from publication import digest
from test_integration import ROOT, free_port, initialize_client_runtime
from test_gui import wait_result


def unwrap(response):
    assert not response.isError, [getattr(item, "text", item.type) for item in response.content]
    value = response.structuredContent
    if value is None:
        value = json.loads(next(item.text for item in response.content if item.type == "text"))
    while isinstance(value, dict) and "status" in value:
        assert value["status"] != "error", value
        if "result" not in value:
            break
        value = value["result"]
    return value


async def connect(connection, operation):
    import httpx
    from mcp import ClientSession
    from mcp.client.streamable_http import streamable_http_client
    async with httpx.AsyncClient(headers={"Authorization": f"Bearer {connection['token']}"},
                                 trust_env=False, timeout=HTTP_READ_SECONDS) as http:
        async with streamable_http_client(f"http://127.0.0.1:{connection['http_port']}/", http_client=http) as (read, write, _):
            async with ClientSession(read, write, read_timeout_seconds=SDK_READ_TIMEOUT) as session:
                await session.initialize()
                return await operation(session)


def cases(blend):
    summaries = ["datablocks", "missing_files", "of_linked_libraries", "path_info", "usage_guess"]
    result = [(f"get_blendfile_summary_{name}", {}) for name in summaries]
    result += [(f"get_blendfile_summary_{name}_for_cli", {"blend_file": blend}) for name in summaries]
    result += [
        ("execute_blender_code", {"code": "import bpy\nm = bpy.data.meshes.new('MCPProbe')\no = bpy.data.objects.new('MCPProbe', m)\nbpy.context.scene.collection.objects.link(o)\no.location.x = 2.5\nresult = {'x':o.location.x, 'during':len(bpy.data.objects)}\nbpy.data.objects.remove(o, do_unlink=True)\nbpy.data.meshes.remove(m)\nresult['after'] = len(bpy.data.objects)"}),
        ("execute_blender_code_for_cli", {"blend_file": blend, "code": "import bpy, os, platform\nresult = {'version':bpy.app.version_string,'binary':bpy.app.binary_path,'background':bpy.app.background,'fixture':bpy.context.scene['mcp_fixture'],'platform':platform.system(),'pid':os.getpid()}"}),
        ("get_objects_summary", {}), ("get_object_detail_summary", {"name": "Cube"}),
        ("get_python_api_docs", {"identifier": "bpy.ops.mesh.primitive_cube_add"}),
        ("search_api_docs", {"query": "primitive_cube_add", "max_results": 3}),
        ("search_manual_docs", {"query": "render", "max_results": 3}),
        ("get_screenshot_of_window_as_json", {}),
        ("jump_to_tab_by_name", {"name": "Modeling"}),
        ("jump_to_tab_by_space_type", {"space_type": "VIEW_3D"}),
        ("jump_to_view3d_object_by_name", {"name": "Cube"}),
        ("jump_to_view3d_object_data_by_name", {"name": "Cube"}),
        ("get_screenshot_of_area_as_image", {"area_ui_type": "VIEW_3D"}),
        ("get_screenshot_of_window_as_image", {}),
        ("render_thumbnail_to_path", {"output_path": "tool-thumbnail.png"}),
        ("render_viewport_to_path", {"output_path": "tool-render.png"}),
    ]
    return result


async def image_details(session, path):
    response = await session.call_tool("execute_blender_code", {"code": (
        "import bpy\n"
        f"i = bpy.data.images.load({str(path)!r}, check_existing=False)\n"
        "try:\n"
        "    p = list(i.pixels)\n"
        "    rgb = [v for j,v in enumerate(p) if j % 4 != 3]\n"
        "    result = {'width':i.size[0],'height':i.size[1],'minimum':min(rgb),'maximum':max(rgb)}\n"
        "finally:\n"
        "    bpy.data.images.remove(i)\n"
    )})
    value = unwrap(response)
    assert value["width"] > 1 and value["height"] > 1, value
    assert value["maximum"] - value["minimum"] > 0.1, f"Image has no visible content: {value}"
    return value


async def verify(session, name, response, run, host):
    if name in {"get_screenshot_of_area_as_image", "get_screenshot_of_window_as_image"}:
        assert not response.isError, response
        image = next(item for item in response.content if item.type == "image")
        path = run / f"{name}.png"
        path.write_bytes(base64.b64decode(image.data, validate=True))
        details = await image_details(session, path)
        return {"path": str(path), **details}
    data = unwrap(response)
    if "datablocks" in name:
        assert data["datablock_counts"]["objects"] == 4, data
    elif "missing_files" in name:
        assert "missing-fixture.png" in json.dumps(data["missing_files"]), data
    elif "linked_libraries" in name:
        assert data["total_library_count"] == 1 and data["direct_libraries"], data
    elif "path_info" in name:
        assert data["is_saved"] and Path(data["filepath"]).name == "fixture.blend", data
    elif "usage_guess" in name:
        assert "Modeling" in data["usage_guesses"] and "Animation" in data["usage_guesses"], data
    elif name == "execute_blender_code":
        assert data == {"x": 2.5, "during": 5, "after": 4}, data
    elif name == "execute_blender_code_for_cli":
        assert data["background"] and data["fixture"] == "all-tools", data
        assert data["version"] == host["version"] and Path(data["binary"]) == Path(host["binary"]), data
    elif name == "get_objects_summary":
        assert "LinkedFixture" in json.dumps(data) and "Cube" in json.dumps(data), data
    elif name == "get_object_detail_summary":
        assert "Cube" in json.dumps(data) and "MESH" in json.dumps(data), data
    elif name == "get_python_api_docs":
        assert data["found"] and "primitive_cube_add" in json.dumps(data), data
    elif name.startswith("search_"):
        assert data["hits"], data
    elif name == "get_screenshot_of_window_as_json":
        assert data["areas"] and data["scene"] == "Scene", data
    elif name.startswith("jump_to_"):
        state = unwrap(await session.call_tool("execute_blender_code", {"code": (
            "import bpy\nresult = {'workspace':bpy.context.window.workspace.name,"
            "'active':bpy.context.view_layer.objects.active.name,"
            "'spaces':[a.type for a in bpy.context.window.screen.areas]}"
        )}))
        if name == "jump_to_tab_by_name":
            assert state["workspace"] == "Modeling", state
        elif "tab_by_space" in name:
            assert "VIEW_3D" in state["spaces"], state
        else:
            assert state["active"] == "Cube" and "VIEW_3D" in state["spaces"], state
        return {"response": data, "actual_state": state}
    elif name.startswith("render_"):
        path = Path(data["filepath"])
        assert path.is_file(), data
        copy = run / path.name
        shutil.copyfile(path, copy)
        details = await image_details(session, copy)
        if "thumbnail" in name:
            assert max(details["width"], details["height"]) <= 320, details
        else:
            assert (details["width"], details["height"]) == (400, 300), details
        return {"response": data, "path": str(copy), **details}
    return data


async def audit(connection, run, report, report_path):
    async def inventory(session):
        return [tool.model_dump(mode="json") for tool in (await session.list_tools()).tools]
    report["inventory"] = await connect(connection, inventory)
    names = {tool["name"] for tool in report["inventory"]}
    plan = cases(connection["blend_file"])
    assert {name for name, _ in plan} == names, names
    for name, arguments in plan:
        started = time.monotonic()
        item = {"tool": name, "arguments": arguments, "status": "Not Run"}
        report["tests"].append(item)
        write_json(report_path, report)
        async def check(session):
            response = await session.call_tool(name, arguments)
            # Store text/structured evidence before validation, including failures.
            if not any(block.type == "image" for block in response.content):
                item["response"] = response.model_dump(mode="json")
            return await verify(session, name, response, run, report["host"])
        try:
            item["evidence"] = await connect(connection, check)
            item["status"] = "Passed"
        except Exception as error:
            item.update(status="Failed", error=f"{type(error).__name__}: {error}", traceback=traceback.format_exc())
        item["seconds"] = round(time.monotonic() - started, 3)
        write_json(report_path, report)
        print(f"{name}: {item['status']} ({item['seconds']}s)", flush=True)
    report["probes"] = []
    for identifier in ("bpy.types.Object.location", "bpy.types.Object.Object.location"):
        item = {"name": "API member lookup", "identifier": identifier}
        async def docs(session):
            return unwrap(await session.call_tool("get_python_api_docs", {"identifier": identifier}))
        try:
            item["response"] = await connect(connection, docs)
            item["status"] = "Passed" if item["response"].get("found") else "Failed"
        except Exception as error:
            item.update(status="Failed", traceback=traceback.format_exc())
        report["probes"].append(item)
        write_json(report_path, report)
    item = {"name": "persistent SDK session", "status": "Not Run", "calls": [],
            "validation": "33 consecutive responses in one SDK session; thumbnail dimensions checked separately"}
    report["probes"].append(item)
    async def persistent(session):
        for number in range(30):
            data = unwrap(await session.call_tool("execute_blender_code", {"code": f"result = {{'sequence':{number}}}"}))
            assert data == {"sequence": number}, data
            item["calls"].append({"tool": "execute_blender_code", "sequence": number, "status": "Passed"})
        for name, arguments in [("search_api_docs", {"query": "primitive_cube_add", "max_results": 3}),
                                ("search_manual_docs", {"query": "render", "max_results": 3}),
                                ("render_thumbnail_to_path", {"output_path": "persistent-thumbnail.png"})]:
            response = await session.call_tool(name, arguments)
            data = unwrap(response)
            item["calls"].append({"tool": name, "status": "Passed", "response": data})
        return len(item["calls"])
    try:
        item["completed"] = await connect(connection, persistent)
        item["status"] = "Passed"
    except Exception:
        item.update(status="Failed", traceback=traceback.format_exc())
    write_json(report_path, report)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blender", type=Path, required=True)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--official-bridge", action="store_true", help="Compare unmodified pinned bridge in the disposable profile")
    args = parser.parse_args()
    run = current_work("mcp-tools")
    report_path = LATEST / f"mcp-tools-{args.label}-tests.json"
    report = {"status": "Not Run", "package_sha256": digest(args.package), "tests": [],
              "human_gui_acceptance": "Not Run", "mode": "isolated GUI and real HTTP MCP SDK"}
    write_json(report_path, report)
    environment = {**os.environ, "BLENDER_USER_RESOURCES": str(run / "profile"),
                   "PYTHONDONTWRITEBYTECODE": "1"}
    with (run / "blender.log").open("w", encoding="utf-8") as log:
        process = subprocess.Popen([
            str(args.blender), "--factory-startup", "--python-exit-code", "1", "--python",
            str(ROOT / "tests/blender_tools_host.py"), "--", str(args.package.resolve()), str(run),
            str(free_port()), str(free_port()),
            *( ["official-bridge"] if args.official_bridge else [] ),
        ], env=environment, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
            **process_options(gui=True))
        try:
            wait_result(run / "service.json", run, process)
            connection = json.loads((run / "service.json").read_text())
            report["host"] = json.loads((run / "host.json").read_text())
            # Initialize the private client only after the native install has finished.
            initialize_client_runtime(args.package, run / "client")
            asyncio.run(audit(connection, run, report, report_path))
            outcomes = [*report["tests"], *report.get("probes", [])]
            report["status"] = "Failed" if any(row["status"] != "Passed" for row in outcomes) else "Passed"
        except Exception as error:
            report.update(status="Failed", error=f"{type(error).__name__}: {error}")
        finally:
            if (run / "native-install.json").exists():
                report["native_install"] = json.loads((run / "native-install.json").read_text())
            (run / "stop").touch()
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.terminate()
                process.wait(timeout=10)
            report["host_exit_code"] = process.returncode
            if process.returncode:
                report["status"] = "Failed"
            write_json(report_path, report)
    print(json.dumps({"status": report["status"], "tested": len(report["tests"]), "report": str(report_path)}))
    if report["status"] == "Failed":
        raise SystemExit(1)


if __name__ == "__main__":
    import sys
    label = sys.argv[sys.argv.index("--label") + 1]
    run_check(f"mcp-tools-{label}", main)
