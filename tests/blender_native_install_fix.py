"""Check native installation and reinstallation in an isolated Blender host."""

import hashlib
import importlib
import os
import platform
import sys
import tomllib
import zipfile
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))
from check_reports import write_json
from native_install_capture import capture_install


def check_installed(module_name, profile, expected_version):
    addon = importlib.import_module(module_name)
    module_path = Path(addon.__file__).resolve()
    assert module_path.is_relative_to(profile), module_path
    manifest_path = module_path.parent / "blender_manifest.toml"
    manifest = tomllib.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["version"] == expected_version, manifest
    assert module_name in bpy.context.preferences.addons, module_name
    preferences = bpy.context.preferences.addons[module_name].preferences
    preferences.autostart = False
    return {
        "module_path": str(module_path),
        "manifest": str(manifest_path),
        "version": manifest["version"],
        "enabled": True,
        "module_in_isolated_profile": "Passed",
    }


def install(package, control, profile, module_name, expected_version, report, stage):
    stage_directory = control / stage
    stage_directory.mkdir(parents=True, exist_ok=True)
    result = {"status": "Not Run"}
    report[stage] = result
    try:
        with capture_install(stage_directory) as trace:
            result["native_install"] = trace
            outcome = bpy.ops.extensions.package_install_files(
                filepath=str(package), repo="user_default", enable_on_install=True,
            )
            result["operator_result"] = sorted(outcome)
            assert outcome == {"FINISHED"}, outcome
        errors = [message for kind, message in trace["messages"] if kind in {"ERROR", "FATAL_ERROR"}]
        assert not errors, errors
        result.update(check_installed(module_name, profile, expected_version))
        result["status"] = "Passed"
    except Exception as error:
        result.update(status="Failed", error=f"{type(error).__name__}: {error}")
        raise


def main():
    from bl_pkg import bl_extension_utils

    package_argument, installer_argument, control_argument = sys.argv[sys.argv.index("--") + 1:]
    package = Path(package_argument).resolve()
    installer = Path(installer_argument).resolve()
    control = Path(control_argument).resolve()
    control.mkdir(parents=True, exist_ok=True)
    report = {
        "status": "Not Run",
        "scope": "Real Blender native installation, reinstallation and add-on enablement",
        "mcp_service_validation": "Not Run",
        "blender_version": bpy.app.version_string,
        "blender_binary": bpy.app.binary_path,
        "background": bpy.app.background,
        "platform": platform.platform(),
        "architecture": platform.machine(),
        "python_version": platform.python_version(),
        "python_executable": sys.executable,
        "package": str(package),
        "patched_installer": str(installer),
        "install": {"status": "Not Run"},
        "disable": {"status": "Not Run"},
        "reinstall": {"status": "Not Run"},
    }
    original_command = bl_extension_utils.blender_ext_cmd
    try:
        assert bpy.app.background, "Run this check with --background"
        profile = Path(os.environ["BLENDER_USER_RESOURCES"]).resolve()
        assert profile.is_relative_to((ROOT / "build/.working").resolve()), profile
        report["profile"] = str(profile)
        repository = next(repo for repo in bpy.context.preferences.extensions.repos if repo.module == "user_default")
        assert Path(repository.directory).resolve().is_relative_to(profile), repository.directory
        report["repository"] = str(Path(repository.directory).resolve())
        report["package_sha256"] = hashlib.sha256(package.read_bytes()).hexdigest()
        report["patched_installer_sha256"] = hashlib.sha256(installer.read_bytes()).hexdigest()
        with zipfile.ZipFile(package) as archive:
            expected = tomllib.loads(archive.read("blender_manifest.toml").decode("utf-8"))
        assert expected["id"] == "blender_mcp_integration", expected["id"]
        report["expected_version"] = expected["version"]
        module_name = "bl_ext.user_default.blender_mcp_integration"
        assert module_name not in bpy.context.preferences.addons, "The isolated profile must start without this add-on"

        def patched_command(python_args):
            return (sys.executable, *python_args, str(installer))

        system_installer = Path(original_command(bpy.app.python_args)[-1]).resolve()
        report["installer_selection"] = "system" if installer == system_installer else "working copy"
        if installer != system_installer:
            bl_extension_utils.blender_ext_cmd = patched_command
        install(package, control, profile, module_name, expected["version"], report, "install")
        report["disable"]["status"] = "Failed"
        outcome = bpy.ops.preferences.addon_disable(module=module_name)
        report["disable"]["operator_result"] = sorted(outcome)
        assert outcome == {"FINISHED"}, outcome
        assert module_name not in bpy.context.preferences.addons, module_name
        report["disable"]["status"] = "Passed"
        install(package, control, profile, module_name, expected["version"], report, "reinstall")
        report["status"] = "Passed"
    except Exception as error:
        report.update(status="Failed", error=f"{type(error).__name__}: {error}")
        raise
    finally:
        bl_extension_utils.blender_ext_cmd = original_command
        write_json(control / "host-result.json", report)


if __name__ == "__main__":
    main()
