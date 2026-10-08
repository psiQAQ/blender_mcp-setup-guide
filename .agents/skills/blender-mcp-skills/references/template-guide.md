# Template Guide

## Built-in template

Use this local template:

- `templates/extension_addon/` (explicit registration and rollback)

Compatibility target:

- Blender **4.2+** (Extension system)

Manifest reference:

- `./manifest-fields.md`

## Mandatory pre-step: system adaptation

Before running Blender commands or editing add-on files, read:

- `./system-adaptation.md`

Before Blender operations, obtain the target runtime through MCP or an explicitly selected local Blender executable:

1. Agent runtime system
2. Blender runtime system

Then choose the file and path strategy for:

- same-system runtime
- cross-system runtime (including WSL to Windows `/mnt/c/...` mapping when applicable)

## Template structure

| Path | Responsibility |
| --- | --- |
| `blender_manifest.toml`, `LICENSE` | Package metadata and license |
| `__init__.py` | Explicit registration and rollback |
| `constants.py`, `properties.py`, `preferences.py` | Identifiers and settings |
| `operators/`, `panels/`, `utils/` | Actions, UI and shared helpers |
| `scripts/` | Development validation, build and optional sync |
| `wheels/` (when required) | Manifest-listed offline dependencies |

## Why this structure

- `blender_manifest.toml`: extension metadata and compatibility.
- `__init__.py`: explicit class order, failure rollback, and reverse cleanup.
- `constants.py`: centralized IDs and naming constants for safer renames.
- `properties.py`: PropertyGroup and scene pointer property side effects.
- `operators/object_ops.py`: executable actions.
- `panels/viewport_panel.py`: UI layout.
- `preferences.py`: add-on settings entry point.
- `utils/common.py`: shared helper functions for reusable logic.
- `wheels`: preferred location for release-time offline dependency wheels listed in `blender_manifest.toml`.
- `scripts/validate_extension.py`: merged validator (local preflight + `blender --command extension validate`).
- `scripts/build_extension.py`: unified Python build entrypoint with system checks and Blender path resolution.
- `scripts/*`: validation, build orchestration, and optional sync helper.

## Recommended usage flow

1. Generate with the repository's `scripts/scaffold_extension.py <id> <new-directory>`, or copy the template and replace both identifier prefixes consistently.
2. Update manifest fields (`id`, `name`, `maintainer`, `version`).
3. Rename example classes and operator IDs.
4. Reload add-on and verify panel/operator/property behavior.
5. Bundle required dependencies as manifest wheels; see `dependency-policy.md`.

## Dependency packaging guidance

- Store writable data in the Extension user directory.
- For published extensions, prefer `wheels = [...]` in `blender_manifest.toml` and store wheel files under `wheels/`.

## Build extension package

Run in the add-on root directory:

```bash
python scripts/build_extension.py --blender <executable> --output-dir <package-directory>
```

Python interpreter priority for scripted checks/build:

1. User-specified extension development Python environment
2. Project virtual environment (`.venv`)
3. Blender bundled Python from MCP (`bpy.app.binary_path_python`)
4. System Python in PATH

## Install package to Extensions repo

After build, install zip to an extension repository (prefer `user_default`) instead of legacy add-on folders.

```python
bpy.ops.extensions.package_install_files(
    filepath=r"C:\\path\\to\\your_extension-1.0.0.zip",
    repo="user_default",
    enable_on_install=True,
    overwrite=True,
)
```

Verification key pattern in preferences map:

- `bl_ext.<repo_module>.<extension_id>`

Detailed install checklist:

- `./extension-install.md`
