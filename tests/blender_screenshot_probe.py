"""Capture startup and two-window screenshot behavior in an isolated Blender GUI."""

from array import array
import argparse
from collections import Counter
import json
from pathlib import Path
import sys
import time
import traceback

import bpy
import gpu


def window_details(window):
    if window is None:
        return None
    return {"pointer": window.as_pointer(), "width": window.width, "height": window.height,
            "screen": window.screen.name, "screen_pointer": window.screen.as_pointer()}


def context_details():
    context = bpy.context
    return {"window": window_details(context.window),
            "area": None if context.area is None else {
                "pointer": context.area.as_pointer(), "type": context.area.type},
            "region": None if context.region is None else {
                "pointer": context.region.as_pointer(), "type": context.region.type},
            "windows": [window_details(window) for window in context.window_manager.windows]}


def graphics_details():
    try:
        backend_get = getattr(gpu.platform, "backend_type_get", None)
        return {"renderer": gpu.platform.renderer_get(), "vendor": gpu.platform.vendor_get(),
                "version": gpu.platform.version_get(), "backend_type_supported": backend_get is not None,
                "backend_type": backend_get() if backend_get is not None else None}
    except Exception as error:
        return {"error": f"{type(error).__name__}: {error}"}


def image_details(path):
    image = bpy.data.images.load(str(path), check_existing=False)
    try:
        pixels = array("f", [0.0]) * len(image.pixels)
        image.pixels.foreach_get(pixels)
        width, height = image.size
        if width <= 0 or height <= 0 or len(pixels) != width * height * 4:
            raise RuntimeError(f"Unexpected image dimensions or pixel count: {width} x {height}, {len(pixels)}")
        channels = [pixels[index::4] for index in range(3)]
        minimum = min(min(channel) for channel in channels)
        maximum = max(max(channel) for channel in channels)
        nonzero = sum(len(channel) - channel.count(0.0) for channel in channels)
        # A few bright pixels in an otherwise empty framebuffer are not a valid UI.
        dominant = sum(max(Counter(channel).values()) for channel in channels)
        variation_fraction = 1.0 - dominant / (width * height * 3)
        return {"width": width, "height": height, "rgb_minimum": minimum, "rgb_maximum": maximum,
                "rgb_nonzero": nonzero, "rgb_channel_count": width * height * 3,
                "black_image": nonzero == 0, "rgb_range": maximum - minimum,
                "non_dominant_channel_fraction": variation_fraction,
                "content_valid": maximum - minimum > 0.1 and variation_fraction > 0.01}
    finally:
        bpy.data.images.remove(image)


class OwnedMainWindow:
    """Control one visible top-level window belonging to this Blender process."""

    def __init__(self):
        import ctypes
        from ctypes import wintypes
        import os

        if os.name != "nt":
            raise RuntimeError("--early-minimized requires Windows")
        self.ctypes, self.wintypes = ctypes, wintypes
        self.pid = os.getpid()
        self.api = ctypes.WinDLL("user32", use_last_error=True)
        self.api.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
        self.api.IsWindowVisible.argtypes = [wintypes.HWND]
        self.api.IsIconic.argtypes = [wintypes.HWND]
        self.api.GetWindowTextLengthW.argtypes = [wintypes.HWND]
        self.api.GetWindow.argtypes = [wintypes.HWND, wintypes.UINT]
        self.api.GetWindow.restype = wintypes.HWND
        self.api.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
        callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        candidates = []

        def visit(hwnd, unused):
            owner = wintypes.DWORD()
            self.api.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
            if (owner.value == self.pid and self.api.IsWindowVisible(hwnd) and
                    self.api.GetWindowTextLengthW(hwnd) and not self.api.GetWindow(hwnd, 4)):
                candidates.append(hwnd)
            return True

        self.api.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
        if not self.api.EnumWindows(callback_type(visit), 0):
            raise ctypes.WinError(ctypes.get_last_error())
        if len(candidates) != 1:
            raise RuntimeError(f"Expected one visible owned main HWND, got {len(candidates)} for PID {self.pid}")
        self.hwnd = candidates[0]

    def state(self):
        owner = self.wintypes.DWORD()
        self.api.GetWindowThreadProcessId(self.hwnd, self.ctypes.byref(owner))
        if owner.value != self.pid:
            raise RuntimeError("Diagnostic HWND no longer belongs to this process")
        return {"hwnd": int(self.hwnd), "pid": self.pid,
                "visible": bool(self.api.IsWindowVisible(self.hwnd)),
                "minimized": bool(self.api.IsIconic(self.hwnd))}

    def show(self, command):
        self.state()
        self.api.ShowWindow(self.hwnd, command)
        return self.state()


