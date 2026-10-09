# 历史截图与 SDK 超时的定向诊断

2026-10-09，Windows x64，Blender 5.1.1 与 5.2.2 LTS。候选包来源与 SHA-256 见[完整工具检查](mcp-tool-checks.md)。本轮只增加诊断入口，没有修改产品源码、候选 ZIP、系统 Blender 或用户配置。

| 问题 | 当前判断 | 状态 |
| --- | --- | --- |
| `search_api_docs` 长时间等待后报 SDK 超时 | 原测试客户端没有设置 HTTPX 超时，实际读取期限为 5 秒；冷搜索超过此期限。真实调用复现，单变量修改后通过 | 超时机制已定位；显式配置读取期限的复测 Passed |
| 缩略图文件已生成，SDK 仍报超时 | 同一客户端期限可以产生此现象；实际渲染完成前 HTTP 流已断开。真实慢渲染复现，单变量修改后通过 | 机制已定位；历史那次 EEVEE 渲染没有服务耗时记录，无法逐事件回填 |
| 窗口截图全黑 | 两张历史 PNG 的 RGB 确实全为零；当前旧包与新包、两种图形后端及窗口状态检查均未复现 | 原因未确认，未标为修复 |
| 原生安装重命名拒绝的剩余归因 | 新增一次管理员记录、普通权限安装的跟踪，12 次中 3 次失败，记录没有丢失事件；失败期间捕获到 Codex 打开子目录 | 支持短时外部访问竞争；永久修复和具体内核拒绝来源未确认，见[目录诊断](native-install-diagnosis.md) |

## HTTP 期限与 SDK 期限

从本任务原始诊断补丁恢复了旧客户端的配置，记录时间为 `2026-10-08T23:47:48.579Z`。AST 核对发现 `httpx.AsyncClient` 只设置了 `headers` 与 `trust_env`，没有 `timeout`；`ClientSession` 则设置了 180 秒。恢复来源和解析结果保存在 `build/latest/mcp-response-diagnosis-summary.json`，没有导出令牌或请求头。

实际随包 HTTPX 的 `_config.py` 定义 `DEFAULT_TIMEOUT_CONFIG = Timeout(timeout=5.0)`。传给 MCP SDK 的自定义 HTTP 客户端保留此值，SDK 的 180 秒期限不会将其改成 180 秒。

实际随包 MCP Python SDK 为 1.30.0。`mcp/client/streamable_http.py` 的 `_handle_sse_response` 捕获读取异常后只输出 debug 日志；没有收到事件 ID 时也不会恢复该请求。于是 HTTP 在约 5 秒时发生 `ReadTimeout`，服务仍然执行并产生结果，而调用方最后只看到 SDK 自己的等待期限耗尽。

诊断将 SDK 期限固定为 30 秒以缩短复现，只改变 HTTP 读取期限。以下均调用真实 GUI、服务、HTTP 流和 SDK；服务计时只注入一次性安装副本。

| 实际场景 | HTTP 读取期限 | 服务执行耗时 | SDK 结果 |
| --- | --- | --- | --- |
| 历史 EEVEE 设置，冷 API 搜索 | 5 秒 | 6.508 秒 | HTTP 约 5.004 秒断开，SDK 约 30.035 秒超时 |
| CPU Cycles 64 samples，冷 API 搜索 | 5 秒 | 6.342 秒 | 超时 |
| 同一 CPU Cycles 设置，缩略图渲染 | 5 秒 | 7.056 秒 | HTTP 约 5.043 秒断开，SDK 超时；实际 PNG 已存在 |
| 同一 CPU Cycles 设置，冷 API 搜索 | 60 秒 | 6.174 秒 | Passed |
| 同一 CPU Cycles 设置，缩略图渲染 | 60 秒 | 7.007 秒 | Passed |

对应报告为 `mcp-response-5.2-http5-tests.json`、`mcp-response-5.2-http5-render-tests.json` 和 `mcp-response-5.2-http60-render-tests.json`。失败的慢渲染确实生成了 1,597,676 字节 PNG，SHA-256 为 `72088978f70582032206504072a0e8ec1976b38eb6669e78003c4eaae39fd15b`，结束后 `render_running: false`。文件存在不代表该次 SDK 收到了响应。

5.1 的独立复测也通过：冷搜索约 9.067 秒、CPU 缩略图约 6.560 秒，均超过旧 HTTP 默认读取期限。本仓库的完整工具检查入口已显式设置 `timeout=60`；新诊断入口默认 HTTP read 60 秒、SDK 30 秒。应按实际工具耗时设置期限，单独增大 SDK 等待时间不能修复一个更早断开的 HTTP 流。

