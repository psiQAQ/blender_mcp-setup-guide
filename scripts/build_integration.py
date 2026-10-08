"""Build and validate a native Blender MCP Extension from locked inputs."""

import argparse
import hashlib
import importlib.metadata
import json
import os
import shutil
import string
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from platforms import resolve, package_name
from publication import extension_version
from upstream_source import verify_source


ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = ROOT / "packaging/upstream.json"
REQUIREMENTS = ROOT / "packaging/requirements-windows-cp313.txt"
WHEEL_LOCK = ROOT / "packaging/wheels-windows-cp313.json"


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def run(command, **kwargs):
    temporary = ROOT / "build/tool-temp"
    temporary.mkdir(parents=True, exist_ok=True)
    kwargs.setdefault("env", {**os.environ, "TMP": str(temporary), "TEMP": str(temporary)})
    subprocess.run([str(value) for value in command], check=True, **kwargs)


def checked_replace(path, before, after):
    content = path.read_text(encoding="utf-8")
    if content.count(before) != 1:
        raise RuntimeError(f"Pinned upstream patch context changed: {path}")
    path.write_text(content.replace(before, after), encoding="utf-8", newline="\n")


def patch_bridge(vendor):
    bridge = vendor / "bridge/mcp_to_blender_server.py"
    checked_replace(bridge, "import json\n", "import hmac\nimport json\n")
    checked_replace(
        bridge, "    request = json.loads(data)\n",
        '    request = json.loads(data)\n'
        '    expected_token = globals().get("_integration_token", "")\n'
        '    supplied_token = request.get("token", "") if isinstance(request, dict) else ""\n'
        '    if not expected_token or not isinstance(supplied_token, str) or not hmac.compare_digest(supplied_token.encode("utf-8"), expected_token.encode("utf-8")):\n'
        '        return _ExecResult({"status": "error", "message": "Bridge authentication required"}), False\n',
    )
    connection = vendor / "blmcp/tools_helpers/connection.py"
    checked_replace(connection, '        "type": "execute",\n', '        "type": "execute",\n        "token": os.environ["BLENDER_MCP_TOKEN"],\n')
    deferred = vendor / "bridge/deferred_tool.py"
    checked_replace(
        deferred,
        '        # Validate JSON serializability when strict_json is set.\n'
        '        if dc.strict_json:\n'
        '            try:\n'
        '                json.dumps(result)\n'
        '            except (TypeError, ValueError) as ex:\n'
        '                _send_and_close(dc, {\n'
        '                    "status": "error",\n'
        '                    "message": "Deferred result is not JSON-serializable: {:s}".format(str(ex)),\n'
        '                })\n'
        '                did_work = True\n'
        '                continue\n',
        '        # Every deferred response crosses the JSON transport boundary.\n'
        '        try:\n'
        '            json.dumps(result)\n'
        '        except (TypeError, ValueError, RecursionError) as ex:\n'
        '            _send_and_close(dc, {\n'
        '                "status": "error",\n'
        '                "message": "Deferred result is not JSON-serializable: {:s}".format(str(ex)),\n'
        '            })\n'
        '            did_work = True\n'
        '            continue\n',
    )


def acquire_upstream(lock, requested):
    verify_source(lock)
    source = requested or ROOT / "submodules/blender_mcp"
    if not (source / ".git").exists():
        raise RuntimeError("Initialize the pinned official submodule: git submodule update --init submodules/blender_mcp")
    if requested is None:
        entry = subprocess.check_output(["git", "-C", str(ROOT), "ls-tree", "HEAD", "submodules/blender_mcp"], text=True).split()
        if len(entry) < 3 or entry[:3] != ["160000", "commit", lock["commit"]]:
            raise RuntimeError("Committed submodule pointer differs from packaging/upstream.json")
    actual = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip()
    dirty = subprocess.check_output(["git", "-C", str(source), "status", "--porcelain"], text=True).strip()
    if actual != lock["commit"] or dirty:
        raise RuntimeError("Upstream checkout must be clean and match packaging/upstream.json")
    origin = subprocess.check_output(["git", "-C", str(source), "remote", "get-url", "origin"], text=True).strip()
    if origin.removesuffix(".git") != lock["repository"].removesuffix(".git"):
        raise RuntimeError("Upstream origin differs from the locked official repository")
    return source


def verify_wheels(wheelhouse, wheel_lock=WHEEL_LOCK):
    locked = json.loads(wheel_lock.read_text(encoding="utf-8"))
    for wheel in locked:
        path = wheelhouse / wheel["filename"]
        if not path.is_file() or digest(path) != wheel["sha256"]:
            raise RuntimeError(f"Missing or altered locked wheel: {path}")
    return locked


def check_build_runtime(python, lock, target):
    probe = "import json,platform,struct,sys; print(json.dumps({'implementation':platform.python_implementation(),'python':f'{sys.version_info.major}.{sys.version_info.minor}','platform':platform.system(),'machine':platform.machine().lower(),'bits':struct.calcsize('P')*8}))"
    result = json.loads(subprocess.check_output([str(python), "-I", "-S", "-B", "-c", probe], text=True))
    if result["machine"] == "x86_64":
        result["machine"] = "amd64"
    if result != {"implementation": "CPython", "python": lock["python"], "platform": target["system"], "machine": target["machine"], "bits": 64}:
        raise RuntimeError(f"Build requires {target['system']} {target['machine']} CPython {lock['python']}; detected {result}")


