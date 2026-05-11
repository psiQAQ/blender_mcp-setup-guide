[简体中文](./docs/README_zh.md) | English

# Blender MCP Skills Toolkit

![Claude Code + Blender MCP 架构图](assets/imgs/claude-code-mcp-blender.png)

A practical repository for building and operating Blender MCP workflows with Claude Code.

## What this repo provides

- Local and remote Blender MCP setup guides
- An extension-only Blender add-on template (Blender 4.2+)
- Python-based validation/build helpers for extension packaging

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

## Repository structure

```text
blender_mcp/
├─ README.md
├─ LICENSE
├─ assets/
├─ docs/
├─ .claude/skills/blender-mcp-skills/
└─ submodules/
```

## Prompt example

```text
Use .claude/skills/blender-mcp-skills/templates/extension_addon to scaffold a Blender 4.2+ extension-only add-on,
keep autoload topology registration, split modules into operators/panels/utils,
and run validate_extension.py + build_extension.py.
```

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
