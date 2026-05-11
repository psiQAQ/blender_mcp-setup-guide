简体中文 | [English](./blender_mcp-remote.md)

# Claude Code 远端控制局域网 Blender — 完整安装与配置教程

> 目标：在本机运行 Claude Code，通过 Blender 官方 MCP Server 远端控制局域网内另一台电脑上的 Blender。  
> 架构：`本机 Claude Code ⇄ (stdio 或 HTTP) ⇄ 本机 blender-mcp 进程 ⇄ (TCP socket) ⇄ 远端 Blender MCP Add-on ⇄ Blender Python API`
>
> 单机本地部署方案，参见 [blender_mcp-setup_zh.md](./blender_mcp-setup_zh.md)。

![Claude Code + Blender MCP 架构图](../assets/imgs/claude-code-mcp-blender.png)

---

## 0. 关键结论（先读）

1. **环境变量名是 `BLENDER_MCP_HOST` / `BLENDER_MCP_PORT`**，不是 `BLENDER_HOST` / `BLENDER_PORT`。  
   源码 `mcp/blmcp/tools_helpers/connection.py:27-28` 使用的变量名带 `_MCP` 中缀。

2. **`BLENDER_MCP_HOST` 填写远端 Blender 电脑的 IP**，不是 Claude Code 所在电脑的 IP。  
   因为 `blender-mcp` 进程是 TCP **客户端**，主动连接远端 Blender Add-on 的 TCP **服务端**。

3. **不要直接把 Claude Code 指向远端 Blender 的 9876 端口**。  
   Blender Add-on 的 9876 端口是裸 TCP socket，不是 MCP HTTP endpoint。  
   正确做法是本机启动 `blender-mcp` 进程，由它连接远端 Blender。

4. **远端 Blender Add-on 默认只监听 `localhost`**，局域网访问需要改为 `0.0.0.0` 或远端电脑的局域网 IP。

5. **长期使用优先推荐 SSH 隧道**。  
   远端 Blender 保持监听 `localhost:9876`，本机通过 `ssh -L` 转发，避免把 Blender Python 执行入口暴露到局域网。

6. **Claude Code HTTP 模式注册时不要加 `--`**。  
   `--` 只用于 stdio 模式中分隔 MCP server 名称和本地启动命令；HTTP 模式应直接写 URL。

---

## 1. 环境假设

| 项目 | 值 | 说明 |
|------|-----|------|
| 本机（Claude Code 电脑）IP | `192.168.2.10` | 固定 IP，用于远端防火墙白名单 |
| 远端电脑（Blender 电脑）IP | `192.168.2.20` | 填入 `BLENDER_MCP_HOST` |
| Blender MCP 端口 | `9876` | Add-on 监听端口，可自定义 |
| MCP Server HTTP 端口 | `8000` | 仅 HTTP 模式使用 |
| Blender 版本 | ≥ 5.1 | 官方要求 |
| Python | ≥ 3.10 | MCP Server 要求 |

检查本机 Claude Code：

```bash
claude --version
claude mcp list
```

检查本机能否访问远端电脑：

```powershell
ping 192.168.2.20
```

---

## 2. 远端电脑：安装 Blender MCP Add-on

### 2.1 安装 Blender 5.1+

