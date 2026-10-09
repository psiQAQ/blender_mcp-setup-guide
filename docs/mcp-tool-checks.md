# 双版本 MCP 工具检查

2026-10-09，在 Windows x64 上使用 Blender 5.1.1 / Python 3.13.9 和 Blender 5.2.2 LTS / Python 3.13.13，分别通过真实 HTTP MCP SDK 调用服务公布的全部 26 个工具。每个工具单独建立 SDK 会话；另测同一会话连续 33 次调用。Blender 使用隔离配置、真实 GUI、随机本机端口和一次性场景，结束后清理运行环境。

当前两个候选包的常规用例均为 **25 Passed / 1 Failed**。失败项为上游缩略图输出尺寸；另一个参数边界是上游 API 类成员查询失败。5.1 已发布包的 6 个 CLI 工具失败，使用当前集成代码构建的 5.1 本地候选已全部通过这 6 项。历史 SDK 超时已定位到旧测试客户端的 HTTP 读取期限，见[响应与截图诊断](mcp-response-diagnosis.md)。原生安装仍有 WinError 5，新跟踪捕获到失败期间的 Codex 子目录访问，详见[目录诊断](native-install-diagnosis.md)。

## 成果来源

| 对象 | 版本与来源 | ZIP SHA-256 |
| --- | --- | --- |
| 5.1 已发布基线 | `1.0.3+integration.1`，上游 v1.0.3 / `2cea8d566dde07fbac28a61d698909d69724e853` | `447c482f87c8a597e174d31b06a38bb61891212963c2c813adfd39f6c80d4d2c` |
| 5.1 本地候选 | `1.0.3+integration.2`，同一上游，当前集成源码 | `0c08933ad2e9cb32ea974120b9519705b78c21ace0d30081431e0abde64b4e25` |
| 5.2 本地候选 | `1.0.2-dev.2+integration.1`，上游 `dbbf836ad4b1025f14a2b3b504c43903f39e0b04` | `85acceb703ad52bcacd412e0991c84c3c3c424fd616826dacc04e8d97325ca23` |

候选位于 `build/latest/dist/`，5.1 位于其 `blender-5.1/` 子目录。来源提交为 `39342f8349618b4486b606e85955cf9fe6423310`；5.1 候选 provenance 标记 `integration_dirty: true`。这些包用于本地验证，本次没有发布安装包、提交代码、推送或提交外部 issue。

5.1 发布基线缓存位于 `build/latest/inputs/mcp-tools/blender-5.1-windows-x64/<SHA-256>/stable.zip`。5.1 候选使用当前仓库已有的 Windows wheel 锁，没有添加依赖或更新 wheel 锁。双版本候选分别通过官方 `extension validate`。

## 全部工具结果

以下列对应 `mcp-tools-5.1-fixed-tests.json` 与 `mcp-tools-5.2-complete-tests.json`。`mcp-tools-5.1-upstream-recheck-tests.json`、`mcp-tools-5.2-upstream-tests.json` 使用同一候选，但把测试配置内的两份桥接文件换成固定提交的原始上游内容；其常规结果同样是 25 / 26 通过。

| 工具 | 5.1 本地候选 | 5.2 本地候选 | 检查内容 |
| --- | --- | --- | --- |
| `execute_blender_code` | Passed | Passed | 创建对象、检查属性、删除后恢复对象数 |
| `execute_blender_code_for_cli` | Passed | Passed | 真实后台 Blender 的版本、二进制路径与场景标记 |
| `get_blendfile_summary_datablocks` | Passed | Passed | 真实 4 个对象 |
| `get_blendfile_summary_datablocks_for_cli` | Passed | Passed | 已保存文件中的 4 个对象 |
| `get_blendfile_summary_missing_files` | Passed | Passed | 实际缺失图片 |
| `get_blendfile_summary_missing_files_for_cli` | Passed | Passed | 保存并保留 fake user 的实际缺失图片 |
| `get_blendfile_summary_of_linked_libraries` | Passed | Passed | 实际链接的 library 与对象 |
| `get_blendfile_summary_of_linked_libraries_for_cli` | Passed | Passed | 后台读取同一 library |
| `get_blendfile_summary_path_info` | Passed | Passed | 保存状态与文件路径 |
| `get_blendfile_summary_path_info_for_cli` | Passed | Passed | 后台读取保存状态与文件路径 |
| `get_blendfile_summary_usage_guess` | Passed | Passed | Modeling / Animation 结果 |
| `get_blendfile_summary_usage_guess_for_cli` | Passed | Passed | 后台场景的相同结果 |
| `get_objects_summary` | Passed | Passed | Cube 与 LinkedFixture 对象 |
| `get_object_detail_summary` | Passed | Passed | Cube 的 MESH 类型与属性 |
| `get_python_api_docs` | Passed / Failed | Passed / Failed | 操作符查询通过；类成员参数失败，见下文 |
| `search_api_docs` | Passed | Passed | 实际 API 文档命中 |
| `search_manual_docs` | Passed | Passed | 实际手册命中 |
| `get_screenshot_of_window_as_json` | Passed | Passed | 窗口、场景与区域信息 |
| `get_screenshot_of_area_as_image` | Passed | Passed | PNG 解码、尺寸与 RGB 像素变化 |
| `get_screenshot_of_window_as_image` | Passed | Passed | PNG 解码、尺寸与 RGB 像素变化 |
| `jump_to_tab_by_name` | Passed | Passed | 实际切到 Modeling workspace |
| `jump_to_tab_by_space_type` | Passed | Passed | 目标 VIEW_3D 区域存在 |
| `jump_to_view3d_object_by_name` | Passed | Passed | 实际活动对象为 Cube |
| `jump_to_view3d_object_data_by_name` | Passed | Passed | 实际活动对象及 VIEW_3D 区域 |
| `render_thumbnail_to_path` | Failed | Failed | 期望最长边 ≤ 320，实际 PNG 为 400 × 300 |
| `render_viewport_to_path` | Passed | Passed | 实际 PNG 为 400 × 300，像素有可见内容 |

