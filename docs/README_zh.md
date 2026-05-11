简体中文 | [English](../README.md)

# Blender MCP Skills Toolkit（中文版）

![Claude Code + Blender MCP 架构图](../assets/imgs/claude-code-mcp-blender.png)

这是一个围绕 **Blender MCP** 的技能与模板仓库，目标是让你更快完成：

- Claude Code + Blender MCP 本地/远端连接配置
- Blender Extension（4.2+）模板复用
- Extension 校验、打包与重载脚本化

## 教程入口

- 本地单机教程（中文）：[`blender_mcp-setup_zh.md`](./blender_mcp-setup_zh.md)
- 本地单机教程（English）：[`blender_mcp-setup_en.md`](./blender_mcp-setup_en.md)
- 远端局域网教程（中文）：[`blender_mcp-remote_zh.md`](./blender_mcp-remote_zh.md)
- 远端局域网教程（English）：[`blender_mcp-remote.md`](./blender_mcp-remote.md)

## 一键可复制提示词（示例）

```text
请基于 .claude/skills/blender-mcp-skills/templates/extension_addon 创建一个 Blender 4.2+ extension-only 插件骨架，
要求使用 auto_load 拓扑注册，按 operators/panels/utils 结构拆分，
并用 scripts/validate_extension.py + scripts/build_extension.py 完成校验和构建。
```

## Skills 安装

- 本仓库技能路径：`./.claude/skills/blender-mcp-skills/`
- 技能名：`blender-mcp-skills`

```bash
npx skills add ./.claude/skills/blender-mcp-skills
```

## 目录结构（摘要）

```text
blender_mcp/
├─ README.md                                # 根目录英文版总览
├─ LICENSE                                  # GNU GPL v2 许可证文本
├─ assets/
│  └─ imgs/
├─ docs/
│  ├─ README_zh.md                          # 本文件（中文总览）
│  ├─ blender_mcp-setup_zh.md               # 本地教程（中文）
│  ├─ blender_mcp-setup_en.md               # 本地教程（英文）
│  ├─ blender_mcp-remote_zh.md              # 远端教程（中文）
│  └─ blender_mcp-remote.md                 # 远端教程（英文）
├─ .claude/skills/blender-mcp-skills/       # 技能与模板
└─ submodules/                              # 外部参考项目（git submodule）
```

## 触发示例（给 Claude）

- “帮我按 `blender-mcp-skills` 模板创建一个新的 extension-only 插件。”
- “把这个旧 `bl_info` 插件迁移到 Blender 4.2+ extension 结构。”
- “用 MCP 发现 Blender 路径，然后做 validate + build。”

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
