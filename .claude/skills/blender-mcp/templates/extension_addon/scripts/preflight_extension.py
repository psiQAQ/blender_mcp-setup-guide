#!/usr/bin/env python3
"""Preflight checks for Blender extension templates."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    print("ERROR: Python 3.11+ is required (tomllib unavailable).")
    sys.exit(2)


REQUIRED_MANIFEST_KEYS = (
    "id",
    "version",
    "name",
    "type",
    "blender_version_min",
    "license",
)


def _discover_extension_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _read_manifest(manifest_path: Path) -> dict:
    with manifest_path.open("rb") as f:
        data = tomllib.load(f)
    if not isinstance(data, dict):
        raise ValueError("Manifest root must be a TOML table.")
    return data


def _collect_project_modules(extension_root: Path) -> set[str]:
    modules: set[str] = set()

    for path in extension_root.rglob("*.py"):
        if "scripts" in path.relative_to(extension_root).parts:
            continue

        rel_parts = path.relative_to(extension_root).parts
        if rel_parts[-1] == "__init__.py":
            if len(rel_parts) >= 2:
                modules.add(rel_parts[-2])
            continue
        modules.add(path.stem)

    for path in extension_root.iterdir():
        if path.is_dir() and (path / "__init__.py").exists() and path.name != "scripts":
            modules.add(path.name)

    return modules


def _scan_absolute_import_warnings(extension_root: Path, project_modules: set[str]) -> list[str]:
    warnings: list[str] = []

    for path in extension_root.rglob("*.py"):
        rel = path.relative_to(extension_root)
        if "scripts" in rel.parts:
            continue

        source = path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError as exc:
            warnings.append(f"{rel}: skipped import scan due to syntax error ({exc.msg}).")
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.name
                    if "." not in name:
                        continue
                    top = name.split(".", 1)[0]
                    if top in project_modules:
                        warnings.append(
                            f"{rel}:{node.lineno} uses project absolute import '{name}' (prefer relative imports)."
                        )
            elif isinstance(node, ast.ImportFrom):
                if node.level != 0 or not node.module:
                    continue
                top = node.module.split(".", 1)[0]
                if top in project_modules:
                    warnings.append(
                        f"{rel}:{node.lineno} uses project absolute import '{node.module}' (prefer relative imports)."
                    )

    return warnings


def main() -> int:
    extension_root = _discover_extension_root()
    manifest_path = extension_root / "blender_manifest.toml"

    errors: list[str] = []
    warns: list[str] = []

    if not manifest_path.exists():
        errors.append("blender_manifest.toml not found in extension root.")
    else:
        try:
            manifest = _read_manifest(manifest_path)
        except Exception as exc:  # pragma: no cover
            errors.append(f"failed to parse blender_manifest.toml: {exc}")
            manifest = {}

        missing = [key for key in REQUIRED_MANIFEST_KEYS if key not in manifest]
        for key in missing:
            errors.append(f"missing required manifest key: {key}")

        wheels = manifest.get("wheels")
        if wheels is not None:
            if not isinstance(wheels, list):
                errors.append("manifest key 'wheels' must be a list when present.")
            else:
                for idx, wheel in enumerate(wheels):
                    if not isinstance(wheel, str):
                        errors.append(f"wheels[{idx}] must be a string path.")
                        continue
                    wheel_path = (extension_root / wheel).resolve()
                    try:
                        wheel_path.relative_to(extension_root)
                    except ValueError:
                        errors.append(f"wheel path must stay within extension root: {wheel}")
                        continue
                    if not wheel_path.exists():
                        errors.append(f"wheel path does not exist: {wheel}")

    project_modules = _collect_project_modules(extension_root)
    warns.extend(_scan_absolute_import_warnings(extension_root, project_modules))

    print(f"OK: extension root = {extension_root}")

    if errors:
        for msg in errors:
            print(f"ERROR: {msg}")
    else:
        print("OK: manifest and wheel checks passed")

    if warns:
        for msg in warns:
            print(f"WARN: {msg}")
    else:
        print("OK: no project absolute-import warnings")

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
