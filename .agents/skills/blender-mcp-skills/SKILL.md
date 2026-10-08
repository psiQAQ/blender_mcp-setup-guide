---
name: blender-mcp-skills
description: Use when users need Blender MCP setup or extension workflows, including installing blender-mcp server + Blender MCP add-on components, fixing missing MCP connections, creating extension templates, or handling register/unregister/reload behavior across different runtime systems.
type: skills
---

# Blender MCP — Plugin and Extension Development

This skill provides a reliable workflow for Blender extension add-on development through Blender MCP.

## When to trigger this skill

Trigger this skill whenever users ask to:

- install Blender MCP components (Blender Add-on + blender-mcp server)
- fix missing blender-mcp command or missing agent-side MCP connection
- create plugin scaffolding
- create a template
- create a new add-on
- create a new extension add-on
- migrate legacy add-on structure to extension structure
- debug register/unregister/reload lifecycle issues
- manage private Python dependencies for Blender extensions

## Route by operation

Template generation and static checks work offline. Before operating a live Blender through MCP, run one query and fetch these fields together:

   - Blender version (`bpy.app.version_string` or `bpy.app.version`)
   - Blender executable path (`bpy.app.binary_path`)
   - Runtime system (`platform.system()`)

If the target Blender version is lower than 4.2, explain that the default template requires the Extension system in 4.2+.

If version is 4.2 or newer, continue. Prefer testing on the user's active Blender version rather than forcing a fixed 5.1+ baseline.

For isolated local builds and tests, an explicitly selected Blender executable supplies the runtime facts without requiring a live MCP connection. The integrated MCP product has its own compatibility range in its manifest.

Setup guide source note:

- This guide is maintained by this repository (not official Blender documentation).
- Its goal is to install official Blender MCP components correctly.

Setup guide (raw URL):

- Local setup (EN): `https://raw.githubusercontent.com/psiQAQ/blender_mcp-setup-guide/main/docs/blender_mcp-setup_en.md`

After MCP installation, verify an actual client session and scene-reading tool call.

## First questions to ask

Before implementation, ask:

1. What is the minimum Blender version target?
   - Default recommendation: 4.2+
2. Is extension-only delivery acceptable?
   - Default: yes, extension-only

## Extension install rule (critical)

For extension-only delivery, do not deploy source folders to legacy add-on paths.

Use extension-native flow only:

1. Build zip from extension root.
   - Default output location: parent directory of the extension source folder.
2. Install zip into extension repo (prefer `user_default`).
3. Verify enabled key format `bl_ext.<repo_module>.<extension_id>`.
4. Ensure zip path is readable by Blender host system (especially cross-system cases).

Detailed install steps and examples:

- `references/extension-install.md`
- `references/system-adaptation.md`

## Built-in template policy

- Keep one local template:
  - `templates/extension_addon/`
- Registration uses explicit class lists, rollback on failure, and reverse cleanup. Consider dependency-aware autoload only when a larger project's class relationships justify it.
- Keep template source code in template directories.
- Do not inline full template source code inside `SKILL.md`.

## Python dependency policy (mandatory)

Read `references/dependency-policy.md` before adding third-party Python packages to an extension.

- Bundle required dependencies as manifest wheels; import them directly.
- Keep the default template free of third-party dependencies and runtime installers.
- Optional capabilities report missing packages when invoked.
- Store writable data with `bpy.utils.extension_path_user(...)`.
- Internet operations respect `bpy.app.online_access` and declared permissions.
- The integrated MCP service loads prebuilt dependencies only in its independent Python process.
- Recommend an external Python environment for heavy dependencies such as `torch`, `opencv-python`, `scipy`, `open3d`, and CUDA packages.

## System operation rule (mandatory)

Before running Blender commands or touching add-on files, read:

- `references/system-adaptation.md`

That document defines:

- how to detect the agent runtime system
- how to detect the Blender runtime system
- how to choose same-system vs cross-system path strategy
- how to handle WSL-mounted Windows paths (such as `/mnt/c/...`) when applicable

For build operations, obtain and validate these facts through MCP or the explicitly selected local Blender:

- Blender executable location (`bpy.app.binary_path`)
- Blender bundled Python (`bpy.app.binary_path_python` when available)
- Blender runtime system (`platform.system()` in Blender)
- Extension root containing `blender_manifest.toml` (must match the local build target)

## Python environment priority for template scripts

When running template scripts for checks, tests, and build, use this interpreter priority:

1. User-specified extension development Python environment
2. Project virtual environment (`.venv`)
3. Blender bundled Python (from MCP-discovered `bpy.app.binary_path_python`)
4. System Python available in PATH

## Path reference rule

All internal paths in this skill are relative to the directory containing this `SKILL.md`.

Do not hard-code agent-specific roots such as:

- `agent-root/skills/<skill-name>/`
- `.agents/skills/<skill-name>/`
- `.opencode/skills/<skill-name>/`

Use relative paths instead:

- `references/system-adaptation.md`
- `references/extension-install.md`
- `templates/extension_addon/`

## Minimal reload commands

```python
bpy.ops.preferences.addon_disable(module="your_module")
bpy.ops.preferences.addon_enable(module="your_module")
```

Use module name (not display name).

## Safety rules

1. Record successful class registrations, roll them back on failure, and re-raise the original error.
2. Unregister owned properties and classes in reverse order; report cleanup failures.
3. Check `hasattr(bpy.types.Scene, "...")` before deleting scene properties.
4. Disable first, then clear only the target package's submodules before re-import when source reload is needed.
5. Validate unregister state through `bpy.types` and preferences map, not only `bpy.ops` proxy checks.

## Reference navigation

- Index: `references/index.md`
- System adaptation: `references/system-adaptation.md`
- Extension workflow: `references/extension-workflow.md`
- Dependency policy: `references/dependency-policy.md`
- Extension install: `references/extension-install.md`
- Lifecycle: `references/lifecycle.md`
- Pitfalls and fixes: `references/pitfalls-and-fixes.md`
- Template guide: `references/template-guide.md`
- Manifest fields: `references/manifest-fields.md`
- Migration notes: `references/migration-notes.md`
