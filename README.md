[简体中文](./docs/README_zh.md) | English

# Blender MCP Local Setup Guide

> Control Blender locally on the same machine via Claude Code using Blender's official MCP Server.  
> Architecture: `Claude Code ⇄ (stdio) ⇄ blender-mcp process ⇄ (TCP localhost) ⇄ Blender MCP Add-on ⇄ Blender Python API`
>
> For HTTP transport or remote Blender setup, see [blender_mcp-remote.md](./docs/blender_mcp-remote.md) (English) / [blender_mcp-remote_zh.md](./docs/blender_mcp-remote_zh.md) (中文).

---

## Requirements

| Item | Version | Notes |
|------|---------|-------|
| Blender | ≥ 5.1 | Official requirement |
| Python | ≥ 3.10 | For blender-mcp |
| uv | latest | Python package manager |

Check Claude Code:

```bash
claude --version
claude mcp list
```

---

## 1. Install Blender MCP Add-on

### 1.1 Install Blender 5.1+

Download from [blender.org](https://www.blender.org/download/).

### 1.2 Install the Add-on

Visit [https://www.blender.org/lab/mcp-server/](https://www.blender.org/lab/mcp-server/). Two installation methods:

- **Drag & drop**: Drag the install link from the page into Blender (twice: first to add the Blender Lab repo, then to install the add-on)
- **Manual**: Download the add-on zip, then `Edit → Preferences → Add-ons → Install from Disk`

> Drag & drop enables update notifications.

### 1.3 Enable the Add-on

```text
Edit → Preferences → Add-ons → Search "MCP"
```

Make sure the add-on is enabled.

### 1.4 Add-on Configuration (keep defaults)

For local setup, keep the default Host:

```text
Host = localhost
Port = 9876
```

Click **Start Server** (or restart Blender to let Auto Start take effect). Confirm you see:

```text
Server is running
```

### 1.5 Enable Online Access

Blender 5.1+ requires online access permission:

```text
Edit → Preferences → System → Online Access → Enable
```

Without this, the add-on will show: `Online access must be enabled in the system preferences`.

---

## 2. Install blender-mcp MCP Server

Install globally with `uv tool install` so `blender-mcp` is available as a system-wide command.

### 2.1 Prerequisites

- [uv](https://docs.astral.sh/uv/#installation) installed
- Python ≥ 3.10

```bash
uv --version
```

### 2.2 Clone the Source

```bash
cd ~/.local/share
git clone --depth 1 https://projects.blender.org/lab/blender_mcp.git
```

> `pyproject.toml` is inside `blender_mcp/mcp/`, not at the repo root. All install commands run from `mcp/`.

### 2.3 Global Install

```bash
cd ~/.local/share/blender_mcp/mcp
uv tool install --python 3.11 .
```

Verify the installation:

```bash
which blender-mcp
blender-mcp --help
```

> `uv tool install` places the package in uv's isolated tool directory — no system Python pollution.

### 2.4 Register with Claude Code

Claude Code auto-manages the `blender-mcp` process in stdio mode — it starts the process on demand and stops it on exit.

```bash
# Note: server name must come before options
claude mcp add blender --transport stdio --scope user \
  -e BLENDER_MCP_HOST=localhost \
  -e BLENDER_MCP_PORT=9876 \
  -- blender-mcp
```

> **Environment variables**: `BLENDER_MCP_HOST` and `BLENDER_MCP_PORT` (note the `_MCP` infix).

Verify:

```bash
claude mcp get blender
```

Expected output: `Status: ✓ Connected` with `BLENDER_MCP_HOST=localhost` in the Environment section.

### 2.5 Updating

When the official repo has updates:

```bash
cd ~/.local/share/blender_mcp

# First time only: set upstream tracking
git branch --set-upstream-to=origin/main main

# Pull latest code
git pull

# Reinstall (upgrade won't work for local-path installs)
cd mcp && uv tool install --reinstall .

# Verify
blender-mcp --help
```

> **Why `--reinstall` instead of `upgrade`**: `uv tool install` was done from a local path. `upgrade` only checks PyPI. `--reinstall` forces a rebuild from the current source.

### 2.6 Uninstalling

```bash
# 1. Remove MCP server registration
claude mcp remove blender -s local
claude mcp remove blender -s user  # if you used --scope user

# 2. Uninstall the tool
uv tool uninstall blender-mcp

# 3. Optionally delete the source
rm -rf ~/.local/share/blender_mcp
```

---

## 3. Connection Test

### 3.1 Check MCP Status

Start Claude Code:

```bash
claude
```

Then type:

```text
/mcp
```

Confirm `blender` shows as **connected**.

### 3.2 Test: Read Scene

In Claude Code:

```text
Use blender MCP to read the object list from the current Blender scene.
```

### 3.3 Test: Create an Object

In Claude Code:

```text
Use blender MCP to create a cube named MCP_Test_Cube at position (0, 0, 1) with size 1, and add a blue material to it.
```

If successful, the new cube should appear in your local Blender viewport.

---

## 4. Data Flow

```text
┌──────────────────┐       stdin/stdout        ┌──────────────────┐
│   Claude Code    │ ◄══════════════════════► │  blender-mcp     │
│   (local)        │    (MCP protocol)         │  (local process) │
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

## 5. Troubleshooting

### 5.1 `claude mcp list` shows disconnected

```bash
claude mcp get blender
```

Check:
- `command` is `blender-mcp` and it's executable
- `BLENDER_MCP_HOST` is `localhost`
- `BLENDER_MCP_PORT` is `9876`

### 5.2 MCP shows connected but operations fail with "Cannot connect to Blender"

Possible causes:
1. Blender add-on not running (check for `Server is running`)
2. Online access not enabled in Blender preferences
3. The add-on's Host was changed from `localhost`

### 5.3 Connection drops after a short time

Possible causes:
1. The Blender add-on has a 10-second idle timeout — it disconnects if no request is received
2. The `blender-mcp` process crashed (check terminal output)

---

## 6. Remove Configuration

```bash
claude mcp remove blender
claude mcp list
```

---

## 7. Security Notes

Blender MCP effectively allows the LLM to execute arbitrary Python code inside Blender. Recommendations:

1. Only use with test projects or backed-up files
2. Avoid running in environments with sensitive files
3. Review high-risk operations before confirming
4. Do not let Claude auto-execute Python code you don't understand

---

## 8. References

- Blender Lab MCP Server: https://www.blender.org/lab/mcp-server/
- Blender MCP source: `blender_mcp/` project directory
- MCP Server entry point: `mcp/blmcp/__init__.py` → `main()`
- TCP connection: `mcp/blmcp/tools_helpers/connection.py` → `send_code()`
- Add-on server: `addon/blender_mcp_addon/mcp_to_blender_server.py` → `start()`
- Claude Code MCP docs: https://docs.anthropic.com/en/docs/claude-code/mcp
