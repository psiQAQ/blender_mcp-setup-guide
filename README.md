[简体中文](./docs/README_zh.md) | English

# Blender MCP Skills Toolkit

![Claude Code + Blender MCP 架构图](assets/imgs/claude-code-mcp-blender.png)

This repository provides two things together:

1. **Official Blender MCP installation tutorials** (local and remote)
2. **A matching practical skill package** (`blender-mcp-skills`) with templates and development guidance

It is designed to let agents install first, then build extension workflows consistently.

## One-line prompt for agent to install the official Blender MCP

```text
Follow https://raw.githubusercontent.com/psiQAQ/blender_mcp-setup-guide/main/docs/blender_mcp-setup_en.md to install the official Blender MCP (Blender Add-on + blender-mcp server), register it with Claude Code, and verify the connection end-to-end.
```

## Skill capabilities (brief)

`blender-mcp-skills` focuses on:

- Extension-only scaffold workflow for Blender 4.2+
- Autoload-based module topology (`operators/panels/utils`)
- Validation/build scripting guidance (`validate_extension.py`, `build_extension.py`)
- Cross-system runtime adaptation hints (WSL/Linux/Windows path strategy)

## Tutorials

- Local setup (English): [`docs/blender_mcp-setup_en.md`](docs/blender_mcp-setup_en.md)
- Local setup (中文): [`docs/blender_mcp-setup_zh.md`](docs/blender_mcp-setup_zh.md)
- Remote/LAN setup (English): [`docs/blender_mcp-remote.md`](docs/blender_mcp-remote.md)
- Remote/LAN setup (中文): [`docs/blender_mcp-remote_zh.md`](docs/blender_mcp-remote_zh.md)
- Chinese repository overview: [`docs/README_zh.md`](docs/README_zh.md)

## Install the local skill

- Skill path: `.claude/skills/blender-mcp-skills/`
- Skill name: `blender-mcp-skills`

```bash
npx skills add ./.claude/skills/blender-mcp-skills
```

## Repository structure (expanded for skill)

```text
blender_mcp/
├─ README.md
├─ LICENSE
├─ assets/
│  └─ imgs/
├─ docs/
│  ├─ README_zh.md
│  ├─ blender_mcp-setup_en.md
│  ├─ blender_mcp-setup_zh.md
│  ├─ blender_mcp-remote.md
│  └─ blender_mcp-remote_zh.md
├─ .claude/
│  └─ skills/
│     └─ blender-mcp-skills/
│        ├─ SKILL.md
│        ├─ references/
│        │  ├─ index.md
│        │  ├─ template-guide.md
│        │  ├─ extension-workflow.md
│        │  ├─ extension-install.md
│        │  ├─ lifecycle.md
│        │  ├─ system-adaptation.md
│        │  ├─ pitfalls-and-fixes.md
│        │  ├─ migration-notes.md
│        │  └─ manifest-fields.md
│        └─ templates/
│           └─ extension_addon/
│              ├─ operators/ panels/ utils/
│              └─ scripts/
└─ submodules/
```

## Prompt example (natural trigger)

```text
I want to build a Blender add-on for [your idea].
Please use blender-mcp-skills to drive the full workflow and deliver a releasable extension package.
```

## TODO (next features)

- Add more production-grade extension templates (by complexity)
- Add stricter automated validation recipes
- Add more migration playbooks from legacy add-ons
- Add richer agent-facing prompt snippets for common tasks

## Acknowledgements

This repository includes references to community projects via git submodules:

- clean-blender-addon-template
- blender-addon-template
- BlenderAddonPackageTool
- blender_vscode
- AdvancedBlenderAddon
- blender-extension-template
- BlenderTemplate

## License

This project is distributed under **GNU GPL v2**. See [`LICENSE`](LICENSE).
