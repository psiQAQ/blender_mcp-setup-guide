"""Exercise the installed Extension with Blender's real GUI event loop and timers."""

import importlib
import json
import os
import socket
import subprocess
import sys
import time
import tomllib
import traceback
from pathlib import Path

import bpy
import gpu

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from check_reports import write_json


def main():
    bpy.context.preferences.view.show_splash = False
    package, directory, http_port, bridge_port = sys.argv[sys.argv.index("--") + 1:]
    control = Path(directory)
    assert not bpy.app.background
    assert bpy.ops.extensions.package_install_files(filepath=package, repo="user_default", enable_on_install=True) == {"FINISHED"}
    name = "bl_ext.user_default.blender_mcp_integration"
    addon = importlib.import_module(name)
    prefs = bpy.context.preferences.addons[name].preferences
    prefs.http_port, prefs.bridge_port = int(http_port), int(bridge_port)
    prefs.autostart = True
    deadline = time.monotonic() + 45
    pending = "initial"
    capture = False
    capture_ready = 0.0
    initial_report = None

    def drive():
        nonlocal addon, prefs, pending, deadline, capture, capture_ready, initial_report
        try:
            if (control / "stop").exists():
                process = addon.SERVICE.process
                assert bpy.ops.preferences.addon_disable(module=name) == {"FINISHED"}
                assert process.poll() is not None
                assert not bpy.app.timers.is_registered(addon._poll_service)
                assert not bpy.app.timers.is_registered(addon._autostart)
                assert all(not cls.is_registered for cls in addon.preferences.CLASSES)
                for port in (int(http_port), int(bridge_port)):
                    with socket.socket() as probe:
                        if os.name != "nt":
                            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                        probe.bind(("127.0.0.1", port))
                write_json(control / "finished.json", {"status": "Passed", "timers_classes_ports_cleanup": "Passed"})
                bpy.ops.wm.quit_blender()
                return None
            if pending and addon.SERVICE.state == "Running":
                assert bpy.app.timers.is_registered(addon._poll_service)
                health = addon.SERVICE.check_health()
                assert len(health["native_dependencies"]) == (6 if os.name == "nt" else 5)
                assert bpy.ops.blmcp_integration.diagnose() == {"FINISHED"}
                for client in ("CODEX", "CLAUDE", "OPENCODE"):
                    prefs.client = client
                    assert bpy.ops.blmcp_integration.copy_configuration() == {"FINISHED"}
                    text = bpy.context.window_manager.clipboard
                    assert (tomllib.loads(text) if client == "CODEX" else json.loads(text))
                if pending == "initial":
                    prefs.client = "CODEX"
                    bpy.context.preferences.active_section = "ADDONS"
                    bpy.context.window_manager.addon_search = "Blender MCP Integrated"
                    assert bpy.ops.preferences.addon_expand(module=name) == {"FINISHED"}
                    window = bpy.context.window_manager.windows[0]
                    area = max(window.screen.areas, key=lambda item: item.width * item.height)
                    area.type = "PREFERENCES"
                    area.tag_redraw()
                    capture = True
                    capture_ready = time.monotonic() + 0.5
                write_json(control / "service.json", {
                    "http_port": prefs.http_port, "bridge_port": prefs.bridge_port,
                    "token": addon.SERVICE.token, "pid": addon.SERVICE.process.pid,
                })
                graphics = {"renderer": gpu.platform.renderer_get(), "vendor": gpu.platform.vendor_get(), "version": gpu.platform.version_get()}
                if os.environ.get("GALLIUM_DRIVER") == "llvmpipe":
                    assert "llvmpipe" in graphics["renderer"].lower(), graphics
                report = {"status": "Passed", "graphics": graphics}
                if pending == "initial":
                    initial_report = report
                else:
                    write_json(control / f"{pending}.json", report)
                pending = ""
            elif capture and time.monotonic() >= capture_ready:
                window = bpy.context.window_manager.windows[0]
                with bpy.context.temp_override(window=window):
                    assert bpy.ops.wm.redraw_timer(type="DRAW_WIN_SWAP", iterations=2) == {"FINISHED"}
                    if sys.platform == "linux":
                        subprocess.run(["import", "-window", "root", str(control / "preferences.png")], check=True, timeout=15)
                    else:
                        assert bpy.ops.screen.screenshot(filepath=str(control / "preferences.png")) == {"FINISHED"}
                image = bpy.data.images.load(str(control / "preferences.png"), check_existing=False)
                try:
                    samples = image.pixels[:][::128]
                    assert max(samples) - min(samples) > 0.1, "GUI screenshot contains no visible interface"
                finally:
                    bpy.data.images.remove(image)
                write_json(control / "initial.json", initial_report)
                capture = False
            if pending and time.monotonic() > deadline:
                raise TimeoutError(f"GUI automatic service start failed: {addon.LAST_ERROR}")
            command = control / "restart"
            if command.exists():
                command.unlink()
                previous = addon.SERVICE.process
                assert bpy.ops.preferences.addon_disable(module=name) == {"FINISHED"}
                assert previous.poll() is not None
                assert bpy.ops.preferences.addon_enable(module=name) == {"FINISHED"}
                addon = importlib.import_module(name)
                prefs = bpy.context.preferences.addons[name].preferences
                prefs.http_port, prefs.bridge_port = int(http_port), int(bridge_port)
                prefs.autostart = True
                pending, deadline = "restarted", time.monotonic() + 45
            return 0.05
        except Exception:
            (control / "failure.txt").write_text(traceback.format_exc(), encoding="utf-8")
            addon.stop_service()
            bpy.ops.wm.quit_blender()
            return None

    bpy.app.timers.register(drive, first_interval=0.1)


if __name__ == "__main__":
    main()
