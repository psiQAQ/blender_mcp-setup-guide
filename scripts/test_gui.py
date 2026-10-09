"""Verify automatic start, real GUI timers, copied settings and GUI cleanup."""

import argparse
import asyncio
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from platforms import process_options

from build_cache import LATEST, current_work

from check_reports import run_check
from publication import digest

from test_integration import ROOT, check_session, free_port, initialize_client_runtime


def wait_result(path, run, process, timeout=90):
    deadline = time.monotonic() + timeout
    while not path.exists():
        if (run / "failure.txt").exists():
            raise RuntimeError((run / "failure.txt").read_text())
        if process.poll() is not None:
            raise RuntimeError(f"GUI Blender exited with code {process.returncode}; see {run / 'blender.log'}")
        if time.monotonic() > deadline:
            raise TimeoutError(f"Timed out waiting for GUI result {path}")
        time.sleep(0.05)


def start_desktop(run, environment):
    if sys.platform != "linux":
        return None
    if not environment.get("DISPLAY"):
        raise RuntimeError("Linux GUI validation requires an X11 display")
    with (run / "desktop.log").open("w", encoding="utf-8") as log:
        desktop = subprocess.Popen(["openbox", "--sm-disable"], env=environment, stdout=log, stderr=subprocess.STDOUT)
    try:
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if desktop.poll() is not None:
                raise RuntimeError(f"X11 window manager exited; see {run / 'desktop.log'}")
            result = subprocess.run(["xprop", "-root", "_NET_SUPPORTING_WM_CHECK"], env=environment, capture_output=True, text=True, check=True, timeout=5)
            if "window id" in result.stdout:
                return desktop
            time.sleep(0.1)
        raise TimeoutError("X11 window manager did not become ready")
    except BaseException:
        desktop.terminate()
        desktop.wait(timeout=10)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blender", required=True, type=Path)
    parser.add_argument("--package", required=True, type=Path)
    args = parser.parse_args()
    package_hash = digest(args.package)
    run = current_work("gui")
    initialize_client_runtime(args.package, run / "client")
    environment = os.environ.copy()
    environment["BLENDER_USER_RESOURCES"] = str(run / "profile")
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    log = (run / "blender.log").open("w", encoding="utf-8")
    graphics = ["--gpu-backend", "opengl"] if environment.get("GALLIUM_DRIVER") == "llvmpipe" else []
    desktop = start_desktop(run, environment)
    process = None
    try:
        process = subprocess.Popen([
            str(args.blender), "--factory-startup", "--debug-gpu", *graphics, "--python-exit-code", "1", "--python",
            str(ROOT / "tests/blender_gui_host.py"), "--", str(args.package.resolve()), str(run),
            str(free_port()), str(free_port()),
        ], env=environment, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, **process_options(gui=True))
        wait_result(run / "initial.json", run, process)
        connection = json.loads((run / "service.json").read_text())
        details = asyncio.run(check_session(connection))
        (run / "restart").touch()
        wait_result(run / "restarted.json", run, process)
        connection = json.loads((run / "service.json").read_text())
        asyncio.run(check_session(connection))
        (run / "stop").touch()
        wait_result(run / "finished.json", run, process)
        process.wait(timeout=15)
        assert process.returncode == 0
        if digest(args.package) != package_hash:
            raise RuntimeError("Package changed during GUI validation")
        report = {"status": "Passed", "package_sha256": package_hash, "mode": "GUI event loop", "automatic_start_and_main_thread_timers": "Passed",
                  "native_dependencies": 6 if os.name == "nt" else 5, "copy_three_client_configurations": "Passed", "health_diagnostic": "Passed",
                  "disable_enable_restart": "Passed", "timers_classes_ports_cleanup": "Passed", "details": details,
                  "human_gui_acceptance": "Not Run", "log": str(run / "blender.log")}
        report["preferences_screenshot"] = str(run / "preferences.png")
        report["graphics"] = json.loads((run / "initial.json").read_text())["graphics"]
        report["screenshot_method"] = "X11 desktop" if sys.platform == "linux" else "Blender window"
        (LATEST / "gui-tests.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2))
    finally:
        (run / "stop").touch()
        if process is not None and process.poll() is None:
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.terminate()
                process.wait(timeout=10)
        if desktop is not None:
            desktop.terminate()
            desktop.wait(timeout=10)
        log.close()


if __name__ == "__main__":
    run_check("gui", main)
