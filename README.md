[简体中文](./docs/README_zh.md) | English

# Blender MCP Integrated and Skills

```mermaid
flowchart LR
    Agent[MCP client] -->|Authenticated local HTTP| Server[Bundled MCP service]
    Server -->|Authenticated TCP| Bridge[Blender Extension bridge]
    Bridge --> Scene[Blender scene]
```

This repository integrates [Blender Lab's official MCP](https://projects.blender.org/lab/blender_mcp) and provides:

1. **An integrated Extension for Windows x64, Linux x64 and macOS Apple Silicon** with the official bridge, MCP tools, documentation, and locked dependencies
2. **A matching practical skill package** (`blender-mcp-skills`) with templates and development guidance

Blender manages an independent authenticated local HTTP service. Install the ZIP, select your agent, and copy its connection configuration. See [build instructions](docs/integration-build.md) and [validation](docs/integration-validation.md). Both release lines require bundled CPython 3.13; Blender 5.0 uses Python 3.11 and is incompatible. The generic template targets Blender 4.2+.

| Blender | Release and fixed official source | Extensions index |
| --- | --- | --- |
| 5.1.0 ≤ version < 5.2.0 | [Stable 1.0.3+integration.1](https://github.com/psiQAQ/blender_mcp-setup-guide/releases/tag/v1.0.3%2Bintegration.1), official v1.0.3 | [5.1 stable](https://notes.psiqaq.cn/blender_mcp-setup-guide/index.json) |
| 5.2.0 ≤ version < 5.3.0 | [Preview 1.0.2-dev.1+integration.1](https://github.com/psiQAQ/blender_mcp-setup-guide/releases/tag/v1.0.2-dev.1%2Bintegration.1), official main snapshot `dbbf836ad4b1025f14a2b3b504c43903f39e0b04` | [5.2 preview](https://notes.psiqaq.cn/blender_mcp-setup-guide/blender-5.2/preview/index.json) |

Each line provides Windows x64, Linux x64 and macOS Apple Silicon packages. The 5.2 preview is a GitHub Pre-release. `main` and `release/blender-5.2` follow the reviewed snapshot; `release/blender-5.1` maintains the 5.1 stable line. Promotion to 5.2 stable requires a new official stable tag, complete native validation and manual publication.

## Choose an installation method

| Method | Suitable environment | Installation and connection | Guide |
| --- | --- | --- | --- |
| Integrated Extension | Native Windows x64 / Linux x64 / macOS ARM64, Blender 5.1 stable or 5.2 preview / CPython 3.13; client and Blender on one computer | Install a bundled ZIP, copy Bearer-authenticated local HTTP settings; no separate uv/Python for users | [English](docs/blender_mcp-setup_en.md) / [中文](docs/blender_mcp-setup_zh.md) |
| Official Extension + stdio | Officially supported Windows/macOS/Linux environments, Blender 5.1+ | Install the official Extension plus Git/uv and an external MCP tool; the client manages its stdio process | [English](docs/blender_mcp-stdio-setup_en.md) / [中文](docs/blender_mcp-stdio-setup_zh.md) |

Each guide includes complete Codex, Claude Code and OpenCode settings, file locations, verification and removal steps. Choose one method for a Blender instance and replace its client entry when switching.

## Setup prompts

Integrated Extension:

```text
Follow https://raw.githubusercontent.com/psiQAQ/blender_mcp-setup-guide/main/docs/blender_mcp-setup_en.md. Check system, architecture and Blender compatibility, install the integrated Extension, configure my MCP client and verify an actual scene read.
```

Official stdio:

```text
Follow https://raw.githubusercontent.com/psiQAQ/blender_mcp-setup-guide/main/docs/blender_mcp-stdio-setup_en.md. Install the official Extension and pinned MCP tool, configure my client for stdio and verify an actual scene read.
```

## Skill capabilities (brief)

`blender-mcp-skills` focuses on:

- Extension-only scaffold workflow for Blender 4.2+
- Explicit class registration, failure rollback, and reverse cleanup
- Manifest wheels for required dependencies and Extension user directories for writable data
- Offline template generation and static checks; runtime discovery for live Blender operations
- Validation/build scripting guidance (`validate_extension.py`, `build_extension.py`)
- Cross-system runtime adaptation hints (WSL/Linux/Windows path strategy)

## Tutorials

- Integrated Extension: [English](docs/blender_mcp-setup_en.md) / [中文](docs/blender_mcp-setup_zh.md)
- Official stdio: [English](docs/blender_mcp-stdio-setup_en.md) / [中文](docs/blender_mcp-stdio-setup_zh.md)
- Integration architecture: [`docs/integration-design.md`](docs/integration-design.md)
- Build and release: [`docs/integration-build.md`](docs/integration-build.md)
- Chinese repository overview: [`docs/README_zh.md`](docs/README_zh.md)

## Install the local skill

- Skill path: `.agents/skills/blender-mcp-skills/`
- Skill name: `blender-mcp-skills`

```bash
npx skills add https://github.com/psiQAQ/blender_mcp-setup-guide
```

## Repository structure (expanded for skill)

| Path | Purpose |
| --- | --- |
| `src/blender_mcp_integration/` | Extension UI and isolated service lifecycle |
| `packaging/` | Pinned upstream, Blender toolchain and dependency inputs |
| `scripts/` | Scaffold, build, test and release preparation |
| `.github/workflows/` | CI, manually triggered release and upstream inspection |
| `.agents/skills/blender-mcp-skills/` | Skill, reference docs and generic template |
| `tests/` | Unit checks and actual Blender hosts |
| `docs/` | Setup, design and validation evidence |
| `submodules/` | Reference implementations |

## Extension dependency policy

The default template has no third-party dependencies. When a feature needs them:

- Bundle required dependencies as `wheels = [...]` in `blender_manifest.toml`.
- Store writable data with `bpy.utils.extension_path_user(...)`.
- Load the integration's prebuilt MCP dependencies only in its independent `-I -S -B` Python process.
- Keep package data, native libraries, and dependency licenses in the final ZIP.
- Heavy scientific or GPU workloads can use an external service with a defined interface.

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

Repository and integration code use **GPL-3.0-or-later**. See [`LICENSE`](LICENSE). The package preserves official upstream copyright notices and bundled dependency licenses.
