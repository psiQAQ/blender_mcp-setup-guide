简体中文 | [English](./blender_mcp-setup_en.md)

# Blender MCP 集成 Extension 安装

适用于 **Windows x64、Linux x64、macOS Apple Silicon，以及 Blender 5.1.x（配套 CPython 3.13）**，客户端与 Blender 在同一台电脑运行。最低版本为 Blender 5.1.0，首版支持范围为 5.1.0 ≤ Blender < 5.2.0。Blender 5.0 内置 Python 3.11，不能使用本集成包。版本依据见 [Blender 5.0 官方源码](https://github.com/blender/blender/blob/v5.0.0/build_files/build_environment/cmake/versions.cmake)与 [5.1 发布说明](https://www.blender.org/download/releases/5-1/)。安装包包含 Blender Lab MCP v1.0.3、运行依赖和文档，使用 Blender 配套 Python，用户无需另外安装 uv 或 Python。

如果希望由客户端启动官方原版 MCP 进程，请使用另一份[官方 stdio 安装教程](blender_mcp-stdio-setup_zh.md)。两种方式的适用情况见[仓库首页](README_zh.md)。

```mermaid
flowchart LR
    Client[Codex / Claude Code / OpenCode] -->|本机 HTTP + Bearer token| Service[随包 MCP 服务]
    Service -->|本机 TCP 9876 + 桥接凭据| Blender[Blender Extension]
```

## 1. 获取并安装集成包

1. 获取与 Blender 版本匹配的 `blender_mcp_integration-1.0.3+integration.1-<platform>.zip`；`<platform>` 选择 `windows-x64`、`linux-x64` 或 `macos-arm64`。从 [Releases](https://github.com/psiQAQ/blender_mcp-setup-guide/releases) 下载；尚无对应发布时，按[构建说明](integration-build.md)构建，本地输出位于 `build/dist/`。
2. 打开 Blender，进入 **Edit → Preferences → Add-ons → 右上角菜单 → Install from Disk**，选择 ZIP，安装并启用 **Blender MCP Integrated**。
3. 展开其偏好面板。若已安装官方原版 **MCP** Extension，先停止并禁用原版，再启动集成包，避免两个桥接服务争用端口。

安装本地 ZIP 后即可使用。也可在 **Extensions → Repositories → Add Remote Repository** 中添加 `https://psiQAQ.github.io/blender_mcp-setup-guide/index.json`，Blender 会选择当前平台对应的包并提供更新。通过在线 Extensions 仓库安装或更新时，需启用 **Preferences → System → Network → Allow Online Access**。

## 2. 启动服务并复制配置

默认启用 **Start MCP When Enabled**，服务会自动启动；也可点击 **Start MCP**。等待状态变为 **MCP: Running**，点击 **Check Connection** 检查 HTTP 服务与 Blender 桥接。

在 **Agent** 中选择实际使用的客户端，再点击 **Copy Connection Configuration**。配置会复制到剪贴板，并写入偏好面板显示的用户目录内 `client-config.txt`。该目录还包含 `service.log` 和 HTTP 凭据；升级包时保留这些用户数据。

| 设置 | 默认值 | 用途 |
| --- | --- | --- |
| HTTP Port | `8000` | 客户端连接 `http://127.0.0.1:8000/` |
| Bridge Port | `9876` | 随包服务与 Blender 通信 |
| Authorization | `Bearer <本机生成的 token>` | HTTP 请求鉴权 |

下文 `YOUR_BLENDER_MCP_TOKEN` 是占位符，必须替换为复制配置中的实际 token；优先直接使用复制的配置。客户端连接根路径 `/`，端口 `9876` 用于桥接。调整 HTTP 端口后需重新复制客户端配置。配置与凭据只供本机使用，不应提交到 Git。

## 3. 配置所用客户端

只需完成所用客户端的小节。已有配置时合并 `blender` 条目，保留其他服务器和设置；同名条目应替换，避免重复。若从 stdio 方式切换，请先按[第 5 节](#5-切换方式与卸载)移除旧条目。

### 3.1 Codex

用户配置文件为 Windows 的 `%USERPROFILE%\.codex\config.toml`、Linux/macOS 的 `~/.codex/config.toml`，例如 `C:\Users\Alice\.codex\config.toml`。也可放在受信任项目的 `.codex/config.toml`，只对该项目生效。目录或文件不存在时创建它，然后添加：

```toml
[mcp_servers.blender]
enabled = true
url = "http://127.0.0.1:8000/"
http_headers = { Authorization = "Bearer YOUR_BLENDER_MCP_TOKEN" }
```

保存后重新启动 Codex CLI 会话，或在桌面客户端的 MCP 设置中重新加载服务器。CLI 可检查已加载的配置：

```text
codex mcp list
codex mcp get blender
```

检查 `blender` 使用 HTTP URL 且包含 `Authorization`。这些命令检查配置；实际通信仍按第 4 节验收。配置字段和作用域见 [OpenAI 官方 MCP 文档](https://developers.openai.com/codex/mcp/)。

### 3.2 Claude Code

**项目配置**：在启动 Claude Code 的项目根目录创建或合并 `.mcp.json`：

```json
{
  "mcpServers": {
    "blender": {
      "type": "http",
      "url": "http://127.0.0.1:8000/",
      "headers": {
        "Authorization": "Bearer YOUR_BLENDER_MCP_TOKEN"
      }
    }
  }
}
```

**用户配置**：如需所有项目使用，也可选择下面的命令，适用于 PowerShell、Bash。它将条目写入用户 `~/.claude.json`；无需手动编辑该文件。用户注册与项目 `.mcp.json` 选择一种作用域即可：

```text
claude mcp add --transport http --scope user blender http://127.0.0.1:8000/ --header "Authorization: Bearer YOUR_BLENDER_MCP_TOKEN"
```

在对应项目目录检查，然后重新开启 Claude Code 会话：

```text
claude mcp list
claude mcp get blender
claude
```

项目 `.mcp.json` 首次使用时按客户端提示批准服务器；在会话中输入 `/mcp` 查看连接状态，再执行第 4 节的场景读取。配置语法和作用域见 [Claude Code 官方文档](https://code.claude.com/docs/en/mcp)。

### 3.3 OpenCode

用户配置文件为 Windows 的 `%USERPROFILE%\.config\opencode\opencode.json`、Linux/macOS 的 `~/.config/opencode/opencode.json`。也可使用项目根目录的 `opencode.json`。在所选文件合并：

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "blender": {
      "type": "remote",
      "url": "http://127.0.0.1:8000/",
      "enabled": true,
      "oauth": false,
      "headers": {
        "Authorization": "Bearer YOUR_BLENDER_MCP_TOKEN"
      }
    }
  }
}
```

这里的 `remote` 表示通过 HTTP 连接，即使服务在本机也使用该类型。示例在复制配置基础上显式添加 `enabled` 和 `oauth: false`，使用集成包提供的 Bearer token。

保存后重新启动 OpenCode，在相同项目目录检查：

```text
opencode mcp list
```

然后按第 4 节读取场景。配置位置见 [OpenCode config](https://opencode.ai/docs/config/)，字段见 [OpenCode MCP 文档](https://opencode.ai/docs/mcp-servers/)。

## 4. 验证实际连接与排查故障

保持 Blender 打开且状态为 **Running**。先向客户端发送只读请求：

> 请使用 blender MCP 读取 Blender 版本和当前场景对象列表，并报告实际返回结果。

客户端应返回当前 Blender 的版本与对象。需要验证修改操作时，在已备份的测试场景中继续：

> 创建名为 MCP_Test_Cube 的立方体，回读位置，再删除该测试对象并确认对象数恢复。

客户端配置已加载、HTTP 健康检查通过与真实场景调用成功是不同检查。可用以下 PowerShell 命令单独检查 HTTP 服务；用实际 token 替换占位符，端口与偏好一致：

```powershell
$token = 'YOUR_BLENDER_MCP_TOKEN'
Invoke-RestMethod -Uri 'http://127.0.0.1:8000/health' -Headers @{ Authorization = "Bearer $token" }
```

| 现象 | 检查与操作 |
| --- | --- |
| 服务没有进入 Running | 核对安装包的平台后缀、系统架构与 Blender 5.1.x / CPython 3.13；查看偏好错误与 `service.log` |
| 端口被占用 | 停止已知的旧服务，或停止集成服务、修改为空闲端口、再启动并重新复制配置 |
| HTTP 401 | 重新复制实际 token，核对 `Authorization` 与 `Bearer ` 前缀 |
| HTTP 403 | 使用 `http://127.0.0.1:<HTTP Port>/`，检查客户端的 Host / Origin |
| 配置中找不到 blender | 核对用户/项目作用域与实际文件位置，重启客户端；项目配置需满足信任要求 |
| MCP 可连接但场景调用失败 | 检查 Blender 桥接、官方原版 Extension 是否仍启用，以及日志中的真实错误 |
| 服务异常退出 | 查看日志，点击 Stop MCP 后再启动；重新检查实际场景调用 |

当前集成包支持三种目标平台的原生同机 loopback。WSL、SSH 或容器中的客户端需要另外核对其运行位置与网络可达性。

## 5. 切换方式与卸载

切换为官方 stdio 方式前，点击 **Stop MCP**，禁用集成 Extension，再移除客户端中的 HTTP `blender` 条目，并按[官方 stdio 教程](blender_mcp-stdio-setup_zh.md)配置。

- Codex：删除所选 `config.toml` 中的 `[mcp_servers.blender]` 配置及其子表；通过 CLI 注册的用户条目也可运行 `codex mcp remove blender`。
- Claude Code：手动配置时只删除 `.mcp.json` 内的 `mcpServers.blender`；用户注册时运行 `claude mcp remove --scope user blender`。
- OpenCode：只删除所选配置中的 `mcp.blender`，保留其他设置。

完全卸载时，在 Blender 中停止服务、禁用并卸载 **Blender MCP Integrated**。用户目录中的日志、凭据和导出配置独立于安装包；确认不再需要后再处理这些数据。

构建与验证细节分别见[构建说明](integration-build.md)和[本地验收记录](integration-validation.md)。
