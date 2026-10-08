简体中文 | [English](../README.md)

# Blender MCP 集成安装与开发技能

```mermaid
flowchart LR
    Agent[MCP 客户端] -->|本机 HTTP + 凭据| Server[随包 MCP 服务]
    Server -->|本机 TCP + 凭据| Bridge[Blender Extension 桥接]
    Bridge --> Scene[Blender 场景]
```

本仓库同时提供两部分内容：

1. **Windows x64、Linux x64、macOS Apple Silicon 集成 Extension**，随包交付 Blender Lab 官方桥接端、MCP 工具、文档与锁定依赖
2. **与教程配套的 skill 包**（`blender-mcp-skills`，含模板与开发指导）

安装 ZIP 后选择 agent 并复制连接配置；Blender 管理独立的本机 HTTP 服务。集成包最低要求 Blender 5.1 / CPython 3.13，首版支持 5.1.0 ≤ Blender < 5.2.0。Blender 5.0 使用 Python 3.11，不适用本集成包。按平台下载 [Release 安装包](https://github.com/psiQAQ/blender_mcp-setup-guide/releases)，或添加 [Extensions 索引](https://psiQAQ.github.io/blender_mcp-setup-guide/index.json)。通用插件模板支持 Blender 4.2+。构建和验收见[构建说明](integration-build.md)与[验证记录](integration-validation.md)。

## 选择安装方式

| 方式 | 适用环境 | 安装与连接方式 | 教程 |
| --- | --- | --- | --- |
| 集成 Extension | 原生 Windows x64 / Linux x64 / macOS ARM64、Blender 5.1.x / CPython 3.13，客户端与 Blender 同机 | 安装随包 ZIP，复制带凭据的本机 HTTP 配置；用户无需另外安装 uv/Python | [中文](blender_mcp-setup_zh.md) / [English](blender_mcp-setup_en.md) |
| 官方 Extension + stdio | 官方支持的 Windows/macOS/Linux 环境、Blender 5.1+ | 安装官方 Extension、Git/uv 和外部 MCP 工具，由客户端管理 stdio 进程 | [中文](blender_mcp-stdio-setup_zh.md) / [English](blender_mcp-stdio-setup_en.md) |

两份教程均提供 Codex、Claude Code、OpenCode 的完整配置、文件位置、验证和移除步骤。同一个 Blender 实例选择一种方式；切换时替换客户端的对应条目。

## 给 Agent 的安装提示词

集成 Extension：

```text
请按 https://raw.githubusercontent.com/psiQAQ/blender_mcp-setup-guide/main/docs/blender_mcp-setup_zh.md 操作。核对系统、架构与 Blender 兼容性，安装集成 Extension，配置我使用的 MCP 客户端，并实际读取场景验证连接。
```

官方 stdio：

```text
请按 https://raw.githubusercontent.com/psiQAQ/blender_mcp-setup-guide/main/docs/blender_mcp-stdio-setup_zh.md 操作。安装官方 Extension 和固定来源的 MCP 工具，为我使用的客户端配置 stdio，并实际读取场景验证连接。
```

## Skills 能力（简述）

`blender-mcp-skills` 主要覆盖：

- Blender 4.2+ extension-only 脚手架流程
- 显式类注册、失败回滚与逆序卸载
- 必需依赖使用 manifest wheels，用户数据写入 Extension 用户目录
- 静态开发离线完成，操作 Blender 时再查询目标运行环境
- 校验/构建脚本实践（`validate_extension.py`、`build_extension.py`）
- 跨系统运行适配提示（WSL/Linux/Windows 路径策略）

## 教程入口

- 集成 Extension：[中文](blender_mcp-setup_zh.md) / [English](blender_mcp-setup_en.md)
- 官方 stdio：[中文](blender_mcp-stdio-setup_zh.md) / [English](blender_mcp-stdio-setup_en.md)
- 集成架构：[`integration-design.md`](integration-design.md)
- 构建与发布：[`integration-build.md`](integration-build.md)

## Skills 安装

- 本仓库技能路径：`./.agents/skills/blender-mcp-skills/`
- 技能名：`blender-mcp-skills`

```bash
npx skills add https://github.com/psiQAQ/blender_mcp-setup-guide
```

## 目录结构（按 skill 展开）

| 路径 | 用途 |
| --- | --- |
| `src/blender_mcp_integration/` | Extension 界面与独立服务生命周期 |
| `packaging/` | 固定上游、Blender 工具链和依赖输入 |
| `scripts/` | 生成、构建、测试及发布准备 |
| `.github/workflows/` | CI、手动触发发布与上游检查 |
| `.agents/skills/blender-mcp-skills/` | 技能、参考说明与通用模板 |
| `tests/` | 单元检查和真实 Blender 验证入口 |
| `docs/` | 安装、设计和验收证据 |
| `submodules/` | 参考实现 |

## Extension 依赖策略

默认模板不需要第三方依赖。需要扩展能力时遵守以下约定：

- 必需依赖使用 `blender_manifest.toml` 的 `wheels = [...]` 随包交付。
- 用户数据写入 `bpy.utils.extension_path_user(...)`。
- 集成产品只在独立的 `-I -S -B` Python 进程中加载 MCP 依赖。
- 包内保留依赖数据、原生库和许可证。
- 科学计算与 GPU 等重型能力可使用具有明确接口的外部服务。

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

本仓库与集成代码采用 **GPL-3.0-or-later**（见 [`../LICENSE`](../LICENSE)）；安装包保留官方版权声明和依赖许可证。
