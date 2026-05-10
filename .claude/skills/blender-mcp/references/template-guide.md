# Template Guide

## Built-in template

Use this local template:

- `.claude/skills/blender-mcp/templates/extension_addon/` (`auto_load` topology registration)

Compatibility target:

- Blender **4.2+** (Extension system)

## Mandatory pre-step: system adaptation

Before running Blender commands or editing add-on files, read:

- `./system-adaptation.md`

Always detect both runtime systems first:

1. Agent runtime system
2. Blender runtime system

Then choose the file and path strategy for:

- same-system runtime
- cross-system runtime (including WSL to Windows `/mnt/c/...` mapping when applicable)

## Template structure

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

## Why this structure

- `blender_manifest.toml`: extension metadata and compatibility.
- `__init__.py + auto_load.py`: topology-based orchestration for dependency-safe class registration.
- `_properties.py`: PropertyGroup and scene pointer property side effects.
- `_operators.py`: executable actions.
- `_panels.py`: UI layout.
- `_preferences.py`: add-on settings entry point.
- `scripts/*`: preflight, build wrappers, and optional sync helper.

## Recommended usage flow

1. Copy template to target add-on folder.
2. Update manifest fields (`id`, `name`, `maintainer`, `version`).
3. Rename example classes and operator IDs.
4. Reload add-on and verify panel/operator/property behavior.

## Build extension package

Run in the add-on root directory:

```bash
blender --command extension build
```
