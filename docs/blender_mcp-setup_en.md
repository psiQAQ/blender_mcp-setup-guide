[简体中文](./blender_mcp-setup_zh.md) | English

# Install the Blender MCP integrated Extension

This package targets **Windows x64, Linux x64, macOS Apple Silicon and Blender 5.1 stable or 5.2 preview with bundled CPython 3.13**, with the client and Blender on the same computer. The 5.1 line uses official v1.0.3; the 5.2 preview uses a pinned official main snapshot. Packages include MCP, dependencies and documentation; users do not need separate uv or Python. Blender 5.0 uses Python 3.11 and is incompatible; see [the official 5.0 source](https://github.com/blender/blender/blob/v5.0.0/build_files/build_environment/cmake/versions.cmake) and [5.1 release notes](https://www.blender.org/download/releases/5-1/).

| Blender range | Package version | Online update index |
| --- | --- | --- |
| 5.1.0 ≤ version < 5.2.0 | `1.0.3+integration.1`, stable | `https://notes.psiqaq.cn/blender_mcp-setup-guide/index.json` |
| 5.2.0 ≤ version < 5.3.0 | `1.0.2-dev.1+integration.1`, preview | `https://notes.psiqaq.cn/blender_mcp-setup-guide/blender-5.2/preview/index.json` |

For a client-managed official MCP process, use the separate [official stdio guide](blender_mcp-stdio-setup_en.md). The [README](../README.md) compares the two methods.

```mermaid
flowchart LR
    Client[Codex / Claude Code / OpenCode] -->|Local HTTP + Bearer token| Service[Bundled MCP service]
    Service -->|Local TCP 9876 + bridge credential| Blender[Blender Extension]
```

## 1. Obtain and install the package

1. Obtain the compatible `blender_mcp_integration-<version>-<platform>.zip` using the table, choosing `windows-x64`, `linux-x64` or `macos-arm64`. Download it from [Releases](https://github.com/psiQAQ/blender_mcp-setup-guide/releases); choose the **Pre-release** for Blender 5.2. Install the platform ZIP; the evidence ZIP is for auditing.
2. In Blender, open **Edit → Preferences → Add-ons → top-right menu → Install from Disk**, select the ZIP, then install and enable **Blender MCP Integrated**.
3. Expand its preferences. Stop and disable the original **MCP** Extension before starting the integration if both are installed, to avoid bridge-port conflicts.

Local ZIP installation is sufficient. Alternatively, add the matching index from the table under **Extensions → Repositories → Add Remote Repository**; Blender selects the matching platform package and offers updates. If Blender 5.1 and 5.2 share an extension directory, create a separate preview repository for 5.2. Online installation and updates require **Preferences → System → Network → Allow Online Access**.

## 2. Start the service and copy its configuration

**Start MCP When Enabled** is on by default; **Start MCP** also starts the service manually. Wait for **MCP: Running**, then use **Check Connection** to check HTTP health and the Blender bridge.

Choose your client in **Agent** and click **Copy Connection Configuration**. This copies the settings to the clipboard and saves `client-config.txt` in the user directory shown in preferences. That directory also contains `service.log` and the HTTP credential; these user files survive package upgrades.

| Setting | Default | Purpose |
| --- | --- | --- |
| HTTP Port | `8000` | Client URL `http://127.0.0.1:8000/` |
| Bridge Port | `9876` | Communication between the bundled service and Blender |
| Authorization | `Bearer <locally generated token>` | HTTP authentication |

Replace `YOUR_BLENDER_MCP_TOKEN` below with the actual copied token. Prefer the generated configuration. Clients use the root path `/`; port `9876` belongs to the bridge. Copy settings again after changing the HTTP port. Keep local credentials out of Git.

## 3. Configure your client

Complete only your client's subsection. Merge the `blender` entry into existing settings while preserving other servers. Replace an existing entry with the same name. When switching from stdio, remove the old entry using [section 5](#5-switch-methods-or-uninstall).

### 3.1 Codex

User settings are in `%USERPROFILE%\.codex\config.toml` on Windows or `~/.codex/config.toml` on Linux/macOS, for example `C:\Users\Alice\.codex\config.toml`. A trusted project's `.codex/config.toml` provides project scope. Create the directory/file if needed, then add:

```toml
[mcp_servers.blender]
enabled = true
url = "http://127.0.0.1:8000/"
http_headers = { Authorization = "Bearer YOUR_BLENDER_MCP_TOKEN" }
```

Save and start a new Codex CLI session, or reload servers in the desktop client's MCP settings. The CLI can inspect the loaded configuration:

```text
codex mcp list
codex mcp get blender
```

Check the HTTP URL and `Authorization` header. Configuration inspection still needs the actual scene check in section 4. See [official OpenAI MCP documentation](https://developers.openai.com/codex/mcp/) for fields and scope.

### 3.2 Claude Code

**Project configuration**: create or merge `.mcp.json` at the root of the project where you launch Claude Code:

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

**User configuration**: alternatively, the following command works in PowerShell and Bash and registers the server across projects in `~/.claude.json`. Choose this scope or the project file:

```text
claude mcp add --transport http --scope user blender http://127.0.0.1:8000/ --header "Authorization: Bearer YOUR_BLENDER_MCP_TOKEN"
```

Check from the relevant project, then start a new session:

```text
claude mcp list
claude mcp get blender
claude
```

Approve a project-scoped server when prompted. Enter `/mcp` in Claude Code to inspect connections, then read the scene as described in section 4. See [Claude Code's official MCP documentation](https://code.claude.com/docs/en/mcp).

### 3.3 OpenCode

User settings are in `%USERPROFILE%\.config\opencode\opencode.json` on Windows or `~/.config/opencode/opencode.json` on Linux/macOS; a project's root `opencode.json` is also supported. Merge:

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

`remote` selects HTTP even for a local service. This example adds explicit `enabled` and `oauth: false` settings to the exported configuration and uses the integration's Bearer token.

Save, restart OpenCode, and check from the same project:

```text
opencode mcp list
```

Then read the scene using section 4. See [OpenCode configuration](https://opencode.ai/docs/config/) and [MCP fields](https://opencode.ai/docs/mcp-servers/).

## 4. Verify communication and diagnose errors

Keep Blender open with the service **Running**. Start with a read-only request:

> Use blender MCP to read Blender's version and the current scene object list. Report the actual returned data.

The result must match your running Blender. For a write check, use a backed-up test scene:

> Create a cube named MCP_Test_Cube, read its position, delete that test object and verify that the object count is restored.

Loaded client settings, HTTP health and successful scene calls are separate checks. To inspect HTTP health in PowerShell, replace the token and use the port from preferences:

```powershell
$token = 'YOUR_BLENDER_MCP_TOKEN'
Invoke-RestMethod -Uri 'http://127.0.0.1:8000/health' -Headers @{ Authorization = "Bearer $token" }
```

| Symptom | Check or action |
| --- | --- |
| Service does not reach Running | Matching package platform and native architecture, Blender 5.1.x / CPython 3.13; preferences error and `service.log` |
| Occupied port | Stop the known previous service, or stop the integration, select free ports, restart and copy settings again |
| HTTP 401 | Copy the actual token again; check `Authorization` and the `Bearer ` prefix |
| HTTP 403 | Use `http://127.0.0.1:<HTTP Port>/`; check Host / Origin |
| blender configuration missing | Check the actual file and user/project scope; restart the client and trust project settings where required |
| Connected but scene calls fail | Check the bridge, original Extension conflict and actual logged error |
| Service exited | Read the log, use Stop MCP and restart, then retry a scene call |

The integration supports native loopback on all three target platforms. WSL, SSH and container clients require a separate check of execution location and network reachability.

## 5. Switch methods or uninstall

Before switching to official stdio, use **Stop MCP**, disable the integration and remove its HTTP entry. Then follow the [stdio guide](blender_mcp-stdio-setup_en.md).

- Codex: remove `[mcp_servers.blender]` and its subtables from the chosen file. A CLI-registered user entry can be removed with `codex mcp remove blender`.
- Claude Code: remove only `mcpServers.blender` from `.mcp.json`, or run `claude mcp remove --scope user blender` for user registration.
- OpenCode: remove only `mcp.blender` from the chosen file.

To uninstall completely, stop, disable and uninstall **Blender MCP Integrated** in Blender. Its separate user directory contains logs, credentials and exported settings; handle those files after confirming they are no longer needed.

See [build instructions](integration-build.md) and [local validation evidence](integration-validation.md) for implementation checks.