从 [blender.org](https://www.blender.org/download/) 下载安装。

### 2.2 安装 Add-on

打开 [https://www.blender.org/lab/mcp-server/](https://www.blender.org/lab/mcp-server/)，有两种安装方式：

- **拖拽安装**：将页面上的安装链接拖入 Blender 窗口（需拖两次：第一次添加 Blender Lab 仓库，第二次安装 Add-on 本体）
- **手动安装**：下载 Add-on zip 文件，在 Blender 中 `Edit → Preferences → Add-ons → Install from Disk`

> 拖拽安装的优势是可以收到更新通知。

### 2.3 启用 Add-on

```text
Edit → Preferences → Add-ons → 搜索 "MCP"
```

确认 Add-on 已启用。

### 2.4 修改 Host 为局域网可访问（关键步骤）

默认配置：

```text
Host = localhost
Port = 9876
```

这在局域网场景下不可用，因为 `localhost` 只允许本机连接。需要修改为：

```text
Host = 0.0.0.0
Port = 9876
```

或指定远端电脑的局域网 IP：

```text
Host = 192.168.2.20
Port = 9876
```

修改路径：`Edit → Preferences → Add-ons → 找到 Blender MCP → 展开设置面板 → 修改 Host 字段`

修改后点击 **Start Server**（或重启 Blender 让 Auto Start 生效），确认显示：

```text
Server is running
```

> **注意**：修改 Host 后需要先 Stop 再 Start 服务器才能生效。

### 2.5 确保 Blender 允许在线访问

Blender 5.1+ 有在线访问控制。在 Blender 中：

```text
Edit → Preferences → System → Online Access → 勾选启用
```

如果不启用，Add-on 启动时会报错：`Online access must be enabled in the system preferences`。

---

## 3. 远端电脑：配置防火墙

### 3.1 Windows 远端电脑

以**管理员权限**打开 PowerShell，先检查当前网络配置文件：

```powershell
Get-NetConnectionProfile
```

如果当前局域网被识别为 `Public`，而下面规则只写了 `-Profile Private`，防火墙规则可能不生效。确认这是可信局域网后，可改为 Private：

```powershell
Set-NetConnectionProfile -InterfaceAlias "你的网络适配器名称(WiFi名字)" -NetworkCategory Private
```

然后执行：

```powershell
# 推荐：只允许 Claude Code 所在电脑的固定 IP 访问
New-NetFirewallRule `
  -DisplayName "Blender MCP 9876 - Claude Code Only" `
  -Direction Inbound `
  -Action Allow `
  -Protocol TCP `
  -LocalPort 9876 `
  -RemoteAddress 192.168.2.10 `
  -Profile Private
```

如果还没有固定 Claude Code 电脑的 IP，可临时允许整个局域网网段：

```powershell
New-NetFirewallRule `
  -DisplayName "Blender MCP 9876 - LAN" `
  -Direction Inbound `
  -Action Allow `
  -Protocol TCP `
  -LocalPort 9876 `
  -RemoteAddress 192.168.2.0/24 `
  -Profile Private
```

验证端口正在监听：

```powershell
netstat -ano | findstr :9876
```

应看到类似输出：

```text
TCP    0.0.0.0:9876          0.0.0.0:0              LISTENING       12345
```

### 3.2 Linux 远端电脑

如果使用 UFW：

```bash
# 推荐：只允许 Claude Code 所在电脑的固定 IP
sudo ufw allow from 192.168.2.10 to any port 9876 proto tcp
sudo ufw status
```

验证端口：

```bash
ss -lntp | grep 9876
```

---

## 4. 本机：测试能否连接远端 Blender

### 4.1 Windows

```powershell
Test-NetConnection 192.168.2.20 -Port 9876
```

成功输出：

```text
TcpTestSucceeded : True
```

### 4.2 Linux / macOS / WSL

```bash
nc -vz 192.168.2.20 9876
```

或：

```bash
timeout 2 bash -c "cat < /dev/null > /dev/tcp/192.168.2.20/9876" && echo OK || echo FAIL
```

> 如果测试失败，按顺序排查：  
> 1. 远端 Blender 是否打开  
> 2. Add-on 是否显示 `Server is running`  
> 3. Host 是否已改为 `0.0.0.0`  
> 4. 防火墙是否放行 9876  
> 5. 两台电脑是否在同一网段  
> 6. 路由器是否开启了 AP 隔离

---

## 5. 本机：安装 blender-mcp MCP Server

使用 `uv tool install` 全局安装，`blender-mcp` 直接作为系统命令使用。

### 5.1 前置条件

- 已安装 `uv`（参考 [uv 官方安装指南](https://docs.astral.sh/uv/#installation)）
- Python ≥ 3.10

```bash
uv --version
```

### 5.2 克隆源码到稳定位置

选择一个稳定路径，后续 `git pull` 和安装操作都在此目录进行：

```bash
cd ~/.local/share
git clone --depth 1 https://projects.blender.org/lab/blender_mcp.git
```

> `pyproject.toml` 在 `blender_mcp/mcp/` 下（非根目录），后续安装操作都在 `mcp/` 中进行。

### 5.3 全局安装

```bash
cd ~/.local/share/blender_mcp/mcp
uv tool install --python 3.11 .
```

安装后 `blender-mcp` 变为系统级命令，验证：

```bash
which blender-mcp
blender-mcp --help
```

> `uv tool install` 将包安装到 uv 的独立工具目录，不会污染系统 Python。

### 5.4 注册到 Claude Code

Claude Code 通过 `claude mcp add` 注册 MCP Server。stdio 模式下 Claude Code 自动管理 `blender-mcp` 进程，退出时自动关闭。

`claude mcp add` 语法（**server name 必须放在 options 之前**）：

```bash
claude mcp add <name> [options] -- <command>
```

#### stdio 模式（推荐）

```bash
# <name>：server name，这里取为 blender（可改任意名）
#
# 远端 Blender（替换 IP 为远端电脑的实际 IP）
claude mcp add blender --transport stdio --scope user \
  -e BLENDER_MCP_HOST=192.168.2.20 \
  -e BLENDER_MCP_PORT=9876 \
  -- blender-mcp

# 全本地模式（本机运行 Blender + MCP）
claude mcp add blender --transport stdio --scope user \
  -e BLENDER_MCP_HOST=localhost \
  -e BLENDER_MCP_PORT=9876 \
  -- blender-mcp
```

> **环境变量名**：是 `BLENDER_MCP_HOST`（带 `_MCP` 中缀），不是 `BLENDER_HOST`。  
> **options 放置规则**：`--transport`、`-e`/`--env`、`--scope` 等必须在 name 之后、`--` 之前。

验证：

```bash
claude mcp get blender
```

应显示 `Status: ✓ Connected` 且 `Environment` 中包含正确的环境变量。

#### http 模式

先手动启动 HTTP 服务（进程需保持运行）：

```bash
BLENDER_MCP_HOST=192.168.2.20 BLENDER_MCP_PORT=9876 blender-mcp --transport http --host 127.0.0.1 --port 8000
```

然后在另一个终端注册（HTTP 模式注册 URL 前**不加 `--`**）：

```bash
claude mcp add --transport http --scope user blender http://127.0.0.1:8000/
```

#### 两种模式对比

| 特性 | stdio 模式 | HTTP 模式 |
|------|-----------|----------|
| 启动方式 | Claude Code 自动启动 | 需手动启动并保持运行 |
| 进程管理 | Claude Code 管理，退出时自动关闭 | 需手动管理 |
| 环境变量传递 | `-e` 直接传入 | 启动前手动设置环境变量 |
| 稳定性 | 高 | 中（进程可能意外退出） |
| 多客户端 | 否（独占） | 是（可多个客户端连同一端点） |
| 适用场景 | 日常使用（推荐） | 需浏览器端同时访问 |
| 网络暴露 | 无（本地进程间通信） | `127.0.0.1:8000` 本地 HTTP |

### 5.5 更新方法（git pull 兼容）

```bash
cd ~/.local/share/blender_mcp

# （首次更新前执行）设置 upstream tracking
git branch --set-upstream-to=origin/main main

# 拉取最新代码
git pull

# 重新安装（从本地路径安装的包，版本号不变时 upgrade 不会生效）
cd mcp && uv tool install --reinstall .

# 验证
blender-mcp --help
```

> **为什么用 `--reinstall` 而不是 `upgrade`**：`uv tool install` 从本地路径安装，`upgrade` 仅检查 PyPI。`--reinstall` 强制从当前源码重新构建安装。

### 5.6 卸载方法

```bash
# 1. 从 Claude Code 移除 MCP Server 注册
claude mcp remove blender -s local
claude mcp remove blender -s user  # 如果之前用了 --scope user

# 2. 卸载全局工具
uv tool uninstall blender-mcp

# 3. 可选：删除源码
rm -rf ~/.local/share/blender_mcp
```

---


## 6. 完整连接测试

### 6.1 检查 MCP 连接状态

启动 Claude Code：

```bash
claude
```

在 Claude Code 中输入：

```text
/mcp
```

确认 `blender` 状态为 **connected**。

### 6.2 测试读取场景

在 Claude Code 中输入：

```text
请使用 blender MCP 读取当前 Blender 场景中的对象列表
```

### 6.3 测试创建对象

在 Claude Code 中输入：

```text
请使用 blender MCP 在当前 Blender 场景中创建一个名为 MCP_Test_Cube 的立方体，位置为 (0, 0, 1)，尺寸为 1，并给它添加一个蓝色材质
```

如果成功，远端 Blender 画面应该出现新的立方体。

### 6.4 TCP 端口级测试

如果 Claude Code 中 MCP 显示 connected 但操作失败，可在本机直接测试 TCP 连接：

```powershell
# Windows PowerShell - 带超时的 TCP 原始协议测试
$client = New-Object System.Net.Sockets.TcpClient
$client.ReceiveTimeout = 2000
$client.SendTimeout = 2000

try {
    $client.Connect("192.168.2.20", 9876)

    $stream = $client.GetStream()
    $payload = '{"type":"execute","code":"result = {\"status\":\"test\"}","strict_json":true}' + "`0"
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($payload)

    $stream.Write($bytes, 0, $bytes.Length)
    Start-Sleep -Milliseconds 300

    $buffer = New-Object byte[] 4096
    if ($stream.DataAvailable) {
        $count = $stream.Read($buffer, 0, $buffer.Length)
        $response = [System.Text.Encoding]::UTF8.GetString($buffer, 0, $count)
        Write-Host "Response:"
        Write-Host $response
    } else {
        Write-Host "Connected, but no response within short wait."
    }
}
catch {
    Write-Host "TCP test failed:"
    Write-Host $_.Exception.Message
}
finally {
    if ($client) {
        $client.Close()
    }
}
```

---

## 7. 数据流图解

### stdio 模式

```text
┌──────────────────┐       stdin/stdout        ┌──────────────────┐
│   Claude Code    │ ◄══════════════════════► │  blender-mcp     │
│   (本机)         │    (MCP 协议)             │  (本机进程)      │
└──────────────────┘                           └────────┬─────────┘
                                                        │
                                                 TCP socket
                                             BLENDER_MCP_HOST
                                             BLENDER_MCP_PORT
                                                        │
                                                        ▼
                                              ┌──────────────────┐
                                              │  Blender Add-on  │
                                              │  (远端电脑)      │
                                              │  0.0.0.0:9876    │
                                              └────────┬─────────┘
                                                        │
                                                  exec(code)
                                                        │
                                                        ▼
                                              ┌──────────────────┐
                                              │  Blender         │
                                              │  Python API      │
                                              └──────────────────┘
```

### HTTP 模式

```text
┌──────────────────┐       HTTP            ┌──────────────────┐
│   Claude Code    │ ◄══════════════════► │  blender-mcp     │
│   (本机)         │  127.0.0.1:8000      │  (本机进程)      │
└──────────────────┘  (MCP Streamable HTTP) └────────┬─────────┘
                                                        │
                                                 TCP socket
                                             BLENDER_MCP_HOST
                                             BLENDER_MCP_PORT
                                                        │
                                                        ▼
                                              ┌──────────────────┐
                                              │  Blender Add-on  │
                                              │  (远端电脑)      │
                                              │  0.0.0.0:9876    │
                                              └────────┬─────────┘
                                                        │
                                                  exec(code)
                                                        │
                                                        ▼
                                              ┌──────────────────┐
                                              │  Blender         │
                                              │  Python API      │
                                              └──────────────────┘
```

---

## 8. 更安全的替代方案：SSH 隧道

如果不想将 Blender 端口暴露到局域网，可使用 SSH 隧道。远端 Blender 保持只监听 `localhost`，本机通过 SSH 转发。

### 8.1 远端 Blender 设置

```text
Host = localhost
Port = 9876
```

不需要改 Host，不需要开防火墙 9876 端口。

### 8.2 本机建立 SSH 隧道

```bash
ssh -N -L 9876:127.0.0.1:9876 user@192.168.2.20
```

Windows 也可用 OpenSSH（Windows 10+ 自带）：

```powershell
ssh -N -L 9876:127.0.0.1:9876 user@192.168.2.20
```

### 8.3 Claude Code 配置

先添加 MCP Server（参考 5.2 节完整步骤）：

```bash
claude mcp add blender -e BLENDER_MCP_HOST=127.0.0.1 -e BLENDER_MCP_PORT=9876 -- blender-mcp
```

此时 `blender-mcp` 连接的是本机的 `127.0.0.1:9876`，SSH 隧道会将流量转发到远端。

### 8.4 两种方案对比

| 项目 | 直连暴露 9876 | SSH 隧道 |
|------|:---:|:---:|
| 局域网其他设备可访问 Blender | 是 | 否 |
| 需要开防火墙 9876 | 是 | 否 |
| 远端 Blender 监听 localhost | 否 | 是 |
| 安全性 | 较低 | 较高 |
| 配置复杂度 | 低 | 中 |
| 推荐场景 | 临时测试 | 长期使用 |

---

## 9. 常见问题

### 9.1 `claude mcp list` 显示 disconnected

```bash
claude mcp get blender
```

重点检查：
- `command` 是否为 `blender-mcp`，该命令能否直接执行
- `BLENDER_MCP_HOST` 是否是远端 Blender 电脑的 IP
- `BLENDER_MCP_PORT` 是否是 `9876`
- 环境变量名是否正确（带 `_MCP` 中缀）

### 9.2 MCP connected 但操作 Blender 报错 "Cannot connect to Blender"

可能原因：
1. 远端 Blender Add-on 未启动（检查 `Server is running` 状态）
2. `BLENDER_MCP_HOST` 仍指向 `localhost` 而非远端 IP
3. 远端 Blender Host 仍是 `localhost`，未改为 `0.0.0.0`
4. 远端防火墙阻止了 9876 端口
5. Blender 未允许在线访问

### 9.3 连接后很快断开

可能原因：
1. Blender Add-on 有客户端超时机制（默认 10 秒），长时间无请求会断开
2. `blender-mcp` 进程崩溃（检查终端输出）

### 9.4 Windows 路径有空格导致失败

使用引号包住完整路径：

```powershell
claude mcp add --transport stdio --scope user blender -- "C:\path with spaces\blender-mcp.exe"
```

### 9.5 HTTP 模式下 Claude Code 连接失败

确认：
1. `blender-mcp --transport http` 进程正在运行
2. 端口 8000 未被占用
3. Claude Code 注册的 URL 是 `http://127.0.0.1:8000/`（注意末尾 `/`）

---

## 10. 删除配置

```bash
claude mcp remove blender
claude mcp list
```

---

## 11. 安全注意事项

Blender MCP 的能力等同于"让 LLM 在 Blender 中执行任意 Python 代码"。建议：

1. 只在测试工程或已备份的工程中使用
2. 不要在包含敏感文件的环境中运行
3. 不要将 9876 端口暴露到公网
4. 局域网直连时限制来源 IP 或网段
5. 优先使用 SSH 隧道
6. 对高风险操作保留人工确认
7. 不要让 Claude 自动执行你没看懂的 Python 代码

---

## 12. 推荐最终配置速查

### 长期使用（推荐：SSH 隧道）

```text
远端 Blender:
  Add-on Host = localhost
  Add-on Port = 9876
  防火墙: 不需要开放 9876 给局域网

本机:
  ssh -N -L 9876:127.0.0.1:9876 user@192.168.2.20

本机 Claude Code MCP 注册:
  见 5.2 节 stdio 模式命令，将 BLENDER_MCP_HOST 改为 127.0.0.1
```

优点：远端 Blender 仍然只接受本机 localhost 连接，局域网其他设备不能直接访问 Blender 的 Python 执行入口。

### 临时测试（局域网直连）

```text
本机 Claude Code 电脑:
  固定 IP = 192.168.2.10

远端 Blender 电脑:
  IP = 192.168.2.20
  Add-on Host = 0.0.0.0
  Add-on Port = 9876

远端防火墙:
  只允许 192.168.2.10 访问 9876

本机 Claude Code MCP 注册:
  见 5.2 节 stdio 模式命令
```

适用场景：短时间验证、同一可信局域网、远端防火墙已经限制来源 IP。

### 不推荐配置

```text
不要将 Claude Code 直接配置到：
  http://192.168.2.20:9876/mcp

原因：
  9876 是 Blender Add-on 的裸 TCP socket，不是 MCP HTTP endpoint。
```

---

## 13. 参考资料

- Blender Lab MCP Server: https://www.blender.org/lab/mcp-server/
- Blender MCP 源码: `blender_mcp/` 项目目录
- MCP Server 入口: `mcp/blmcp/__init__.py` → `main()` 函数
- TCP 连接实现: `mcp/blmcp/tools_helpers/connection.py` → `send_code()` 函数
- Add-on 服务端: `addon/blender_mcp_addon/mcp_to_blender_server.py` → `start()` 函数
- Claude Code MCP 文档: https://docs.anthropic.com/en/docs/claude-code/mcp
