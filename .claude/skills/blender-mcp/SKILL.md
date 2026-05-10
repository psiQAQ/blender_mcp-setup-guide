---
name: blender-mcp
description: Use when users need Blender MCP plugin or extension workflows, especially creating scaffolds/templates/new add-ons, handling register/unregister/reload behavior, or adapting file and command operations across different runtime systems.
type: skills
---

# Blender MCP — Plugin and Extension Development

This skill provides a reliable workflow for Blender extension add-on development through Blender MCP.

## When to trigger this skill

Trigger this skill whenever users ask to:

- create plugin scaffolding
- create a template
- create a new add-on
- create a new extension add-on
- migrate legacy add-on structure to extension structure
- debug register/unregister/reload lifecycle issues

## First questions to ask

Before implementation, ask:

1. What is the minimum Blender version target?
   - Default recommendation: 4.2+
2. Is extension-only delivery acceptable?
   - Default: yes, extension-only

## Built-in template policy

- Keep one local template:
  - `.claude/skills/blender-mcp/templates/extension_addon/`
- Registration strategy is autoload-only (`auto_load.py` topology registration).
- Keep template source code in template directories.
- Do not inline full template source code inside `SKILL.md`.

## System operation rule (mandatory)

Before running Blender commands or touching add-on files, read:

- `.claude/skills/blender-mcp/references/system-adaptation.md`

That document defines:

- how to detect the agent runtime system
- how to detect the Blender runtime system
- how to choose same-system vs cross-system path strategy
- how to handle WSL-mounted Windows paths (such as `/mnt/c/...`) when applicable

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

- Index: `.claude/skills/blender-mcp/references/index.md`
- System adaptation: `.claude/skills/blender-mcp/references/system-adaptation.md`
- Extension workflow: `.claude/skills/blender-mcp/references/extension-workflow.md`
- Lifecycle: `.claude/skills/blender-mcp/references/lifecycle.md`
- Pitfalls and fixes: `.claude/skills/blender-mcp/references/pitfalls-and-fixes.md`
- Template guide: `.claude/skills/blender-mcp/references/template-guide.md`
- Migration notes: `.claude/skills/blender-mcp/references/migration-notes.md`
