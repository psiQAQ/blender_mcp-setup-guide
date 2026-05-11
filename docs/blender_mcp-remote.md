[简体中文](./blender_mcp-remote_zh.md) | English

# Claude Code Remote Control Blender via LAN — Complete Setup Guide

> Control Blender on a remote machine over LAN from Claude Code using Blender's official MCP Server.  
> Architecture: `Claude Code (local) ⇄ (stdio or HTTP) ⇄ blender-mcp process (local) ⇄ (TCP socket) ⇄ Blender MCP Add-on (remote) ⇄ Blender Python API`
>
> For local single-machine setup, see [blender_mcp-setup_en.md](./blender_mcp-setup_en.md).

![Claude Code + Blender MCP Architecture](../assets/imgs/claude-code-mcp-blender.png)

---

## 0. Key Takeaways (Read First)

1. **Environment variables are `BLENDER_MCP_HOST` / `BLENDER_MCP_PORT`**, not `BLENDER_HOST` / `BLENDER_PORT`.  
   Source: `mcp/blmcp/tools_helpers/connection.py:27-28` uses the `_MCP` infix.

2. **`BLENDER_MCP_HOST` must be the remote Blender machine's IP**, not the Claude Code machine's IP.  
   The `blender-mcp` process is a TCP **client** that connects to the remote Blender Add-on's TCP **server**.

3. **Do NOT point Claude Code directly to the remote Blender's port 9876**.  
   Port 9876 on the Blender Add-on is a raw TCP socket, not an MCP HTTP endpoint.  
   Always run `blender-mcp` locally to bridge the connection.

4. **The remote Blender Add-on listens on `localhost` by default** — change it to `0.0.0.0` or the remote machine's LAN IP for LAN access.

5. **SSH tunneling is recommended for long-term use**.  
   Keep the remote Blender on `localhost:9876` and forward locally via `ssh -L`.

6. **Do NOT add `--` before the URL in HTTP mode registration**.  
   `--` is only used in stdio mode to separate the server name from the command.

---

## 1. Environment Assumptions

| Item | Value | Notes |
|------|-------|-------|
| Local (Claude Code) IP | `192.168.2.10` | Static IP for firewall allowlist |
| Remote (Blender) IP | `192.168.2.20` | Fill into `BLENDER_MCP_HOST` |
| Blender MCP port | `9876` | Add-on listen port, configurable |
| MCP Server HTTP port | `8000` | HTTP mode only |
| Blender version | ≥ 5.1 | Official requirement |
| Python | ≥ 3.10 | MCP Server requirement |

Check Claude Code:

```bash
claude --version
claude mcp list
```

Check connectivity to the remote machine:

```powershell
ping 192.168.2.20
```

---

## 2. Remote Machine: Install Blender MCP Add-on

### 2.1 Install Blender 5.1+

