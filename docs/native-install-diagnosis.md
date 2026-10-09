# Windows 原生扩展目录重命名诊断

2026-10-09，Windows x64，Blender 5.1.1 / Python 3.13.9 与 Blender 5.2.2 LTS / Python 3.13.13。

`WinError 5` 发生在 **Blender 官方扩展安装器将解压暂存目录改为正式目录** 的阶段，早于集成扩展导入和 MCP 服务启动。5.1 与 5.2 均有实际失败记录。最新一次 WPR 跟踪没有丢失事件，12 次普通权限安装中 3 次失败，失败期间均捕获到 Codex 桌面进程打开暂存子目录。证据支持短时外部访问竞争；此前第二次跟踪的第 12 次失败仍不能回填具体占用者，永久修复和具体内核拒绝来源也未确认。

## 错误位置与来源

5.2 的 `5.2/scripts/addons_core/bl_pkg/cli/blender_ext.py:4147` 调用：

```python
os.rename(filepath_local_pkg_temp, filepath_local_pkg)
```

源目录为 `blender_mcp_integration@`，目标为 `blender_mcp_integration`。暂存解压成功后才执行这一步；目标在本轮失败时不存在。异常被官方安装器记为 `Failed to rename directory`，随后清理暂存目录。进程退出码可能仍为 0，因此本仓库的检查同时核对正式目录的 manifest、原始错误及扩展是否实际可用。

使用系统安装的未改动安装器，在独立的 `python.exe -I -S -B` 进程中也能复现。没有 MCP 客户端、扩展导入或服务启动，足以把该失败与 MCP 请求处理区分开。测试只在一次性进程中观察 `os.rename`；没有修改 Program Files 内的源码。

| 官方安装器 | SHA-256 |
| --- | --- |
| Blender 5.1.1 | `3738e7660bdaa7493d756be3132274eef6eb748305a16cf957f5e324573e93da` |
| Blender 5.2.2 | `246cb49882f6129340767023bdc28e98c8ea6e743f64ebbff8aec774f842e5e1` |

候选包版本、来源和哈希见[工具检查](mcp-tool-checks.md)。5.1 的已发布包与当前候选都出现过原生安装失败，不能把差异归因于某一版 Python 或某个集成包版本。

## 第二次跟踪摘要

第二次跟踪中，管理员仅运行记录器；12 个安装进程均报告 `administrator: false`。第 1、5、12 次失败，其余 9 次成功。`FileIo Rename` 与随后同一请求的 `OperationEnd` 按时间关联，避免把重复使用的 IRP 地址串成一个请求。

| 用例 | 安装 PID | 原生重命名结果 | 与重命名重叠的外部访问 |
| --- | --- | --- | --- |
| 1 | 28056 | `0xC0000022`，341.3 微秒 | PID 135884 的 Pylance 打开 `bpy.types.NodeSocketVectorDirection.rst`；打开事件在重命名前 3.6 微秒，Cleanup 在开始后 8.8034 毫秒 |
| 5 | 72656 | `0xC0000022`，206.5 微秒 | PID 150648 的 Codex 打开 `_vendor` 目录；打开事件在重命名前 22.8 微秒，Cleanup 在开始后 64.3 微秒 |
| 12 | 14780 | `0xC0000022`，112.3 微秒 | 没有记录到当时仍未 Cleanup 的外部子对象；占用者未确认 |

ETW 中的进程记录及现场进程路径对应 VS Code 的 Pylance `server.bundle.js` 和 Codex 桌面 `ChatGPT.exe`。这些进程在记录前已存在，避免只凭当前 PID 误认进程。部分成功用例附近也有这些进程的活动，因此“曾访问目录”本身不足以证明导致某一次失败。

失败请求中记录到的过滤器回调地址属于 `fileinfo.sys`。回调事件没有指出它返回拒绝；不能根据回调出现就归责该驱动，也没有证据把这三次失败归责 Defender。第一轮成功安装中的 Defender 扫描事件只能说明扫描发生过。

跟踪停止时报告 **2553 个丢失事件**。目录内已有 Cleanup、尚未记录 Close 的 FileObject 不被当作仍有用户句柄；打开失败的对象也被排除。没有捕获到某个句柄不能证明它不存在。这是第三次失败以及具体内核拒绝来源的验证限制。

原始与关联证据位于：

- `build/latest/native-rename-trace-5.2-external-tests.json`
- `build/latest/evidence/native-trace-5.2-external/findings.json`
- `build/latest/evidence/native-trace-5.2-external/rename-context.json`
- 同目录的 `trace-control.json`、`recording-profile.wprp` 与 `retention.json`
- 本次完整 ETL 已由第三次无事件丢失的记录取代；保留原始与归档 SHA-256、统计和关联摘要

## 第三次跟踪：没有事件丢失的失败现场

