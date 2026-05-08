简体中文 | [English](../README.md)

# Claude Code 本地控制 Blender — 完整安装与配置教程

> 目标：在本机同一台电脑上运行 Claude Code + Blender，通过 Blender 官方 MCP Server 控制 Blender。  
> 架构：`Claude Code ⇄ (stdio) ⇄ blender-mcp 进程 ⇄ (TCP localhost) ⇄ Blender MCP Add-on ⇄ Blender Python API`
>
> HTTP 模式或远端控制局域网 Blender 的方案，参见 [blender_mcp-remote_zh.md](./blender_mcp-remote_zh.md)。

![Claude Code + Blender MCP 架构图](../assets/imgs/claude-code-mcp-blender.png)

---

## 1. 环境假设

| 项目 | 值 | 说明 |
|------|-----|------|
| Blender 版本 | ≥ 5.1 | 官方要求 |
| Python | ≥ 3.10 | MCP Server 要求 |

检查本机 Claude Code：

```bash
claude --version
claude mcp list
```

---

## 2. 安装 Blender MCP Add-on

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

### 2.4 Add-on 配置（保持默认即可）

本地模式无需修改 Host，保持默认值：

```text
Host = localhost
Port = 9876
```

点击 **Start Server**（或重启 Blender 让 Auto Start 生效），确认显示：

```text
Server is running
```

### 2.5 确保 Blender 允许在线访问

Blender 5.1+ 有在线访问控制。在 Blender 中：

```text
Edit → Preferences → System → Online Access → 勾选启用
```

如果不启用，Add-on 启动时会报错：`Online access must be enabled in the system preferences`。

---

## 3. 安装 blender-mcp MCP Server

使用 `uv tool install` 全局安装，`blender-mcp` 直接作为系统命令使用。

### 3.1 前置条件

- 已安装 `uv`（参考 [uv 官方安装指南](https://docs.astral.sh/uv/#installation)）
- Python ≥ 3.10

```bash
uv --version
```

### 3.2 克隆源码到稳定位置

```bash
cd ~/.local/share
git clone --depth 1 https://projects.blender.org/lab/blender_mcp.git
```

> `pyproject.toml` 在 `blender_mcp/mcp/` 下（非根目录），后续安装操作都在 `mcp/` 中进行。

### 3.3 全局安装

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

### 3.4 注册到 Claude Code

Claude Code 通过 `claude mcp add` 注册 MCP Server。stdio 模式下 Claude Code 自动管理 `blender-mcp` 进程，退出时自动关闭。

```bash
# 注册（注意：server name 必须放在 options 之前）
claude mcp add blender --transport stdio --scope user \
  -e BLENDER_MCP_HOST=localhost \
  -e BLENDER_MCP_PORT=9876 \
  -- blender-mcp
```

> **环境变量名**：是 `BLENDER_MCP_HOST`（带 `_MCP` 中缀），不是 `BLENDER_HOST`。

验证：

```bash
claude mcp get blender
```

应显示 `Status: ✓ Connected` 且 `Environment` 中包含 `BLENDER_MCP_HOST=localhost`。

### 3.5 更新方法（git pull 兼容）

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

### 3.6 卸载方法

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

## 4. 完整连接测试

### 4.1 检查 MCP 连接状态

启动 Claude Code：

```bash
claude
```

在 Claude Code 中输入：

```text
/mcp
```

确认 `blender` 状态为 **connected**。

### 4.2 测试读取场景

在 Claude Code 中输入：

```text
请使用 blender MCP 读取当前 Blender 场景中的对象列表
```

### 4.3 测试创建对象

在 Claude Code 中输入：

```text
请使用 blender MCP 在当前 Blender 场景中创建一个名为 MCP_Test_Cube 的立方体，位置为 (0, 0, 1)，尺寸为 1，并给它添加一个蓝色材质
```

如果成功，本地 Blender 画面应该出现新的立方体。

---

## 5. 数据流图解

```text
┌──────────────────┐       stdin/stdout        ┌──────────────────┐
│   Claude Code    │ ◄══════════════════════► │  blender-mcp     │
│   (本机)         │    (MCP 协议)             │  (本机进程)      │
└──────────────────┘                           └────────┬─────────┘
                                                        │
                                                 TCP socket
                                              localhost:9876
                                                        │
                                                        ▼
                                              ┌──────────────────┐
                                              │  Blender Add-on  │
                                              │  localhost:9876   │
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

## 6. 常见问题

### 6.1 `claude mcp list` 显示 disconnected

```bash
claude mcp get blender
```

重点检查：
- `command` 是否为 `blender-mcp`，该命令能否直接执行
- `BLENDER_MCP_HOST` 是否为 `localhost`
- `BLENDER_MCP_PORT` 是否为 `9876`

### 6.2 MCP connected 但操作 Blender 报错 "Cannot connect to Blender"

可能原因：
1. Blender Add-on 未启动（检查 `Server is running` 状态）
2. Blender 未允许在线访问（检查系统偏好设置）
3. Add-on 的 Host 被改为了非 localhost 的值

### 6.3 连接后很快断开

可能原因：
1. Blender Add-on 有客户端超时机制（默认 10 秒），长时间无请求会断开
2. `blender-mcp` 进程崩溃（检查终端输出）

---

## 7. 删除配置

```bash
claude mcp remove blender
claude mcp list
```

---

## 8. 安全注意事项

Blender MCP 的能力等同于"让 LLM 在 Blender 中执行任意 Python 代码"。建议：

1. 只在测试工程或已备份的工程中使用
2. 不要在包含敏感文件的环境中运行
3. 对高风险操作保留人工确认
4. 不要让 Claude 自动执行你没看懂的 Python 代码

---

## 9. 参考资料

- Blender Lab MCP Server: https://www.blender.org/lab/mcp-server/
- Blender MCP 源码: `blender_mcp/` 项目目录
- MCP Server 入口: `mcp/blmcp/__init__.py` → `main()` 函数
- TCP 连接实现: `mcp/blmcp/tools_helpers/connection.py` → `send_code()` 函数
- Add-on 服务端: `addon/blender_mcp_addon/mcp_to_blender_server.py` → `start()` 函数
- Claude Code MCP 文档: https://docs.anthropic.com/en/docs/claude-code/mcp