这里的 Passed 仅表示响应正常送达且没有 `isError`。上游缩略图尺寸错误和 `bpy.types.Object.location` 查询失败仍由完整工具用例判定为 Failed，本轮没有修复这两项。

## 黑色截图的证据边界

历史 `window.png` 与 `window-recheck.png` 均为 1920 × 1009，RGB 最小值和最大值都是 0，两份 SHA-256 相同：`d082f62d4784db6290a75e98ed3d2def968e53b21c187e30ebc0f550788fc0c2`。这确认了图片内容全黑，不能归因于查看器透明背景或传输损坏。

本轮保留了 101 次实际图像内容检查，全部含有非零且变化的 RGB 像素。覆盖范围包括：

- 5.2 历史 dev.1 ZIP 与当前 dev.2 ZIP，同一会话内按历史十工具顺序调用；5.1 当前候选另行检查。
- OpenGL 和 Vulkan；正常、最小化、恢复、最大化、隐藏、重新显示。
- MCP 图像工具与直接 `bpy.ops.screen.screenshot` 对照。
- 两个主窗口、Preferences 窗口、Render 窗口及所有窗口重绘。

用户已确认历史现场没有远程桌面、锁屏或显示器切换。历史报告中的 GUI 有两个窗口，但原进程已经关闭，未留下当时的图形后端及 framebuffer 状态。两次尝试在启动时最小化窗口，初次截图记录仍是 `minimized: false`，因此不能声称覆盖了“首次绘制之前始终最小化”的条件。后续明确处于最小化和隐藏状态的截图检查通过。

以上结果排查了若干可执行条件，未获得能够稳定产生历史黑图的现场循环。没有足够证据归责上游、集成代码或驱动，也没有以猜测修改产品。

## 复现入口与报告解释

仓库根目录的 PowerShell，使用已有解释器与候选。检查会启动自己拥有的隔离 GUI，结束后导出诊断并清理安装环境。

```powershell
$python = 'C:\Users\ustcw\miniforge3\python.exe'
$blender = 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe'
$package = 'build/latest/dist/blender_mcp_integration-1.0.2-dev.2+integration.1-windows-x64.zip'

# 复现旧客户端期限：搜索与慢渲染预期 Failed，保留真实输出文件。
& $python -B scripts/diagnose_mcp_responses.py --blender $blender --package $package --label local-http5 --historical-scene --render-samples 64 --rounds 1 --skip-window-matrix --http-read-timeout 5

# 只改变 HTTP 读取期限，验证响应送达。
& $python -B scripts/diagnose_mcp_responses.py --blender $blender --package $package --label local-http60 --historical-scene --render-samples 64 --rounds 1 --skip-window-matrix --http-read-timeout 60

# 图像内容与窗口状态矩阵。
& $python -B scripts/diagnose_mcp_responses.py --blender $blender --package $package --label local-images --historical-scene --rounds 1 --multi-window
```

服务执行日志使用 `[MCP-DIAG]` 前缀，只存在于诊断脚本与一次性服务副本。服务原文件与注入后文件的哈希保存在报告。HTTP 只记录工具名、消息 ID、时间、状态及字节数，不记录认证数据。SDK 收到结果后可以主动关闭 SSE，`eof_observed: false` 本身不是失败；旧格式报告的 `body_complete: false` 同样不能单独作为断流证据。

`mcp-response-5.2-dev1-tests.json` 的首次检查在诊断注入前置条件处失败，原因是旧文件使用 CRLF；诊断器修正换行识别后重测。dev.1 的 OpenGL/Vulkan 重测各有两次 CLI 路径失败，属于已知旧包未设置 `BLENDER_PATH` 的条件；当前 dev.2 通过。它们没有被混记为图像或超时失败。

最后复核的 `mcp-response-5.2-final-tests.json` 在官方原生安装阶段再次发生 WinError 5，尚未调用工具；Failed 报告与日志独立保留。测试入口现会在收到安装器 ERROR 后直接报告安装失败，避免下游 ModuleNotFoundError 掩盖原因。新的独立 `mcp-response-5.2-final-recheck-tests.json` 为 Passed：11 次真实调用与 1 次图像内容检查通过。独立重跑成功不会覆盖前一次安装失败。

诊断汇总保存在 `build/latest/mcp-response-diagnosis-summary.json`。独立人工 GUI 验收、修改 SDK 依赖、永久修复黑图、正式发布及外部 issue 提交均为 Not Run。
