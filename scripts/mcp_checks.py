"""Shared client deadlines and semantic checks for the native MCP runners."""

import json
from datetime import timedelta
from pathlib import Path

HTTP_READ_SECONDS = 60
SDK_READ_TIMEOUT = timedelta(seconds=90)


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


async def check_cli_tools(session, connection, host):
    """Exercise all six tools against a saved file with real linked/missing data."""
    blend_file = connection["blend_file"]
    code = (
        "import bpy\nresult = {'version': bpy.app.version_string, "
        "'binary': bpy.app.binary_path, 'background': bpy.app.background, "
        "'fixture': bpy.context.scene['mcp_fixture']}"
    )
    results = {}
    name = "execute_blender_code_for_cli"
    value = unwrap(await session.call_tool(name, {"blend_file": blend_file, "code": code}))
    assert value["background"] and value["fixture"] == "all-tools", value
    assert value["version"] == host["version"], value
    assert Path(value["binary"]).resolve() == Path(host["binary"]).resolve(), value
    results[name] = {"status": "Passed", "response": value}
    for suffix in ("datablocks", "missing_files", "of_linked_libraries", "path_info", "usage_guess"):
        name = f"get_blendfile_summary_{suffix}_for_cli"
        value = unwrap(await session.call_tool(name, {"blend_file": blend_file}))
        if suffix == "datablocks":
            assert value["datablock_counts"]["objects"] == 4, value
        elif suffix == "missing_files":
            assert "missing-fixture.png" in json.dumps(value["missing_files"]), value
        elif suffix == "of_linked_libraries":
            assert value["total_library_count"] == 1 and value["direct_libraries"], value
        elif suffix == "path_info":
            assert value["is_saved"] and Path(value["filepath"]).resolve() == Path(blend_file).resolve(), value
        elif suffix == "usage_guess":
            assert "Modeling" in value["usage_guesses"] and "Animation" in value["usage_guesses"], value
        results[name] = {"status": "Passed", "response": value}
    return results