用户单独批准一次 `-ExternalWorker -Focused` 记录。管理员只负责 WPR，12 个实际安装进程全部为 `administrator: false`；不使用诊断重试。安装结果是 9 Passed / 3 Failed，失败为第 3、5、8 次。WPR 已停止，记录器已退出。`xperf tracestats` 报告 0 lost events / 0 lost buffers。

这次减少了无关 provider 与堆栈，保留 FileIO 生命周期、过滤器初始化/失败、进程与模块信息及 Rename 堆栈。完整 ETL 原始体积 1,380,245,877 字节，gzip 归档为 965,364,407 字节；解压后全部字节 SHA-256 校验通过，详见最新 `retention.json`。

PID 150648 的进程元数据对应 Codex 桌面的 `ChatGPT.exe`。以下时刻以该次 `FileIo Rename` 开始为 0；打开结果均成功，共享掩码均为 7。

| 实际失败用例 / 安装 PID | Codex 打开的子目录 | 打开时刻 | Cleanup 时刻 | 关联的 FileIo OpEnd |
| --- | --- | --- | --- | --- |
| 3 / 68892 | `_vendor` | +57.1 微秒 | +111.0 微秒 | +90.5 微秒，`0xC0000022` |
| 5 / 155020 | `_vendor` | +109.5 微秒 | +180.6 微秒 | +134.9 微秒，`0xC0000022` |
| 8 / 53448 | `_vendor/runtime` | +83.3 微秒 | +948.5 微秒 | +936.7 微秒，`0xC0000022` |

第 3 次在 Rename 开始时没有外部未 Cleanup 的子对象；Codex 在操作开始后才打开 `_vendor`，并在该局部拒绝事件之后 Cleanup。只检查开始时刻的句柄会漏掉这类竞争。关联器现在同时保留开始时已有的对象与操作期间新增的打开记录，也按事件时间解析进程身份，避免 PID 后续复用导致误认。

