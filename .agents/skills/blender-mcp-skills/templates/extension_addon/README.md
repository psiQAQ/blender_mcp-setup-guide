# Blender Extension Add-on Template (4.2+)

This template is a modular starter for Blender Extension Add-ons.

It registers an explicit class list in dependency order and rolls back partial registration on failure.

The root `__init__.py` owns class registration. Module-level functions attach and remove Scene properties; cleanup runs in reverse order.

## Folder layout

| Path | Responsibility |
| --- | --- |
| `blender_manifest.toml`, `LICENSE` | Package metadata and license |
| `__init__.py` | Explicit registration and rollback |
| `constants.py`, `properties.py`, `preferences.py` | Identifiers and settings |
| `operators/`, `panels/`, `utils/` | Actions, UI and shared helpers |
| `scripts/` | Development validation, build and optional sync |

## When to use this template

Use this template for Blender 4.2+ extension development.

## Quick start

1. Copy this folder and rename it to your extension module name.
2. Update `blender_manifest.toml`:
   - `id`
   - `name`
   - `maintainer`
   - `version`
3. Replace `my_example_extension` and `MY_EXAMPLE_EXTENSION` consistently across source and metadata. The repository generator `scripts/scaffold_extension.py <id> <new-directory>` performs this replacement and supplies the license.
4. Disable/enable in Blender and verify registration behavior.

## Build

Run in the extension root directory (where `blender_manifest.toml` is located):

```bash
python scripts/build_extension.py --blender <executable> --output-dir <package-directory>
```

## Scripted validation and build

Run from the extension root (the folder containing `blender_manifest.toml`).

```bash
# Optional: gather Blender runtime info from MCP and save to JSON
# (binary_path / binary_path_python / blender_system / extension_root)

# Validate (local preflight + blender --command extension validate)
python scripts/validate_extension.py

# Validate with explicit Blender executable
python scripts/validate_extension.py \
  --blender "/path/to/blender"

# Unified build entrypoint (runs validate_extension.py first)
python scripts/build_extension.py \
  --mcp-info-json /path/to/blender_mcp_info.json

# Cross-system mode example (WSL -> Windows Blender)
python scripts/build_extension.py \
  --mcp-info-json /path/to/blender_mcp_info.json \
  --allow-cross-system
```

## Standard local verification commands

Run from the extension root to perform a minimal local verification pass:

```bash
# Python syntax check
python -m py_compile \
  __init__.py \
  constants.py \
  preferences.py \
  properties.py \
  operators/object_ops.py \
  panels/viewport_panel.py \
  utils/common.py \
  scripts/build_extension.py \
  scripts/sync_and_reload.py \
  scripts/validate_extension.py

# Local preflight only (no Blender invocation)
python scripts/validate_extension.py --skip-blender-validate

# Full validate when Blender is available
python scripts/validate_extension.py --blender "/path/to/blender"

# Build extension zip
python scripts/build_extension.py --blender "/path/to/blender"
```

Python interpreter selection priority used by script orchestration:

1. User-specified interpreter (`--python` or `EXTENSION_DEV_PYTHON`)
2. Project virtual environment (`.venv`)
3. Blender bundled Python (`binary_path_python` from MCP info JSON or `BLENDER_PYTHON`)
4. System Python from PATH (`python3` / `python`)

## sync_and_reload helper (optional)

```bash
python scripts/sync_and_reload.py \
  --source /path/to/source/addon \
  --target "/path/to/blender/extensions/user_default/my_example_extension" \
  --module my_addon \
  --delete-stale \
  --dry-run
```

Legacy `scripts/addons` targets are blocked by default in extension-only workflow.
Use `--allow-legacy-target` only when intentionally developing a legacy add-on.

## Development notes

- For WSL + Windows Blender, target installed extension repo paths, and ensure paths are Blender-host resolvable.
- Keep one authoritative explicit class list in the root `__init__.py` and verify rollback and reverse cleanup.
- Bundle required dependencies as manifest wheels; writable data belongs in `bpy.utils.extension_path_user(...)`.