def create_scene():
    scene = bpy.context.scene
    for obj in list(scene.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    mesh = bpy.data.meshes.new("ScreenshotProbeCube")
    mesh.from_pydata(
        [(-1, -1, -1), (-1, -1, 1), (-1, 1, -1), (-1, 1, 1),
         (1, -1, -1), (1, -1, 1), (1, 1, -1), (1, 1, 1)], [],
        [(0, 4, 6, 2), (1, 3, 7, 5), (0, 1, 5, 4),
         (2, 6, 7, 3), (0, 2, 3, 1), (4, 5, 7, 6)],
    )
    mesh.update()
    obj = bpy.data.objects.new("ScreenshotProbeCube", mesh)
    scene.collection.objects.link(obj)
    material = bpy.data.materials.new("ScreenshotProbeBlue")
    material.diffuse_color = (0.1, 0.4, 0.8, 1.0)
    mesh.materials.append(material)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == "VIEW_3D":
                space = area.spaces.active
                space.shading.type = "SOLID"
                space.shading.color_type = "MATERIAL"
                space.region_3d.view_location = (0.0, 0.0, 0.0)
                space.region_3d.view_distance = 8.0


def main():
    arguments = sys.argv[sys.argv.index("--") + 1:]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--early-minimized", action="store_true")
    args = parser.parse_args(arguments)
    control = args.output_dir.resolve()
    control.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    report = {"status": "Not Run", "version": bpy.app.version_string,
              "binary": bpy.app.binary_path, "background": bpy.app.background,
              "graphics": graphics_details(), "cases": [], "redraws": [],
              "early_minimized": args.early_minimized,
              "frame_evidence": "Execution phase and explicit redraw calls only; native frame counters are not instrumented. "
                                "screen.screenshot itself calls WM_redraw_windows before reading pixels."}
    native_window = None

    def write_report():
        (control / "host-result.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def fail():
        report.update(status="Failed", error=traceback.format_exc())
        (control / "failure.txt").write_text(report["error"], encoding="utf-8")
        write_report()
        bpy.ops.wm.quit_blender()

    def capture(window, phase, event_loop_pass):
        requires_minimized = args.early_minimized and phase in {
            "startup-python-w0", "early-minimized-redraw-w0", "early-minimized-after-event-loop-w0"}
        path = control / f"{len(report['cases']) + 1:02d}-{phase}.png"
        row = {"phase": phase, "event_loop_pass": event_loop_pass,
               "sequence": len(report["cases"]) + 1, "status": "Not Run",
               "seconds_since_start": round(time.monotonic() - started, 6), "path": str(path),
               "target_window": window_details(window), "context_before_override": context_details()}
        report["cases"].append(row)
        with bpy.context.temp_override(window=window):
            row["context_at_call"] = context_details()
            row["graphics_at_call"] = graphics_details()
            if native_window is not None:
                row["owned_main_window_state_at_call"] = native_window.state()
                if requires_minimized and not row["owned_main_window_state_at_call"]["minimized"]:
                    raise RuntimeError(f"{phase} did not run with the owned main window minimized")
            row["screenshot_return"] = sorted(bpy.ops.screen.screenshot(filepath=str(path)))
            row["context_after_call"] = context_details()
            if native_window is not None:
                row["owned_main_window_state_after_call"] = native_window.state()
        row["image"] = image_details(path)
        row["black_image"] = row["image"]["black_image"]
        row["status"] = "Passed" if row["screenshot_return"] == ["FINISHED"] and row["image"]["content_valid"] else "Failed"
        row["finished_seconds_since_start"] = round(time.monotonic() - started, 6)
        if requires_minimized and not row["owned_main_window_state_after_call"]["minimized"]:
            raise RuntimeError(f"{phase} did not leave the owned main window minimized")
        print(f"[SCREENSHOT-PROBE] {phase}: {row['status']}, black={row['black_image']}", flush=True)

    def after_event_loop():
        try:
            for index, window in enumerate(windows):
                capture(window, f"after-event-loop-w{index}", 3 if args.early_minimized else 2)
            report["black_image_count"] = sum(case["black_image"] for case in report["cases"])
            report["invalid_image_count"] = sum(not case["image"]["content_valid"] for case in report["cases"])
            report["status"] = "Failed" if any(case["status"] == "Failed" for case in report["cases"]) else "Passed"
            write_report()
            bpy.ops.wm.quit_blender()
        except Exception:
            fail()
        return None

    def first_timer():
        try:
            event_loop_pass = 2 if args.early_minimized else 1
            capture(windows[0], "first-timer-w0", event_loop_pass)
            with bpy.context.temp_override(window=windows[0]):
                report["window_new_return"] = sorted(bpy.ops.wm.window_new())
            candidates = list(bpy.context.window_manager.windows)
            if len(candidates) != 2:
                raise RuntimeError(f"Expected exactly two owned windows, got {len(candidates)}")
            windows.append(next(window for window in candidates if window != windows[0]))
            for step, index in enumerate((0, 1, 0, 1), 1):
                capture(windows[index], f"alternating-{step}-w{index}", event_loop_pass)
            for index, window in enumerate(windows):
                with bpy.context.temp_override(window=window):
                    result = bpy.ops.wm.redraw_timer(type="DRAW_WIN_SWAP", iterations=2)
                    report["redraws"].append({"window": window_details(window), "return": sorted(result),
                                              "seconds_since_start": round(time.monotonic() - started, 6)})
                capture(window, f"after-explicit-redraw-w{index}", event_loop_pass)
            bpy.app.timers.register(after_event_loop, first_interval=0.5)
        except Exception:
            fail()
        return None

    def minimized_after_event_loop():
        try:
            capture(windows[0], "early-minimized-after-event-loop-w0", 1)
            report["restored_native_window"] = native_window.show(9)
            if report["restored_native_window"]["minimized"]:
                raise RuntimeError("ShowWindow(SW_RESTORE) did not restore the owned main window")
            capture(windows[0], "early-restored-no-explicit-redraw-w0", 1)
            with bpy.context.temp_override(window=windows[0]):
                result = bpy.ops.wm.redraw_timer(type="DRAW_WIN_SWAP", iterations=2)
                report["redraws"].append({"phase": "early-minimized-recovery", "window": window_details(windows[0]),
                                          "return": sorted(result), "seconds_since_start": round(time.monotonic() - started, 6)})
            capture(windows[0], "early-minimized-recovery-w0", 1)
            bpy.app.timers.register(first_timer, first_interval=0.1)
        except Exception:
            fail()
        return None

    try:
        if bpy.app.background:
            raise RuntimeError("Screenshot probe requires a real GUI process")
        windows = list(bpy.context.window_manager.windows)
        if len(windows) != 1:
            raise RuntimeError(f"Expected one initial owned window, got {len(windows)}")
        bpy.context.preferences.view.show_splash = False
        if args.early_minimized:
            native_window = OwnedMainWindow()
            report["initial_native_window"] = native_window.state()
            report["minimized_native_window"] = native_window.show(6)
            if not report["minimized_native_window"]["minimized"]:
                raise RuntimeError("ShowWindow(SW_MINIMIZE) did not minimize the owned main window")
        create_scene()
        capture(windows[0], "startup-python-w0", 0)
        if args.early_minimized:
            with bpy.context.temp_override(window=windows[0]):
                result = bpy.ops.wm.redraw_timer(type="DRAW_WIN_SWAP", iterations=2)
                report["redraws"].append({"phase": "early-minimized-redraw", "window": window_details(windows[0]),
                                          "return": sorted(result), "seconds_since_start": round(time.monotonic() - started, 6)})
            capture(windows[0], "early-minimized-redraw-w0", 0)
            bpy.app.timers.register(minimized_after_event_loop, first_interval=0.5)
        else:
            bpy.app.timers.register(first_timer, first_interval=0.1)
    except Exception:
        fail()


if __name__ == "__main__":
    main()