这里仍有重要边界：第 4、7 次安装的 Python `os.rename` 和实际 manifest 均成功，但各有一个关联 FileIo OpEnd 记录 `0xC0000022`。第 4 次已用 xperf 独立解码核对同一事件及堆栈，排除了本地 TDH 字段解析错误。该日志点位于 `fileinfo.sys` 的 postoperation 路径；Microsoft 的[完成处理说明](https://learn.microsoft.com/en-us/windows-hardware/drivers/ifs/performing-completion-processing-for-an-i-o-operation)说明，这类回调处在过滤器栈的完成处理链中。记录没有提供所有上层处理的最终返回状态，不能把单个日志点的状态等同于最终 Win32 调用结果，也不能据此判定是哪一个驱动改变了结果。

因此 **实际失败次数以 Python 异常和安装目录为准，始终是 3 次**；`caller_status` 与 `event_status` 分开保留。成功用例也有 Codex 访问，证据支持“时机相关的短时竞争”，不能简化为“发现 Codex 就必定失败”或“fileinfo/Defender 返回了最终拒绝”。旧跟踪第 12 次没有在操作区间内捕获到同样的打开，不能用新用例代替其缺失现场。

最新证据目录为 `build/latest/evidence/native-trace-5.2-external-focused/`，保留：

- `native-install.etl.gz`、`retention.json`、`trace-control.json`、实际 WPR profile 与 `trace-statistics.txt`。
- `findings.json`、`rename-context.json`，含开始时与操作期间打开的对象及其后续 Cleanup。
- `worker-windows.json`、`case-4-events.csv`，用于核对局部事件状态与调用结果不一致的边界。
- `build/latest/native-rename-trace-5.2-external-focused-tests.json`，绑定未改动安装器及实际 ZIP 哈希。

## 最小句柄实验

`scripts/check_windows_rename.py` 在自己拥有的临时目录中，分别打开一个子文件或子目录，测试共享掩码 3 与 7。四种情况下，父目录的 DELETE 权限检查均通过，但父目录重命名均返回 WinError 5；等待 250 毫秒仍失败，关闭该子句柄后立即成功。

这说明父目录 DELETE 权限足够并不能排除子对象占用，`FILE_SHARE_DELETE` 也不能保证父目录重命名成功。Windows 的 [FileRenameInformation 规范](https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-fsa/87f86c9b-6c2a-4803-84b7-131a74a434fa)规定了目录包含打开文件时返回 `STATUS_ACCESS_DENIED` 的条件。该实验与跟踪支持“外部扫描与原生目录重命名发生竞争”的判断；无法据此补齐丢失的第三次事件。

另用真实子进程测试了“用户文件句柄已经关闭，仅保留映射视图”的情况，包含只读与 copy-on-write，各 3 次。六次父目录重命名都成功，见 `windows-rename-sections-tests.json`。此结果排除了本实验中的单纯数据映射假设，不能扩展为排除所有内核或过滤器状态。

## 对照与缓解结果

每个尝试的报告和日志都保留。以下计数区分首次失败与诊断恢复：

| 对照 | 首次结果 | 最终安装 / 解释 |
| --- | --- | --- |
| 5.1 早期普通安装，3 次 | 2 Failed / 1 Passed | 5.1 也受影响；`native-install-5.1-tests.json` |
| 5.1 当前候选普通安装，8 次 | 8 Passed | 此批未复现，不代表根治 |
| 5.2 普通安装，8 次 | 2 Failed / 6 Passed | `native-rename-5.2-timing-baseline-tests.json` |
| 5.2 首次重命名前等待 250 毫秒，8 次 | 8 Passed | 单变量缓解实验，不是正式修复 |
| 第一轮管理员记录及安装，5 次 | 5 Passed | 改变了安装令牌，没有捕获原失败 |
| 第二轮管理员记录、普通权限安装，12 次 | 3 Failed / 9 Passed | 三次原生拒绝已捕获 |
| 第三轮 focused 记录、普通权限安装，12 次 | 3 Failed / 9 Passed | 无事件丢失；三次失败期间均有 Codex 子目录打开 |
| 5.2 临时目录加入 `node_modules` 层，12 次 | 3 Failed / 9 Passed | 目录名不能可靠隔离所有扫描；未用于正式入口 |
| 5.2 有时限的诊断重试，12 次 | 2 Failed / 10 Passed | 两次首次失败均在 50 毫秒后的首次重试恢复；最终 12 次安装成功 |
| 5.1 同一诊断重试，12 次 | 1 Failed / 11 Passed | 首次失败在 50 毫秒后的首次重试恢复；最终 12 次安装成功 |

此前 `native-rename-5.2-recovery-tests.json` 的 12 次最终成功包含四次首次失败；其重试发生在句柄诊断完成之后，已经等待约 1.8–3.85 秒，不能解释为“立即重试”。当前入口会保留首次 Failed 状态，即使诊断恢复成功也返回失败退出码。

仓库新增 `.vscode/settings.json`，为 Pylance 和 VS Code 文件监视排除 `build`。这是减少已观察扫描的本地配置，不覆盖其他程序；配置写入后的无重试纯净对照尚未单独完成，不能把它记为已验证的根治。

诊断重试仅限 WinError 5、源目录仍存在且目标不存在，等待序列为 50、100、200、400、800 毫秒，总计 1.55 秒；其他错误立即保留。它证明短时竞争具有可恢复性，可作为官方安装器修复的候选方向。**本轮没有将该重试注入正式产品或系统 Blender**；正式安装的 WinError 5 仍属于 Failed，具体驱动归因和永久修复属于 Not Run。没有关闭用户进程、强制关闭外部句柄、修改 ACL 或安全设置。

## 可运行的复现与缓解入口

在仓库根目录的 PowerShell 中运行，使用普通权限。首次失败时会返回退出码 1，日志仍保留。

```powershell
$python = 'C:\Users\ustcw\miniforge3\python.exe'
$hostPython = 'C:\Program Files\Blender Foundation\Blender 5.2\5.2\python\bin\python.exe'
$installer = 'C:\Program Files\Blender Foundation\Blender 5.2\5.2\scripts\addons_core\bl_pkg\cli\blender_ext.py'
$package = 'build/latest/dist/blender_mcp_integration-1.0.2-dev.2+integration.1-windows-x64.zip'

# 默认调用未改动的官方安装器，记录首次重命名。
& $python -B scripts/diagnose_native_install.py --python $hostPython --installer $installer --package $package --version 5.2.2 --runs 8 --label local-5.2

# 独立测试短时恢复；报告仍保留首次失败。
& $python -B scripts/diagnose_native_install.py --python $hostPython --installer $installer --package $package --version 5.2.2 --runs 8 --bounded-retry --label local-5.2-retry

# 确定性子句柄占用实验，不需要管理员权限。
& $python -B scripts/check_windows_rename.py
```

5.1 改用其 `python.exe`、`blender_ext.py`、5.1 候选包与 `--version 5.1.1`。全部安装和实验环境在 `build/.working/` 中创建，结束后清理；报告导出的路径用于定位证据，不表示安装环境仍保留。

新的 WPR 记录需要管理员权限及单独授权；三次已授权记录均已停止。`trace_native_install.ps1 -ExternalWorker -Focused` 让管理员仅记录，安装应从普通权限会话运行。已完成记录不重复触发 UAC。

官方安装器注释引用 [Blender #130211](https://projects.blender.org/blender/blender/issues/130211)，本轮网页访问返回 403，未核实该 issue 的内容。新增[宿主问题草稿](upstream-issues/native-extension-rename.md)，供后续在 Blender 宿主仓库核对已有问题后提交；它与 MCP 上游的两个工具缺陷分开记录。
