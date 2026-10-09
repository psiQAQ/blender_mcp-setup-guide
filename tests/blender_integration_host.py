"""Install the final ZIP into an isolated Blender and serve its real bridge."""

import importlib
import json
import os
import socket
import sys
import time
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from check_reports import write_json
sys.path.insert(0, str(Path(__file__).parent))
from native_install_capture import capture_install


def main():
    arguments = sys.argv[sys.argv.index("--") + 1:]
    package, control, http_port, bridge_port = arguments[:4]
    control = Path(control)
    control.mkdir(parents=True, exist_ok=True)
    with capture_install(control):
        install(arguments, package)
    repo = next((item for item in bpy.context.preferences.extensions.repos if item.module == 'integration_test'), None) if len(arguments) == 5 else None
    repo_index = list(bpy.context.preferences.extensions.repos).index(repo) if repo else -1
    module_name = f"bl_ext.{repo.module if repo else 'user_default'}.blender_mcp_integration"
    addon = importlib.import_module(module_name)
    prefs = bpy.context.preferences.addons[module_name].preferences
    prefs.autostart = False
    prefs.http_port = int(http_port)
    prefs.bridge_port = int(bridge_port)
    make_cli_fixture(control)
    blend_file = control / "cli-test.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_file))
    addon.start_service()

    def publish():
        write_json(control / "service.json", {
            "http_port": prefs.http_port, "bridge_port": prefs.bridge_port,
            "token": addon.SERVICE.token, "pid": addon.SERVICE.process.pid,
            "log": str(addon.SERVICE.directory / "service.log"),
            "blend_file": str(blend_file),
            "host_binary": bpy.app.binary_path,
        })

    try:
        deadline = time.monotonic() + 30
        while addon.SERVICE.poll() != "Running":
            if time.monotonic() > deadline:
                raise RuntimeError("Integration startup timed out")
            addon._bridge.poll()
            time.sleep(0.02)
        publish()
        while not (control / "stop").exists():
            command_file = control / "action.json"
            if command_file.exists():
                action = json.loads(command_file.read_text(encoding="utf-8"))["action"]
                command_file.unlink()
                if action == "parent-exit":
                    os._exit(0)
                elif action == "stop-start":
                    addon.stop_service()
                    addon.start_service()
                elif action == "timer-exception":
                    bridge = addon._bridge
                    original_poll = bridge.poll
                    def unexpected_poll_error():
                        raise ValueError("Injected unexpected bridge failure")
                    bridge.poll = unexpected_poll_error
                    try:
                        assert addon._poll_service() is None
                        assert "ValueError: Injected unexpected bridge failure" in addon.LAST_ERROR
                        assert addon.SERVICE.process is None and addon._bridge is None
                    finally:
                        bridge.poll = original_poll
                    addon.start_service()
                elif action == "upgrade":
                    assert repo is not None
                    before = json.loads((Path(addon.__file__).parent / "provenance.json").read_text())
                    previous = addon.SERVICE.process
                    token = addon.SERVICE.token
                    port_values = (prefs.http_port, prefs.bridge_port)
                    expected = json.loads((control / "expected-upgrade.json").read_text())
                    assert before["extension_version"] == expected["before"]
                    assert bpy.ops.extensions.repo_sync(repo_index=repo_index) == {"FINISHED"}
                    assert bpy.ops.extensions.package_upgrade_all(use_active_only=True) == {"FINISHED"}
                    assert previous.poll() is not None, "Upgrade left the old service alive"
                    addon = importlib.import_module(module_name)
                    prefs = bpy.context.preferences.addons[module_name].preferences
                    assert (prefs.http_port, prefs.bridge_port) == port_values
                    assert not prefs.autostart
                    after = json.loads((Path(addon.__file__).parent / "provenance.json").read_text())
                    assert after["extension_version"] == expected["after"]
                    addon.start_service()
                    assert addon.SERVICE.token == token, "Upgrade replaced the user's HTTP credential"
                elif action == "cleanup-error":
                    previous = addon.SERVICE.process
                    original_stop = addon.SERVICE.stop
                    def injected_stop():
                        original_stop()
                        raise OSError("Injected cleanup error")
                    addon.SERVICE.stop = injected_stop
                    try:
                        try:
                            addon.stop_service()
                        except ExceptionGroup as error:
                            assert "Injected cleanup error" in str(error)
                        else:
                            raise AssertionError("Cleanup error was swallowed")
                        assert previous.poll() is not None
                        assert addon._bridge is None, "A failed process cleanup prevented bridge cleanup"
                    finally:
                        del addon.SERVICE.stop
                    addon.start_service()
                elif action == "port-conflict":
                    addon.stop_service()
                    with socket.socket() as occupied:
                        if os.name != "nt":
                            occupied.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                        occupied.bind(("127.0.0.1", prefs.http_port))
                        occupied.listen(1)
                        try:
                            addon.start_service()
                        except addon.ServiceError as error:
                            assert "already in use" in str(error)
                        else:
                            raise AssertionError("Port conflict did not fail")
                    addon.start_service()
                elif action == "crash-recovery":
                    addon.SERVICE.process.terminate()
                    addon.SERVICE.process.wait(timeout=5)
                    assert addon._poll_service() is None
                    assert addon.SERVICE.process is None
                    assert addon._bridge is None
                    addon.start_service()
                elif action == "disable-enable":
                    http_value, bridge_value = prefs.http_port, prefs.bridge_port
                    process = addon.SERVICE.process
                    assert bpy.ops.preferences.addon_disable(module=module_name) == {"FINISHED"}
                    assert process.poll() is not None
                    assert module_name not in bpy.context.preferences.addons
                    assert bpy.ops.preferences.addon_enable(module=module_name) == {"FINISHED"}
                    addon = importlib.import_module(module_name)
                    prefs = bpy.context.preferences.addons[module_name].preferences
                    prefs.autostart = False
                    prefs.http_port, prefs.bridge_port = http_value, bridge_value
                    addon.start_service()
                elif action == "duplicate-start":
                    pid = addon.SERVICE.process.pid
                    try:
                        addon.start_service()
                    except addon.ServiceError as error:
                        assert "already" in str(error)
                    else:
                        raise AssertionError("Duplicate start did not fail")
                    assert addon.SERVICE.process.pid == pid
                else:
                    raise ValueError(action)
                while addon.SERVICE.poll() != "Running":
                    addon._bridge.poll()
                    time.sleep(0.02)
                publish()
                write_json(control / "action-result.json", {"action": action, "status": "Passed"})
            addon.SERVICE.poll()
            addon._bridge.poll_blocking(timeout=0.02)
    finally:
        addon.stop_service()
        bpy.ops.preferences.addon_disable(module=module_name)


def install(arguments, package):
    if len(arguments) == 5:
        bpy.context.preferences.system.use_online_access = True
        repo = bpy.context.preferences.extensions.repos.new(
            name="Integration Test", module="integration_test", remote_url=arguments[4],
        )
        repo.use_sync_on_startup = False
        repo_index = list(bpy.context.preferences.extensions.repos).index(repo)
        bpy.context.preferences.extensions.active_repo = repo_index
        assert bpy.ops.extensions.repo_sync(repo_index=repo_index) == {"FINISHED"}
        outcome = bpy.ops.extensions.package_install(
            repo_index=repo_index, pkg_id="blender_mcp_integration", enable_on_install=True,
        )
    else:
        outcome = bpy.ops.extensions.package_install_files(
            filepath=str(Path(package).resolve()), repo="user_default", enable_on_install=True,
        )
    assert outcome == {"FINISHED"}, outcome


def make_cli_fixture(control):
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
    bpy.context.scene["mcp_fixture"] = "all-tools"


if __name__ == "__main__":
    main()
