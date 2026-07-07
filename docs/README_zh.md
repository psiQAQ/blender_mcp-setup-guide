简体中文 | [English](../README.md)

# Blender MCP Skills Toolkit（中文版）

![Agent + Blender MCP 架构图](../assets/imgs/claude-code-mcp-blender.png)

本仓库同时提供两部分内容：

1. **官方 Blender MCP 安装教程**（本地/远端）
2. **与教程配套的 skill 包**（`blender-mcp-skills`，含模板与开发指导）

目标是先安装打通，再稳定复用 extension 开发流程，并持续扩展更多能力。

## 给 Agent 的一句话安装 Blender 官方 MCP 的提示词

```text
请严格按 https://raw.githubusercontent.com/psiQAQ/blender_mcp-setup-guide/main/docs/blender_mcp-setup_zh.md 完成官方 Blender MCP 安装（Blender Add-on + blender-mcp server），并在你的 agent 中完成注册与连通性验证。
```

同一套安装思路也支持其他 agent。请按各家 agent 的 MCP 配置格式进行接入。

安装教程中已提供 OpenCode 示例：可直接向 `~/.config/opencode/opencode.json`（Linux/macOS）或 `%USERPROFILE%\\.config\\opencode\\opencode.json`（Windows）添加 `blender` 的 MCP 配置。
也提供了 Codex 示例：可通过向 `.codex/config.toml` 添加配置接入同一个 MCP Server。

## Skills 能力（简述）

`blender-mcp-skills` 主要覆盖：

- Blender 4.2+ extension-only 脚手架流程
- autoload 拓扑注册与 `operators/panels/utils` 结构拆分
- 插件私有 Python 依赖管理（`deps/site-packages` + `pip --target`）
- Add-on Preferences 依赖状态展示与用户显式点击安装
- 校验/构建脚本实践（`validate_extension.py`、`build_extension.py`）
- 跨系统运行适配提示（WSL/Linux/Windows 路径策略）

## 教程入口

- 本地单机教程（中文）：[`blender_mcp-setup_zh.md`](./blender_mcp-setup_zh.md)
- 本地单机教程（English）：[`blender_mcp-setup_en.md`](./blender_mcp-setup_en.md)
- 远端局域网教程（中文）：[`blender_mcp-remote_zh.md`](./blender_mcp-remote_zh.md)
- 远端局域网教程（English）：[`blender_mcp-remote.md`](./blender_mcp-remote.md)

## Skills 安装

- 本仓库技能路径：`./.agents/skills/blender-mcp-skills/`
- 技能名：`blender-mcp-skills`

```bash
npx skills add https://github.com/psiQAQ/blender_mcp-setup-guide
```

## 目录结构（按 skill 展开）

```text
blender_mcp/
├─ README.md                                # 根目录英文总览
├─ LICENSE
├─ assets/
│  └─ imgs/
├─ docs/
│  ├─ README_zh.md                          # 本文件（中文总览）
│  ├─ blender_mcp-setup_zh.md               # 本地教程（中文）
│  ├─ blender_mcp-setup_en.md               # 本地教程（英文）
│  ├─ blender_mcp-remote_zh.md              # 远端教程（中文）
│  └─ blender_mcp-remote.md                 # 远端教程（英文）
├─ .agents/skills/blender-mcp-skills/
│  ├─ SKILL.md                              # 技能入口
│  ├─ references/                           # 开发思路与规范指导
│  │  ├─ index.md / template-guide.md
│  │  ├─ extension-workflow.md / extension-install.md / lifecycle.md
│  │  ├─ system-adaptation.md / dependency-policy.md / pitfalls-and-fixes.md
│  │  └─ migration-notes.md / manifest-fields.md
│  └─ templates/extension_addon/
│     ├─ operators/ panels/ utils/
│     ├─ utils/dependency_manager.py
│     └─ scripts/
├─ tests/
│  └─ test_validate_extension.py
└─ submodules/                              # 外部参考项目（git submodule）
```

## Extension 依赖策略

内置 extension 模板支持开发期和内部工具场景的插件私有 Python 依赖：

- 依赖声明集中放在 `utils/dependency_manager.py`。
- 缺失依赖只会在用户于 Add-on Preferences 中点击 **Install Missing Dependencies** 后安装。
- 安装命令使用 Blender Python 执行 `pip install --target deps/site-packages`，不会写入 Blender 自带 Python 的全局 `site-packages`。
- 插件注册时加入私有依赖路径，注销时从 `sys.path` 移除。
- 默认使用清华 PyPI 镜像，并在 Preferences 中提供关闭选项。
- 正式发布优先使用 `blender_manifest.toml` 的 `wheels = [...]`；`torch`、`opencv-python`、`scipy`、`open3d`、CUDA 栈等重型依赖通常应放在外部 Python 环境中。

## 提示词示例（自然触发）

```text
我想做一个 Blender 插件来实现 [你的需求]。
请使用 blender-mcp-skills 驱动完整流程，并交付可发布的 extension 包。
```

## TODO（后续能力）

- 增加按复杂度分层的模板
- 增加更严格的自动化校验流程
- 补充 legacy 到 extension 的迁移案例库
- 增加常见任务的一句话提示词集合

## 鸣谢

感谢以下开源项目提供实践与参考：

- `clean-blender-addon-template`
- `blender-addon-template`
- `BlenderAddonPackageTool`
- `blender_vscode`
- `AdvancedBlenderAddon`
- `blender-extension-template`
- `BlenderTemplate`

## 开源许可

本仓库默认采用 **GNU GPL v2**（见 [`../LICENSE`](../LICENSE)）。