def build(args):
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    identifier, target = resolve(args.platform)
    lock["platform"] = identifier
    requirements = ROOT / "packaging" / target["requirements"]
    wheel_lock = ROOT / "packaging" / target["wheel_lock"]
    args.wheelhouse = args.wheelhouse or ROOT / "build/wheels" / identifier
    check_build_runtime(args.python, lock, target)
    version = extension_version(lock)
    source = acquire_upstream(lock, args.upstream)
    import tomllib
    source_version = tomllib.loads((source / "mcp/pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    if source_version != lock["version"]:
        raise ValueError("Pinned source version differs from the recorded server version")
    args.wheelhouse.mkdir(parents=True, exist_ok=True)
    if not args.offline:
        run([args.python, "-m", "pip", "download", "--quiet", "--only-binary=:all:", "--no-deps", "--require-hashes",
             "-r", requirements, "--dest", args.wheelhouse, "--cache-dir", ROOT / "build/pip-cache",
             "--index-url", "https://pypi.org/simple"])
    wheels = verify_wheels(args.wheelhouse, wheel_lock)
    work = ROOT / "build/work"
    work.mkdir(parents=True, exist_ok=True)
    args.output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="integration-", dir=work) as temporary:
        locked_wheels = Path(temporary) / "locked-wheels"
        locked_wheels.mkdir()
        for wheel in wheels:
            shutil.copyfile(args.wheelhouse / wheel["filename"], locked_wheels / wheel["filename"])
        stage = Path(temporary) / "blender_mcp_integration"
        shutil.copytree(ROOT / "src/blender_mcp_integration", stage, ignore=shutil.ignore_patterns("__pycache__"))
        vendor = stage / "_vendor"
        vendor.mkdir()
        upstream_license = source / "LICENSE"
        if upstream_license.is_file():
            shutil.copyfile(upstream_license, vendor / "LICENSE")
        (vendor / "__init__.py").write_text("", encoding="utf-8")
        bridge = vendor / "bridge"
        bridge.mkdir()
        (bridge / "__init__.py").write_text("", encoding="utf-8")
        for module in sorted((source / "addon/blender_mcp_addon").glob("*.py")):
            if module.name != "__init__.py":
                shutil.copyfile(module, bridge / module.name)
        shutil.copytree(source / "mcp/blmcp", vendor / "blmcp", ignore=shutil.ignore_patterns("__pycache__"))
        original_hashes = {str(path.relative_to(vendor)): digest(path) for path in (bridge / "mcp_to_blender_server.py", bridge / "deferred_tool.py", vendor / "blmcp/tools_helpers/connection.py")}
        patch_bridge(vendor)
        runtime = vendor / "runtime"
        run([args.python, "-m", "pip", "--isolated", "install", "--quiet", "--no-index", "--find-links", locked_wheels,
             "--only-binary=:all:", "--no-deps", "--require-hashes", "--no-compile", "--target", runtime, "-r", requirements])
        provenance = {
            **lock, "extension_version": version,
            "upstream_submodule_commit": lock["commit"],
            "source_version": source_version,
            "upstream_license_sha256": digest(upstream_license) if upstream_license.is_file() else None,
            "integration_commit": subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip(),
            "integration_dirty": bool(subprocess.check_output(["git", "-C", str(ROOT), "status", "--porcelain"], text=True).strip()),
            "requirements_sha256": digest(requirements), "wheel_lock_sha256": digest(wheel_lock),
            "wheels": wheels,
            "downstream_patches": [
                {"path": name, "original_sha256": original, "patched_sha256": digest(vendor / name)}
                for name, original in original_hashes.items()
            ],
            "dependencies": sorted(
                ({"name": distribution.metadata["Name"], "version": distribution.version}
                 for distribution in importlib.metadata.distributions(path=[str(runtime)])),
                key=lambda dependency: dependency["name"].lower(),
            ),
        }
        (stage / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
        shutil.copyfile(ROOT / "LICENSE", stage / "LICENSE")
        template = (ROOT / "packaging/blender_manifest.toml.in").read_text(encoding="utf-8")
        (stage / "blender_manifest.toml").write_text(string.Template(template).substitute(version=version, platform=identifier, **{key: lock[key] for key in ("blender_min", "blender_max")}), encoding="utf-8")
        run([args.blender, "--command", "extension", "build", "--source-dir", stage, "--output-dir", args.output])
    package = args.output / package_name(version, identifier)
    (args.output / f"blender_mcp_integration-{version}.zip").rename(package)
    run([args.blender, "--command", "extension", "validate", package])
    with zipfile.ZipFile(package) as archive:
        if any(part in {"__pycache__", ".venv", ".git"} for name in archive.namelist() for part in Path(name).parts):
            raise RuntimeError("Build contains development files")
    (args.output / f"{package.name}.sha256").write_text(f"{digest(package)}  {package.name}\n", encoding="utf-8")
    (args.output / f"provenance-{identifier}.json").write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    print(package)
    return package


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blender", required=True, type=Path)
    parser.add_argument("--python", default=Path(sys.executable), type=Path)
    parser.add_argument("--upstream", type=Path)
    parser.add_argument("--platform", choices=("windows-x64", "linux-x64", "macos-arm64"))
    parser.add_argument("--wheelhouse", type=Path)
    parser.add_argument("--output", default=ROOT / "build/dist", type=Path)
    parser.add_argument("--offline", action="store_true")
    build(parser.parse_args())


if __name__ == "__main__":
    main()
