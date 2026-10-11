# Windows 启动阶段的全黑窗口截图

2026-10-11，Windows x64、NVIDIA GeForce RTX 4070 Ti SUPER、驱动 572.83。在 Blender 5.1.1 和 5.2.2 的 OpenGL 窗口启动阶段，先将窗口最小化，再执行真实 `bpy.ops.screen.screenshot`，稳定得到全黑 PNG。恢复同一个窗口后再次截图，图像恢复正常。

这定位了一个能产生历史症状的具体机制，并验证了恢复方法。历史现场已关闭，缺少当时的最小化状态、图形后端和 GPU 上下文，因此历史两张黑图是否由同一机制导致，仍未确认。当前没有修改截图工具源码或正式集成 ZIP，也没有部署自动恢复补丁。

## 原因与影响

Blender 的截图操作会先调用 `WM_redraw_windows`，再读取窗口像素。Windows 的绘制循环明确跳过最小化窗口；支持前缓冲区读取时，截图随后读取该窗口的 front buffer。在本次 OpenGL 实验中，启动阶段最小化的窗口没有得到正常绘制，读取结果全为零，但操作仍返回 `FINISHED`。

对应官方源码：[截图调用顺序](https://raw.githubusercontent.com/blender/blender/v5.2.2/source/blender/editors/screen/screendump.cc)、[最小化跳过与像素读取分支](https://raw.githubusercontent.com/blender/blender/v5.2.2/source/blender/windowmanager/intern/wm_draw.cc)。这是结合源码和单变量实验得出的机制判断；没有记录内核级 GPU 帧计数。

MCP 窗口图像工具使用同一个截图操作，因而可能收到一个格式正确、尺寸正常但内容全黑的 PNG。JSON 窗口结构仍可读取，场景本身没有因此丢失。已经正常绘制过的窗口与普通双窗口切换在本次对照中通过，不能把所有最小化截图都判为必然失败。

## 单变量验证

探针仅操作自己启动的隔离 Blender，使用真实 GUI、Win32 窗口状态和实际 PNG 像素，没有清空 framebuffer 或构造黑图。最小化用例在截图前后均核验同一 PID/HWND 的 `IsIconic=True`。

| 条件 | 状态 | 观察 |
| --- | --- | --- |
| 5.1.1 OpenGL、5.2.2 OpenGL/Vulkan，正常启动和双窗口切换 | Passed | 每组 10 张，共 30 张正常图像 |
| 5.1.1 / 5.2.2 OpenGL，启动阶段最小化 | Failed，符合复现预期 | 两版首次截图均全黑；恢复并重绘后各 10 张通过 |
| 5.2.2 OpenGL，保持最小化并调用 `DRAW_WIN_SWAP` | Failed，符合复现预期 | 仍全黑，重绘调用无法消除窗口状态条件 |
| 5.2.2 OpenGL，保持最小化并经过 0.5 秒事件循环 | Failed，符合复现预期 | 仍全黑，单纯等待不能恢复 |
| 同一 5.2.2 OpenGL 进程，仅恢复窗口，再直接截图 | Passed | 无需额外显式重绘即恢复；从恢复起的 11 张图像均正常 |
| 5.2.2 Vulkan，同一最小化与恢复流程 | Failed，符合空白图复现预期 | 最小化时三张纯深灰，RGB 均约 0.0941；恢复后 11 张正常 |
| 5.2.2 当前集成包，按历史顺序及多窗口调用 | Passed | 19 次实际 MCP 调用正常送达，5 张图像正常；不代表所有工具语义通过 |
| 当前包真实 MCP 截图，正常窗口 | Passed | 原始 PNG、工具输出和客户端收到的 PNG 逐字节一致 |
| 当前包真实 MCP 截图，启动阶段最小化后恢复 | Failed，符合复现预期 | 最小化时两张近乎全黑图均被内容检查拒绝；恢复后通过，三个请求的原始与输出 PNG 均逐字节一致 |
| 历史那次故障的唯一因果归属 | Not Run | 当时缺失的窗口/GPU 状态无法事后补测 |
| 独立人工 GUI 验收 | Not Run | 上述均为自动操作的真实 GUI 检查 |

5.2.2 OpenGL 复现图为 1920 × 1009，RGB 最小值和最大值均为 0，SHA-256 为 `d082f62d4784db6290a75e98ed3d2def968e53b21c187e30ebc0f550788fc0c2`，与历史两张 PNG 逐字节一致。相同尺寸的全黑图片可以来自不同原因，因此哈希一致只确认症状一致。

Vulkan 初版报告只按 RGB 非零判定，误将三张纯深灰图标为 Passed。目视检查与已保存的 `rgb_minimum == rgb_maximum` 暴露了这一门槛缺陷。随后真实 MCP 重复截图中还出现了少量亮点，单靠最大值与最小值之差也会误判。当前内容检查同时要求 RGB 范围大于 0.1，以及各颜色通道偏离其众数的分量比例大于 1%；`black_image` 仍只表示严格全零。这是本测试界面的有效内容门槛，不是通用图像质量判定。

最终 MCP 复测的两张无效图，变化比例均约为 `0.00000172`，恢复后的正常界面约为 `0.440324`。原始 PNG、工具编码后的 PNG 和客户端收到的字节均已关联核验：故障在原生截图时已经存在，这次复现没有发生传输损坏或缩图导致的内容变化。首次 MCP 复现还得到与历史相同的全零 PNG；几乎全黑但带少量亮点的后续样本单独保留，没有混记为严格全零。更换 Vulkan 后端也没有消除未绘制窗口的空白图。

原始历史时序还确认：第一次黑图发生在 API 搜索超时和缩略图渲染之前；重检前仅关闭了本轮新增的 Render 窗口。两次都没有记录截图所用窗口指针、最小化状态或重编码前 PNG，不能把后续渲染当作首次黑图的原因，也不能仅凭最终文件较小就断言没有发生重编码。

## 恢复方法

出现全黑窗口截图时，恢复对应 Blender 窗口，使其正常显示并完成绘制，再调用截图工具。本次在相同 OpenGL 进程中验证了这一方法；仅在最小化状态反复调用重绘或等待没有效果。

自动化启动时，应让目标窗口完成一次正常绘制，再接受截图请求。对返回的 PNG 检查实际 RGB 内容，不能只依据 `FINISHED`、MCP 成功状态或文件存在判定截图可用。若恢复后仍黑，应保留当次图像与窗口/GPU 状态；本次实验没有证明此方法覆盖所有黑图原因。

## 复现与报告

在仓库根目录的 PowerShell 中运行。脚本会启动并退出自己的 Blender；与其他项目需要独占 Blender 的验收串行运行。

```powershell
$python = 'C:\Users\ustcw\miniforge3\python.exe'
$blender = 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe'

# 正常启动、首次 timer、两个窗口交替截图。
& $python -B scripts/diagnose_screenshot_startup.py `
    --blender $blender --label normal-opengl --gpu-backend opengl

# 预期 Failed：保留三张真实黑图，随后验证恢复后的正常图像。
& $python -B scripts/diagnose_screenshot_startup.py `
    --blender $blender --label early-minimized --gpu-backend opengl --early-minimized

# 只改变图形后端，其他步骤保持一致。
& $python -B scripts/diagnose_screenshot_startup.py `
    --blender $blender --label early-minimized-vulkan --gpu-backend vulkan --early-minimized

# 真实 MCP 调用：保留原图/输出及窗口状态，再恢复自身窗口并重试。
$package = 'build/latest/validated/blender-5.2/windows-x64/dist/blender_mcp_integration-1.0.2-dev.2+integration.1-windows-x64.zip'
& $python -B scripts/diagnose_mcp_responses.py `
    --blender $blender --package $package --label black-min-check `
    --rounds 2 --screenshot-only --skip-initial-redraw --early-minimized
```

`--screenshot-only` 跳过历史十工具和渲染流程，但仍会先读取运行信息并重读历史 PNG 像素。诊断只修改本次隔离安装副本，截图、缩图和 Base64 编码顺序保持不变；像素分析在编码完成后执行。报告记录实际窗口、GPU/WGL、源图和输出图，不能把这类插入观测的重复调用视为完全没有扰动。

当前证据保存在：

- `build/latest/screenshot-startup-5.1-opengl-tests.json`、`screenshot-startup-5.2-opengl-tests.json` 和 `screenshot-startup-5.2-vulkan-tests.json`：正常启动对照。
- `build/latest/screenshot-startup-5.1-early-minimized-tests.json` 与 `screenshot-startup-5.2-early-minimized-tests.json`：首次失败与恢复。
- `build/latest/screenshot-startup-5.2-minimized-timing-tests.json`：最小化时重绘、事件循环等待及恢复的逐步对照。
- `build/latest/screenshot-startup-5.2-minimized-vulkan-tests.json`：Vulkan 单变量对照。
- `build/latest/screenshot-startup-5.2-minimized-vulkan-content-tests.json`：修正内容门槛后的实际 Vulkan 复测，前三张纯灰 Failed，恢复后 11 张 Passed。
- `build/latest/screenshot-content-audit-tests.json`：重读 80 张已保存的像素统计，记录 5 张全黑、3 张纯深灰及初版门槛的 3 次误报；没有把这次审计记成新的 GUI 运行。
- `build/latest/mcp-response-black-resume-baseline-tests.json`：当前包的实际 MCP 基线。
- `build/latest/mcp-response-black-observed-normal-tests.json`：正常 MCP 截图的原图/输出观测。
- `build/latest/mcp-response-black-observed-minimized-tests.json`：首次 MCP 复现与恢复，包含旧范围门槛误判的稀疏亮点样本。
- `build/latest/mcp-response-black-min-check-tests.json`：最终空间变化门槛的实际 MCP 复测；前两张 Failed、恢复后 Passed，宿主正常退出。
- `build/latest/evidence/screenshot-startup-<标签>/`：逐张 PNG 和 Blender 日志。

报告绑定探针和外层脚本的 SHA-256。包含黑图的检查保持 `Failed`，恢复成功单独记录在后续 case 中。首次外层程序曾过早读取尚未完成的报告，误报失败；该诊断保留在 `evidence/failed-checks/`，修正为等待宿主退出再读取最终报告后，正常 OpenGL 组通过。运行环境导出后清理。

`mcp-response-black-observed-minimized-spatial-tests.json` 在服务启动时因较长运行路径下的临时会话文件创建报 `FileNotFoundError`，没有调用截图工具；该 Failed 记录独立保留。只缩短诊断标签后，最终 `black-min-check` 完成。复现命令使用较短标签，不将这次启动失败混入截图结果。
