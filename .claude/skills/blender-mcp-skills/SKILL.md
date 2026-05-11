---
name: blender-mcp-skills
description: Use when users need Blender MCP setup or extension workflows, including installing official blender-mcp/add-on, fixing missing MCP connections, creating extension templates, or handling register/unregister/reload behavior across different runtime systems.
type: skills
---

# Blender MCP — Plugin and Extension Development

This skill provides a reliable workflow for Blender extension add-on development through Blender MCP.

## When to trigger this skill

Trigger this skill whenever users ask to:

- install official Blender MCP (Blender Add-on + blender-mcp server)
- fix missing blender-mcp command or missing Claude MCP connection
- create plugin scaffolding
- create a template
- create a new add-on
- create a new extension add-on
- migrate legacy add-on structure to extension structure
- debug register/unregister/reload lifecycle issues

## Official Blender MCP install gate (mandatory)

Before extension development, always run a readiness check:

1. `blender-mcp --help` must run successfully.
2. `claude mcp list` must show a configured Blender MCP server entry.

If either check fails, stop development tasks and run official installation first.

Official tutorial (raw URL):

- Local setup (EN): `https://raw.githubusercontent.com/psiQAQ/blender_mcp-setup-guide/main/docs/blender_mcp-setup_en.md`

After installation, re-run the two checks above. Only continue add-on development after both pass.

## First questions to ask

Before implementation, ask:

1. What is the minimum Blender version target?
   - Default recommendation: 4.2+
2. Is extension-only delivery acceptable?
   - Default: yes, extension-only

## Built-in template policy

- Keep one local template:
  - `.claude/skills/blender-mcp-skills/templates/extension_addon/`
- Registration strategy is autoload-only (`auto_load.py` topology registration).
- Keep template source code in template directories.
- Do not inline full template source code inside `SKILL.md`.

## System operation rule (mandatory)

Before running Blender commands or touching add-on files, read:

- `.claude/skills/blender-mcp-skills/references/system-adaptation.md`

That document defines:

- how to detect the agent runtime system
- how to detect the Blender runtime system
- how to choose same-system vs cross-system path strategy
- how to handle WSL-mounted Windows paths (such as `/mnt/c/...`) when applicable

For build operations, always query runtime facts through MCP first and validate before execution:

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

## Minimal reload commands

```python
bpy.ops.preferences.addon_disable(module="your_module")
bpy.ops.preferences.addon_enable(module="your_module")
```

Use module name (not display name).

## Safety rules

1. Prefer `try/except ValueError` for class registration safety.
2. Prefer `try/except (ValueError, RuntimeError)` for class unregistration safety.
3. Check `hasattr(bpy.types.Scene, "...")` before deleting scene properties.
4. Clear submodule cache in `sys.modules` before re-import when reloading.
5. Validate unregister state through `bpy.types` and preferences map, not only `bpy.ops` proxy checks.

## Reference navigation

- Index: `.claude/skills/blender-mcp-skills/references/index.md`
- System adaptation: `.claude/skills/blender-mcp-skills/references/system-adaptation.md`
- Extension workflow: `.claude/skills/blender-mcp-skills/references/extension-workflow.md`
- Lifecycle: `.claude/skills/blender-mcp-skills/references/lifecycle.md`
- Pitfalls and fixes: `.claude/skills/blender-mcp-skills/references/pitfalls-and-fixes.md`
- Template guide: `.claude/skills/blender-mcp-skills/references/template-guide.md`
- Manifest fields: `.claude/skills/blender-mcp-skills/references/manifest-fields.md`
- Migration notes: `.claude/skills/blender-mcp-skills/references/migration-notes.md`
