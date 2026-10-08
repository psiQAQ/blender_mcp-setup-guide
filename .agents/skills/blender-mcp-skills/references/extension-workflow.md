# Extension Development Workflow

Use this workflow for iterative extension add-on development.

## Before running commands or file operations

Read:

- `./system-adaptation.md`

That document defines how to:

- detect agent runtime system and Blender runtime system
- choose same-system or cross-system file strategy
- resolve path handling details (including WSL `/mnt/c/...` cases)

## Template policy

Use only this template:

- `templates/extension_addon/`

Registration uses explicit class lists, rollback on failure, and reverse cleanup.

## Version policy

Target Blender 4.2+ extension workflow.

Do not add legacy add-on compatibility branches in the default flow.

## Core iteration loop

1. Edit code in project workspace.
2. For dev reload, sync changed source files to the active development module path only when needed.
3. Disable and re-enable add-on in Blender.
4. Verify behavior.
5. Repeat until stable.

## Build and install (extension-native, required before delivery)

1. Run `python scripts/build_extension.py --blender <executable> --output-dir <directory>` in the Extension root. It validates the source and final ZIP.
2. Install generated zip into extension repo (prefer `user_default`) using Blender extension install flow.
3. Confirm extension is enabled under key `bl_ext.<repo_module>.<extension_id>`.

Do not treat extension packages as legacy add-ons. Specifically, do not deploy extension source to legacy paths like:

- `.../scripts/addons/<module>`
- `D:\\Program Files\\Blender Foundation\\addons\\<module>`

Install operator example:

```python
bpy.ops.extensions.package_install_files(
    filepath=r"C:\\path\\to\\your_extension-1.0.0.zip",
    repo="user_default",
    enable_on_install=True,
    overwrite=True,
)
```

See also:

- `./extension-install.md`

## Minimal reload commands

```python
bpy.ops.preferences.addon_disable(module="my_addon")
bpy.ops.preferences.addon_enable(module="my_addon")
```

## Build-before-reload (optional)

When the extension has build artifacts or generated outputs, run build scripts before reload.

Recommended order:

1. Obtain runtime facts through MCP or the selected local Blender executable and confirm the Extension root containing `blender_manifest.toml`.
2. Review manifest fields against `./manifest-fields.md` when metadata was edited.
3. Run unified Python build entrypoint (`scripts/build_extension.py`) which calls `scripts/validate_extension.py` first.
4. Sync changed files to Blender target directory.
5. Run add-on disable/enable.

Python interpreter priority for script execution:

1. User-specified extension development Python environment
2. Project virtual environment (`.venv`)
3. Blender bundled Python from MCP (`bpy.app.binary_path_python`)
4. System Python in PATH

## sync_and_reload helper (optional)

Template script:

- `templates/extension_addon/scripts/sync_and_reload.py`

Purpose:

- Provides `--source`, `--target`, `--module`, `--dry-run`, `--delete-stale`, and `--allow-legacy-target` CLI.
- Syncs only newer/new files (currently `.py` / `.toml` / `.json`).
- Prints next-step Blender reload commands and does not call Blender API.

Example:

```bash
python templates/extension_addon/scripts/sync_and_reload.py \
  --source /path/to/workspace/addon_src \
  --target "/path/to/blender/extensions/user_default/my_extension" \
  --module my_addon \
  --delete-stale \
  --dry-run
```

WSL development + Windows Blender example:

```bash
python templates/extension_addon/scripts/sync_and_reload.py \
  --source /home/ustcw/project-folder/blender_mcp/my_addon \
  --target "/mnt/c/Users/<user>/AppData/Roaming/Blender Foundation/Blender/4.5/extensions/user_default/my_extension" \
  --module my_addon \
  --delete-stale \
  --dry-run
```

The exact installed extension directory should be discovered from Blender extension repository settings or from the enabled module key `bl_ext.<repo_module>.<extension_id>`.

## Dependency install policy

- Silent auto-install is forbidden.
- Required dependencies are bundled as manifest wheels.
- Writable data uses `bpy.utils.extension_path_user(...)`.
- Independent services initialize their own locked runtime without changing Blender's module search path.
- Do not install packages into Blender bundled Python global `site-packages`.
- Do not hide network installs in `register()` or add-on enable flow.
- The helper only syncs files and prints reload hints; it does not install dependencies.

## CI release reference (extension-native)

The repository's `.github/workflows/ci.yml` validates unit tests, generated templates, and the integrated package. `release.yml` consumes validated artifacts. For a standalone project, adapt this minimal reference by supplying a compatible Blender executable:

```yaml
name: extension-release
on:
  push:
    tags:
      - "v*"
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: python scripts/build_extension.py
```

### version consistency check

Before build, validate git tag and manifest `version` consistency. Fail fast when they do not match.

## Safety checks

- Quote paths with spaces.
- Use module name (not display name) for disable/enable.
- Avoid relying on `hasattr(bpy.ops...)` for unregister checks.
