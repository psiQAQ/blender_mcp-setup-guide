"""Run the unmodified official MCP Extension in an isolated GUI process."""

import hashlib
import importlib
import json
import platform
import sys
import traceback
from pathlib import Path

import bpy
import gpu

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
sys.path.insert(0, str(Path(__file__).parent))
from check_reports import write_json
from native_install_capture import capture_install


def main():
    package, directory, bridge_port = sys.argv[sys.argv.index("--") + 1:]
    control = Path(directory)
    assert not bpy.app.background
    bpy.context.preferences.view.show_splash = False
    bpy.context.preferences.system.use_online_access = True
    with capture_install(control):
        assert bpy.ops.extensions.package_install_files(
            filepath=package, repo="user_default", enable_on_install=True,
        ) == {"FINISHED"}
    name = "bl_ext.user_default.mcp"
    addon = importlib.import_module(name)
    root = Path(addon.__file__).parent
    assert not (root / "_vendor").exists()
    prefs = bpy.context.preferences.addons[name].preferences
    prefs.use_autostart = False
    prefs.host, prefs.port = "127.0.0.1", int(bridge_port)
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 2
    scene.render.resolution_x, scene.render.resolution_y = 400, 300
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    bpy.ops.wm.save_as_mainfile(filepath=str(control / "fixture.blend"))
    assert bpy.ops.blmcp.server_start() == {"FINISHED"}
    write_json(control / "host.json", {
        "version": bpy.app.version_string, "binary": bpy.app.binary_path,
        "python": sys.version, "platform": platform.system(), "background": bpy.app.background,
        "graphics": {"renderer": gpu.platform.renderer_get(), "vendor": gpu.platform.vendor_get(),
                     "version": gpu.platform.version_get()},
        "extension_module": name,
        "installed_source_hashes": {
            str(path.relative_to(root)).replace("\\", "/"): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(root.rglob("*")) if path.is_file() and path.suffix in {".py", ".toml"}
        },
    })

    def drive():
        try:
            if (control / "stop").exists():
                assert bpy.ops.blmcp.server_stop() == {"FINISHED"}
                bpy.ops.wm.quit_blender()
                return None
            return 0.05
        except Exception:
            (control / "failure.txt").write_text(traceback.format_exc(), encoding="utf-8")
            bpy.ops.wm.quit_blender()
            return None

    bpy.app.timers.register(drive, first_interval=0.5)


if __name__ == "__main__":
    main()
