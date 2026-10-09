"""Resolve locked native build inputs and portable process options."""

import importlib.util
import json
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_package = types.ModuleType("integration_build_runtime")
_package.__path__ = [str(ROOT / "src/blender_mcp_integration")]
sys.modules[_package.__name__] = _package
_spec = importlib.util.spec_from_file_location("integration_build_runtime.runtime", ROOT / "src/blender_mcp_integration/runtime.py")
runtime = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(runtime)


def records():
    return json.loads((ROOT / "packaging/platforms.json").read_text(encoding="utf-8"))


def resolve(identifier=None):
    identifier = identifier or runtime.platform_id()
    record = records()[identifier]
    return identifier, record


def package_name(version, identifier):
    return f"blender_mcp_integration-{version}-{identifier}.zip"


def process_options(gui=False):
    return runtime.process_options(gui)