这些是单个真实场景中的自动化用例，不能代表所有参数和所有 Blender 状态均已覆盖。人工 GUI 操作验收、其他系统、最低兼容 Blender 版本、完整发布与远端 CI 属于 Not Run。

## 失败尝试与责任判断

全部原始尝试保存在最新报告及日志中；`scripts/summarize_mcp_tools.py` 生成 `build/latest/mcp-tool-failures.json`，保留最终恢复为 Passed 的历史错误字段。完整工具检查的历史汇总包含 10 份报告、23 条失败尝试，按原因归并如下。本轮另外 13 份响应/图像诊断报告由 `mcp-response-diagnosis-summary.json` 逐份列出，包括诊断前置条件失败、旧包 CLI 失败和刻意复现的 HTTP 超时。

| 失败尝试 | 证据与根因 | 处理及状态 |
| --- | --- | --- |
| 5.1 发布包的 `execute_blender_code_for_cli` 及五个 `*_for_cli` 摘要工具 | 上游 CLI 默认使用 `BLENDER_PATH`，否则调用 PATH 中的 `blender`；发布包未注入宿主路径，错误为 `Blender executable not found at 'blender'` | 当前集成运行时已设置真实 `bpy.app.binary_path`；重新构建 5.1 候选并复测，六项 Passed。已发布包仍需另行发布修复版本 |
| `render_thumbnail_to_path` 输出过大 | 两版本 GUI 均产出 400 × 300；原始桥接对照同样失败。上游 `INVOKE_DEFAULT` 异步渲染后过早恢复分辨率 | 上游问题，[issue 草稿](upstream-issues/thumbnail-deferred-render.md)。未修改上游工具 |
| `get_python_api_docs("bpy.types.Object.location")` | 两版本返回 `found: false`；RST 实际包含 location。父文件前缀被去掉后，解析器仍要求根类名 | 上游问题，[issue 草稿](upstream-issues/api-class-member-resolution.md)。`bpy.types.Object.Object.location` 临时查询通过 |
| 此前用户 GUI 的窗口截图全黑 | 历史两张 PNG 的 RGB 确为零；定向诊断中 101 次真实图像内容检查通过，含旧包、两种图形后端及多窗口 | 当前未复现，具体原因未确认。用户确认没有 RDP、锁屏或显示器切换；详见[诊断边界](mcp-response-diagnosis.md) |
| 此前 `search_api_docs` 的 SDK 会话超时 180 秒 | 旧测试客户端未设置 HTTPX 期限，默认 5 秒；实际冷搜索超过 6 秒，HTTP 先断开，SDK 随后等到自身期限 | 测试客户端配置问题。保持相同场景和 SDK 期限，只将 HTTP read 改为 60 秒后 Passed；不是 MCP 工具执行失败 |
| 此前缩略图 SDK 会话超时 180 秒 | 真实慢渲染复现：HTTP 约 5 秒断开，服务约 7 秒完成并写出 PNG，SDK 随后超时 | 同一客户端期限机制，改为 60 秒后 Passed。旧 EEVEE 那次没有完整服务计时；与仍未修复的尺寸问题分别记录 |
| 初次 5.2 CLI 缺失文件摘要为空 | 测试图片没有 fake user，保存文件时被 Blender 清除 | 修正测试夹具；GUI / CLI 缺失文件摘要均 Passed，非产品缺陷 |
| 5.1 检查启动阶段未安装扩展 | 原生安装器重命名被拒绝，后续 ModuleNotFoundError 是其结果；该次没有调用工具 | 归入宿主安装问题，见[目录诊断](native-install-diagnosis.md) |
| 诊断脚本原子写入与句柄快照错误 | 一次在每个原生消息后反复替换 JSON 导致自己的 WinError 5；另一次句柄数组长度变化触发 ValueError | 改为消息流完成后写一次、检查动态缓冲区范围；这些诊断失败没有被记为 MCP 上游失败 |

