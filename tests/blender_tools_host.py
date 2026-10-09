"""Serve the installed extension from a disposable, real Blender GUI scene."""

import importlib
import json
import platform
import subprocess
import sys
import time
import traceback
from pathlib import Path

import bpy
import gpu

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from check_reports import write_json
sys.path.insert(0, str(Path(__file__).parent))
from native_install_capture import capture_install


def main():
    arguments = sys.argv[sys.argv.index("--") + 1:]
    package, directory, http_port, bridge_port = arguments[:4]
    control = Path(directory)
    bpy.context.preferences.view.show_splash = False
    bpy.context.preferences.view.language = "en_US"
    bpy.context.preferences.view.use_translate_interface = False
    assert not bpy.app.background
    with capture_install(control):
        assert bpy.ops.extensions.package_install_files(
            filepath=package, repo="user_default", enable_on_install=True,
        ) == {"FINISHED"}
    name = "bl_ext.user_default.blender_mcp_integration"
    addon = importlib.import_module(name)
    original_bridge = []
    if len(arguments) > 4 and arguments[4] == "official-bridge":
        import hashlib
        root = Path(addon.__file__).parent
        provenance = json.loads((root / "provenance.json").read_text())
        source = Path(__file__).resolve().parents[1] / "submodules/blender_mcp"
        for filename in ("mcp_to_blender_server.py", "deferred_tool.py"):
            content = subprocess.check_output(["git", "-C", str(source), "show",
                f"{provenance['commit']}:addon/blender_mcp_addon/{filename}"])
            path = root / "_vendor/bridge" / filename
            path.write_bytes(content)
            original_bridge.append({"path": filename, "source_commit": provenance["commit"],
                                    "sha256": hashlib.sha256(content).hexdigest()})
    prefs = bpy.context.preferences.addons[name].preferences
    prefs.autostart = False
    prefs.http_port, prefs.bridge_port = int(http_port), int(bridge_port)

    # Positive fixtures make the summaries check actual missing and linked data.
    library = control / "library.blend"
    mesh = bpy.data.meshes.new("LinkedMesh")
    obj = bpy.data.objects.new("LinkedFixture", mesh)
    bpy.data.libraries.write(str(library), {obj})
    bpy.data.objects.remove(obj)
    bpy.data.meshes.remove(mesh)
    with bpy.data.libraries.load(str(library), link=True) as (_, target):
        target.objects = ["LinkedFixture"]
    bpy.context.scene.collection.objects.link(target.objects[0])
    image = bpy.data.images.new("MissingFixture", width=1, height=1)
    image.source = "FILE"
    image.use_fake_user = True
    image.filepath = str(control / "missing-fixture.png")
    scene = bpy.context.scene
    scene["mcp_fixture"] = "all-tools"
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 2
    scene.render.resolution_x, scene.render.resolution_y = 400, 300
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    blend_file = control / "fixture.blend"
    assert bpy.ops.wm.save_as_mainfile(filepath=str(blend_file)) == {"FINISHED"}
    diagnostic = None
    if 'diagnostic' in arguments[4:]:
        sys.path.insert(0, str(Path(__file__).parent))
        from blender_diagnostic_hooks import instrument_host
        diagnostic = instrument_host(addon, control)
    addon.start_service()
    deadline = time.monotonic() + 45
    ready = False

    def drive():
        nonlocal ready
        try:
            if (control / "stop").exists():
                addon.stop_service()
                write_json(control / "finished.json", {"status": "Passed"})
                bpy.ops.wm.quit_blender()
                return None
            if addon.SERVICE.state == "Running" and not ready:
                window = bpy.context.window_manager.windows[0]
                if 'skip-initial-redraw' not in arguments[4:]:
                    with bpy.context.temp_override(window=window):
                        bpy.ops.wm.redraw_timer(type="DRAW_WIN_SWAP", iterations=2)
                write_json(control / "service.json", {
                    "http_port": prefs.http_port, "bridge_port": prefs.bridge_port,
                    "token": addon.SERVICE.token, "pid": addon.SERVICE.process.pid,
                    "blend_file": str(blend_file), "host_binary": bpy.app.binary_path,
                })
                write_json(control / "host.json", {
                    "version": bpy.app.version_string, "binary": bpy.app.binary_path,
                    "platform": platform.system(), "background": bpy.app.background,
                    "graphics": {"renderer": gpu.platform.renderer_get(),
                                 "vendor": gpu.platform.vendor_get(), "version": gpu.platform.version_get()},
                    "extension": json.loads((Path(addon.__file__).parent / "provenance.json").read_text()),
                    "original_bridge_override": original_bridge,
                    "diagnostic_instrumentation": diagnostic,
                })
                ready = True
            if not ready and time.monotonic() > deadline:
                raise TimeoutError(f"Service start failed: {addon.LAST_ERROR}")
            return 0.05
        except Exception:
            (control / "failure.txt").write_text(traceback.format_exc(), encoding="utf-8")
            addon.stop_service()
            bpy.ops.wm.quit_blender()
            return None

    bpy.app.timers.register(drive, first_interval=1.0)


if __name__ == "__main__":
    main()
