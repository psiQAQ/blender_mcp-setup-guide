# Blender Extension Add-on Template (4.2+) — autoload-only variant

This template is a modular starter for Blender Extension Add-ons.

It uses `auto_load.py` to discover submodules and register classes in topological order.

Class registration is handled by `auto_load.py`. Module-level `register()`/`unregister()` should be used only for non-class side effects (for example Scene property attach/detach).

## Folder layout

```text
extension_addon/
├─ blender_manifest.toml
├─ __init__.py
├─ auto_load.py
├─ _properties.py
├─ _operators.py
├─ _panels.py
├─ _preferences.py
├─ scripts/
│  ├─ preflight_extension.py
│  ├─ build_extension.sh
│  ├─ build_extension.ps1
│  └─ sync_and_reload.py
└─ README.md
```

## When to use this template

Use this template for Blender 4.2+ extension development.

## Quick start

1. Copy this folder and rename it to your extension module name.
2. Update `blender_manifest.toml`:
   - `id`
   - `name`
   - `maintainer`
   - `version`
3. Replace demo class names and IDs.
4. Disable/enable in Blender and verify registration behavior.

## Build

Run in the extension root directory (where `blender_manifest.toml` is located):

```bash
blender --command extension build
```

## Scripted preflight and build

Run from the extension root (the folder containing `blender_manifest.toml`).

```bash
# Run checks only
python scripts/preflight_extension.py

# Build with preflight (Bash)
bash scripts/build_extension.sh

# Show Bash script help
bash scripts/build_extension.sh --help
```

```powershell
# Build with preflight (PowerShell)
pwsh -File scripts/build_extension.ps1

# Show PowerShell script help
pwsh -File scripts/build_extension.ps1 -Help
```

## sync_and_reload helper (optional)

```bash
python scripts/sync_and_reload.py \
  --source /path/to/source/addon \
  --target "/path/to/blender/addons/my_addon" \
  --module my_addon \
  --dry-run
```

## Development notes

- For WSL + Windows Blender, prefer direct writes to `/mnt/c/.../scripts/addons` when available.
- Keep module side effects in module `register()`/`unregister()` and let `auto_load.py` handle class registration order.