常规操作符 `bpy.ops.mesh.primitive_cube_add` 文档查询 Passed；类成员失败记录在 `probes` 中。保持同一 SDK 会话的 33 次调用验证响应送达，缩略图尺寸由独立用例验证。

## 本地检查与重现入口

PowerShell，在仓库根目录使用已有 Python。以下检查会启动自己拥有的隔离 Blender GUI，并清理该配置；不会改写用户当前配置。

```powershell
$python = 'C:\Users\ustcw\miniforge3\python.exe'
$blender = 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe'
$package = 'build/latest/dist/blender_mcp_integration-1.0.2-dev.2+integration.1-windows-x64.zip'
& $python -B scripts/test_mcp_tools.py --blender $blender --package $package --label 5.2-complete
& $python -B scripts/test_mcp_tools.py --blender $blender --package $package --label 5.2-upstream --official-bridge
& $python -B scripts/summarize_mcp_tools.py
```

5.1 改用 `Blender 5.1/blender.exe`、对应候选包及独立 label。预期工具/API 问题仍存在时，脚本退出码为 1，并保留完整 Failed 报告。

5.1 的锁定来源在 `packaging/validation-blender-5.1.json`。从本地官方子模块的已有对象创建一次性干净源码，沿用当前集成代码和 wheel 锁：

```powershell
$blender51 = 'C:\Program Files\Blender Foundation\Blender 5.1\blender.exe'
$python51 = 'C:\Program Files\Blender Foundation\Blender 5.1\5.1\python\bin\python.exe'
& $python51 -B scripts/build_locked_candidate.py --blender $blender51 --lock packaging/validation-blender-5.1.json --output build/latest/dist/blender-5.1 --platform windows-x64 --offline
```

源码与子模块远端保持原样；临时克隆在构建结束后清理。离线构建要求固定提交与已核验 wheels 已在本地；缺失时直接失败。`--lock` 也可配合 `build_integration.py --upstream` 使用。发布仍使用正式发布流程及干净提交。

## 其他验证

| 项目 | 状态 |
| --- | --- |
| 标准库单元测试 | Passed：80 项 |
| 两个 Windows 候选官方格式校验 | Passed |
| 两版本所有 26 个工具的真实调用 | 已运行：各 25 常规用例 Passed、1 Failed；类成员参数另有 Failed |
| 两版本原始上游桥接对照 | Passed：完成对照；上游问题仍 Failed |
| 同一 SDK 会话连续 33 次响应 | Passed：两个版本及原始桥接对照 |
| 独立人工操作、跨系统、最低版本、发布验收 | Not Run |

`integration-tests.json` 的工具数量只证明工具发现。当前原生入口还会真实调用全部六个 CLI 工具并核对正向夹具；其他逐工具行为以 `mcp-tools-*-tests.json` 为准。每次原生安装失败独立保留。

## 官方分体复测

2026-10-10 使用干净固定提交构建原版 `mcp` Extension，在项目临时目录通过 uv 安装独立外部工具，使用真实 stdio SDK 启动服务。未安装集成 Extension，也未加载 `_vendor`；安装后的官方源码哈希与归档源码一致。

| 版本 | GUI 会话 | 缩略图尺寸失败 | 标准类成员查询失败 | 正常操作符 / 重复类名前缀对照 |
| --- | --- | --- | --- | --- |
| Blender 5.1.1 / v1.0.3 | 3 | 8/9 | 3/3 | 各 3/3 Passed |
| Blender 5.2.2 / dbbf836ad4b1 | 3 | 7/9 | 3/3 | 各 3/3 Passed |

所有 PNG 均检查实际尺寸和像素内容，每次调用后的场景设置均恢复。两项失败保留为 Failed；测试执行完整为 Passed。官方来源的 Extension 与 MCP 服务版本分别记录，5.2 固定提交中二者为 1.0.0 与 1.0.2。

入口：`scripts/test_upstream_split.py --blender <可执行文件> --upstream-ref <完整 SHA> --label <唯一标识>`。完整报告位于 `build/latest/upstream-split-*-tests.json`，运行环境已经清理；[5.1 脱敏证据](upstream-issues/evidence/blender-5.1-official.json)与[5.2 脱敏证据](upstream-issues/evidence/blender-5.2-official.json)可随两个英文 issue 草稿分享。上游 README 指向 `https://projects.blender.org/lab/blender_mcp/issues`；固定 Git 树未包含仓库模板，网页创建表单不可读，未声称已核对服务器模板。

本轮 5.1 候选的六个 CLI 工具、认证、生命周期和 GUI 自动化 Passed。5.2 本机集成检查在安装阶段遇到 WinError 5，保留 Failed；未实施暂缓问题的缓解。正式包与三平台发布状态以对应干净提交的最终验证记录为准。