Download from [blender.org](https://www.blender.org/download/).

### 2.2 Install the Add-on

Visit [https://www.blender.org/lab/mcp-server/](https://www.blender.org/lab/mcp-server/). Two methods:

- **Drag & drop**: Drag the install link into Blender (twice: first to add the Blender Lab repo, then to install the add-on)
- **Manual**: Download the add-on zip, then `Edit → Preferences → Add-ons → Install from Disk`

> Drag & drop enables update notifications.

### 2.3 Enable the Add-on

```text
Edit → Preferences → Add-ons → Search "MCP"
```

Confirm the add-on is enabled.

### 2.4 Change Host to LAN-accessible (Critical)

Default configuration:

```text
Host = localhost
Port = 9876
```

This won't work over LAN since `localhost` only accepts local connections. Change to:

```text
Host = 0.0.0.0
Port = 9876
```

Or specify the remote machine's LAN IP:

```text
Host = 192.168.2.20
Port = 9876
```

Path: `Edit → Preferences → Add-ons → Find Blender MCP → Expand settings → Edit Host field`

After changing, click **Start Server** (or restart Blender for Auto Start). Confirm:

```text
Server is running
```

> You need to Stop then Start the server for the Host change to take effect.

### 2.5 Enable Online Access

Blender 5.1+ requires online access permission:

```text
Edit → Preferences → System → Online Access → Enable
```

Without this, the add-on will error: `Online access must be enabled in the system preferences`.

---

## 3. Remote Machine: Configure Firewall

### 3.1 Windows Firewall

Open PowerShell as **administrator**. Check the network profile:

```powershell
Get-NetConnectionProfile
```

If identified as `Public`, firewall rules with `-Profile Private` may not apply. If the LAN is trusted, switch to Private:

```powershell
Set-NetConnectionProfile -InterfaceAlias "your WiFi name" -NetworkCategory Private
```

Add a firewall rule:

```powershell
# Recommended: allow only the Claude Code machine
New-NetFirewallRule `
  -DisplayName "Blender MCP 9876 - Claude Code Only" `
  -Direction Inbound `
  -Action Allow `
  -Protocol TCP `
  -LocalPort 9876 `
  -RemoteAddress 192.168.2.10 `
  -Profile Private
```

If the Claude Code machine doesn't have a static IP yet, allow the whole subnet temporarily:

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

Verify the port is listening:

```powershell
netstat -ano | findstr :9876
```

Expected output:

```text
TCP    0.0.0.0:9876          0.0.0.0:0              LISTENING       12345
```

### 3.2 Linux Firewall (UFW)

```bash
# Recommended: allow only the Claude Code machine
sudo ufw allow from 192.168.2.10 to any port 9876 proto tcp
sudo ufw status
```

Verify:

```bash
ss -lntp | grep 9876
```

---

## 4. Local Machine: Test Remote Connectivity

### 4.1 Windows

```powershell
Test-NetConnection 192.168.2.20 -Port 9876
```

Success:

```text
TcpTestSucceeded : True
```

### 4.2 Linux / macOS / WSL

```bash
nc -vz 192.168.2.20 9876
```

Or:

```bash
timeout 2 bash -c "cat < /dev/null > /dev/tcp/192.168.2.20/9876" && echo OK || echo FAIL
```

> Troubleshooting order if it fails:  
> 1. Is Blender running on the remote machine?  
> 2. Does the add-on show `Server is running`?  
> 3. Was the Host changed from `localhost` to `0.0.0.0`?  
> 4. Is port 9876 allowed in the firewall?  
> 5. Are both machines on the same subnet?  
> 6. Does the router have AP isolation enabled?

---

## 5. Local Machine: Install blender-mcp MCP Server

Install globally with `uv tool install` so `blender-mcp` is available as a system-wide command.

### 5.1 Prerequisites

- [uv](https://docs.astral.sh/uv/#installation) installed
- Python ≥ 3.10

```bash
uv --version
```

### 5.2 Clone the Source

```bash
cd ~/.local/share
git clone --depth 1 https://projects.blender.org/lab/blender_mcp.git
```

> `pyproject.toml` is inside `blender_mcp/mcp/`. All install commands run from `mcp/`.

### 5.3 Global Install

```bash
cd ~/.local/share/blender_mcp/mcp
uv tool install --python 3.11 .
```

Verify:

```bash
which blender-mcp
blender-mcp --help
```

> `uv tool install` places the package in uv's isolated tool directory.

### 5.4 Register with Claude Code

Claude Code auto-manages `blender-mcp` in stdio mode.

#### stdio mode (recommended)

```bash
# Remote Blender (replace IP with your remote machine's IP)
claude mcp add blender --transport stdio --scope user \
  -e BLENDER_MCP_HOST=192.168.2.20 \
  -e BLENDER_MCP_PORT=9876 \
  -- blender-mcp

# Local mode (Blender + MCP on the same machine)
claude mcp add blender --transport stdio --scope user \
  -e BLENDER_MCP_HOST=localhost \
  -e BLENDER_MCP_PORT=9876 \
  -- blender-mcp
```

> **Environment variables**: `BLENDER_MCP_HOST` (with `_MCP` infix), not `BLENDER_HOST`.  
> **Option order**: `--transport`, `-e`/`--env`, `--scope` must come after the server name and before `--`.

Verify:

```bash
claude mcp get blender
```

Should show `Status: ✓ Connected` with correct environment variables.

#### http mode

Start the HTTP service manually (keep the process running):

```bash
BLENDER_MCP_HOST=192.168.2.20 BLENDER_MCP_PORT=9876 blender-mcp --transport http --host 127.0.0.1 --port 8000
```

Then register in another terminal (no `--` before the URL):

```bash
claude mcp add --transport http --scope user blender http://127.0.0.1:8000/
```

#### Mode comparison

| Feature | stdio mode | HTTP mode |
|---------|-----------|----------|
| Startup | Auto by Claude Code | Manual, must keep running |
| Process management | Managed by Claude Code | Manual |
| Environment variables | Via `-e` flag | Set manually before startup |
| Stability | High | Medium (process may exit) |
| Multi-client | No (exclusive) | Yes (shared endpoint) |
| Use case | Daily use (recommended) | Browser-based access |
| Network exposure | None (local IPC) | `127.0.0.1:8000` local HTTP |

### 5.5 Updating (git pull compatible)

```bash
cd ~/.local/share/blender_mcp

# First time only: set upstream tracking
git branch --set-upstream-to=origin/main main

# Pull latest code
git pull

# Reinstall
cd mcp && uv tool install --reinstall .

# Verify
blender-mcp --help
```

> **Why `--reinstall` instead of `upgrade`**: Installed from a local path, not PyPI. `--reinstall` forces a rebuild from current source.

### 5.6 Uninstalling

```bash
# 1. Remove MCP server registration
claude mcp remove blender -s local
claude mcp remove blender -s user

# 2. Uninstall the tool
uv tool uninstall blender-mcp

# 3. Optionally delete source
rm -rf ~/.local/share/blender_mcp
```

---

## 6. Connection Test

### 6.1 Check MCP Status

Start Claude Code:

```bash
claude
```

Then type:

```text
/mcp
```

Confirm `blender` shows as **connected**.

### 6.2 Test: Read Scene

```text
Use blender MCP to read the object list from the current Blender scene.
```

### 6.3 Test: Create an Object

```text
Use blender MCP to create a cube named MCP_Test_Cube at position (0, 0, 1) with size 1, and add a blue material to it.
```

If successful, the new cube should appear in the remote Blender viewport.

### 6.4 Raw TCP Test

If MCP shows connected but operations fail, test the TCP socket directly:

```powershell
# Windows PowerShell
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
    if ($client) { $client.Close() }
}
```

---

## 7. Data Flow Diagrams

### stdio mode

```text
┌──────────────────┐       stdin/stdout        ┌──────────────────┐
│   Claude Code    │ ◄══════════════════════► │  blender-mcp     │
│   (local)        │    (MCP protocol)         │  (local process) │
└──────────────────┘                           └────────┬─────────┘
                                                        │
                                                 TCP socket
                                             BLENDER_MCP_HOST
                                             BLENDER_MCP_PORT
                                                        │
                                                        ▼
                                              ┌──────────────────┐
                                              │  Blender Add-on  │
                                              │  (remote)         │
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

### HTTP mode

```text
┌──────────────────┐       HTTP            ┌──────────────────┐
│   Claude Code    │ ◄══════════════════► │  blender-mcp     │
│   (local)        │  127.0.0.1:8000      │  (local process) │
└──────────────────┘  (MCP Streamable HTTP) └────────┬─────────┘
                                                        │
                                                 TCP socket
                                             BLENDER_MCP_HOST
                                             BLENDER_MCP_PORT
                                                        │
                                                        ▼
                                              ┌──────────────────┐
                                              │  Blender Add-on  │
                                              │  (remote)         │
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

## 8. More Secure Alternative: SSH Tunneling

If you don't want to expose the Blender port to the LAN, use SSH tunneling. The remote Blender stays on `localhost` and the local machine forwards via SSH.

### 8.1 Remote Blender Configuration

```text
Host = localhost
Port = 9876
```

No need to change Host or open firewall port 9876.

### 8.2 Establish SSH Tunnel (local machine)

```bash
ssh -N -L 9876:127.0.0.1:9876 user@192.168.2.20
```

Windows (OpenSSH, built-in on Windows 10+):

```powershell
ssh -N -L 9876:127.0.0.1:9876 user@192.168.2.20
```

### 8.3 Claude Code Registration

```bash
claude mcp add blender -e BLENDER_MCP_HOST=127.0.0.1 -e BLENDER_MCP_PORT=9876 -- blender-mcp
```

The `blender-mcp` connects to `127.0.0.1:9876` locally, and the SSH tunnel forwards traffic to the remote machine.

### 8.4 Direct vs SSH Tunnel Comparison

| Item | Direct (expose 9876) | SSH Tunnel |
|------|:---:|:---:|
| Other LAN devices can access Blender | Yes | No |
| Firewall port 9876 required | Yes | No |
| Remote Blender listens on localhost | No | Yes |
| Security | Lower | Higher |
| Configuration complexity | Low | Medium |
| Recommended for | Quick tests | Long-term use |

---

## 9. Troubleshooting

### 9.1 `claude mcp list` shows disconnected

```bash
claude mcp get blender
```

Check:
- `command` is `blender-mcp` and executable
- `BLENDER_MCP_HOST` is the remote Blender machine's IP
- `BLENDER_MCP_PORT` is `9876`
- Environment variable names have the `_MCP` infix

### 9.2 MCP connected but "Cannot connect to Blender"

Possible causes:
1. Remote Blender add-on not running (check `Server is running`)
2. `BLENDER_MCP_HOST` still points to `localhost` instead of the remote IP
3. Remote Blender Host is still `localhost`, not `0.0.0.0`
4. Remote firewall blocking port 9876
5. Online access not enabled in Blender

### 9.3 Connection drops quickly

Possible causes:
1. Blender Add-on has a 10-second idle timeout
2. `blender-mcp` process crashed

### 9.4 Windows path with spaces

Quote the full path:

```powershell
claude mcp add --transport stdio --scope user blender -- "C:\path with spaces\blender-mcp.exe"
```

### 9.5 HTTP mode connection fails

Check:
1. `blender-mcp --transport http` process is running
2. Port 8000 is not occupied
3. The registered URL has a trailing slash: `http://127.0.0.1:8000/`

---

## 10. Remove Configuration

```bash
claude mcp remove blender
claude mcp list
```

---

## 11. Security Notes

Blender MCP effectively allows the LLM to execute arbitrary Python code inside Blender. Recommendations:

1. Only use with test projects or backed-up files
2. Avoid running in environments with sensitive files
3. Do not expose port 9876 to the public internet
4. Restrict source IP/subnet for LAN direct connections
5. Prefer SSH tunneling for long-term use
6. Review high-risk operations before confirming
7. Do not let Claude auto-execute Python code you don't understand

---

## 12. Quick Reference

### Long-term use (SSH tunnel, recommended)

```text
Remote Blender:
  Add-on Host = localhost
  Add-on Port = 9876
  Firewall: no port 9876 needed

Local machine:
  ssh -N -L 9876:127.0.0.1:9876 user@192.168.2.20

Claude Code MCP registration:
  claude mcp add blender -e BLENDER_MCP_HOST=127.0.0.1 -e BLENDER_MCP_PORT=9876 -- blender-mcp
```

### Quick test (direct LAN)

```text
Claude Code machine IP:   192.168.2.10
Remote Blender IP:        192.168.2.20
Remote Add-on Host:       0.0.0.0
Remote Add-on Port:       9876
Remote firewall:          allow 192.168.2.10 only

Claude Code MCP registration:
  see stdio mode commands in section 5.4
```

### Not recommended

```text
Do NOT point Claude Code directly to:
  http://192.168.2.20:9876/mcp

Reason:
  9876 is the Blender Add-on's raw TCP socket, not an MCP HTTP endpoint.
```

---

## 13. References

- Blender Lab MCP Server: https://www.blender.org/lab/mcp-server/
- Blender MCP source: `blender_mcp/` project directory
- MCP Server entry point: `mcp/blmcp/__init__.py` → `main()`
- TCP connection: `mcp/blmcp/tools_helpers/connection.py` → `send_code()`
- Add-on server: `addon/blender_mcp_addon/mcp_to_blender_server.py` → `start()`
- Claude Code MCP docs: https://docs.anthropic.com/en/docs/claude-code/mcp
