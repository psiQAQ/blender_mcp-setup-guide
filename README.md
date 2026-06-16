[简体中文](./docs/README_zh.md) | English

# Blender MCP Skills Toolkit

![Agent + Blender MCP Architecture](assets/imgs/claude-code-mcp-blender.png)

This repository provides two things together:

1. **Official Blender MCP installation tutorials** (local and remote)
2. **A matching practical skill package** (`blender-mcp-skills`) with templates and development guidance

It is designed to let agents install first, then build extension workflows consistently.

## One-line prompt for agent to install the official Blender MCP

```text
Follow https://raw.githubusercontent.com/psiQAQ/blender_mcp-setup-guide/main/docs/blender_mcp-setup_en.md to install the official Blender MCP (Blender Add-on + blender-mcp server), register it with your agent, and verify the connection end-to-end.
```

The same setup pattern also works for other agents. Use each agent's MCP configuration format.

The installation guides include an OpenCode example that directly adds a `blender` MCP server entry to `~/.config/opencode/opencode.json` (Linux/macOS) or `%USERPROFILE%\\.config\\opencode\\opencode.json` (Windows).
They also include a Codex example that adds the same server to `.codex/config.toml`.

## Skill capabilities (brief)

`blender-mcp-skills` focuses on:

- Extension-only scaffold workflow for Blender 4.2+
- Autoload-based module topology (`operators/panels/utils`)
- Extension-private Python dependency management (`deps/site-packages` + `pip --target`)
- Add-on Preferences dependency status UI and explicit user-triggered installs
- Validation/build scripting guidance (`validate_extension.py`, `build_extension.py`)
- Cross-system runtime adaptation hints (WSL/Linux/Windows path strategy)

## Tutorials

- Local setup (English): [`docs/blender_mcp-setup_en.md`](docs/blender_mcp-setup_en.md)
- Local setup (中文): [`docs/blender_mcp-setup_zh.md`](docs/blender_mcp-setup_zh.md)
- Remote/LAN setup (English): [`docs/blender_mcp-remote.md`](docs/blender_mcp-remote.md)
- Remote/LAN setup (中文): [`docs/blender_mcp-remote_zh.md`](docs/blender_mcp-remote_zh.md)
- Chinese repository overview: [`docs/README_zh.md`](docs/README_zh.md)

## Install the local skill

- Skill path: `.agents/skills/blender-mcp-skills/`
- Skill name: `blender-mcp-skills`

```bash
npx skills add ./.agents/skills/blender-mcp-skills
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
├─ .agents/
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
│        │  ├─ dependency-policy.md
│        │  ├─ pitfalls-and-fixes.md
│        │  ├─ migration-notes.md
│        │  └─ manifest-fields.md
│        └─ templates/
│           └─ extension_addon/
│              ├─ operators/ panels/ utils/
│              ├─ utils/dependency_manager.py
│              └─ scripts/
├─ tests/
│  └─ test_validate_extension.py
└─ submodules/
```

## Extension dependency policy

The built-in extension template supports private Python dependencies for development and internal tools:

- Dependencies are declared in `utils/dependency_manager.py`.
- Missing packages are installed only after the user clicks **Install Missing Dependencies** in Add-on Preferences.
- Installs use Blender's Python with `pip install --target deps/site-packages`, so Blender's bundled global `site-packages` is not modified.
- The private dependency path is added during add-on registration and removed during unregistration.
- The default installer uses the Tsinghua PyPI mirror, with a Preferences toggle to disable it.
- Release builds should prefer `wheels = [...]` in `blender_manifest.toml`; heavy packages such as `torch`, `opencv-python`, `scipy`, `open3d`, or CUDA stacks should usually live in an external Python environment.

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
