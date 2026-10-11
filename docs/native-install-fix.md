# Windows 安装目录重命名修复

修复对象是 Blender 官方扩展安装器 `bl_pkg/cli/blender_ext.py`。Windows 上，暂存目录内的文件或子目录仍被打开时，将暂存目录改成正式名称可能返回 `WinError 5`。错误发生在扩展导入之前；安装失败后，该扩展不可用。历史现场与确定性实验见[原生安装诊断](native-install-diagnosis.md)。

本地修复针对 Blender 5.1.1 与 5.2.2 的已核验安装器，只改变安装包的暂存目录提交步骤。2026-10-11 经用户批准，补丁已应用到两个系统安装器，并通过默认系统安装入口复测。工作副本、原始字节备份、差异和哈希清单位于 `build/latest/native-install-fix/blender-<完整版本>/`。系统部署状态单独记录于该目录的 `deployment.json`。

## 重试边界

- 仅在 Windows 且实际错误为 `WinError 5` 时重试。
- 源必须仍为目录，目标必须不存在；等待前后均检查，包含失效符号链接的目标占用。
- 等待为 50、100、200、400、800 毫秒，累计 1.55 秒，最多执行六次原生重命名。文件系统调用本身耗时另计。
- 重试输出 `STATUS`，持续拒绝或其他错误保留原安装器的 `ERROR` 和失败返回。取消在重试通知及等待结束时检查。
- 升级沿用原安装器先移除或迁移旧目录的流程。持续失败或取消仍可能留下未安装状态；这份补丁不增加升级回滚能力。

这是一份有界恢复修复，不能解决持续权限拒绝或长时间占用。原安装器的批量入口可能在单包失败时仍退出 0，验证必须检查 `ERROR`、manifest 和扩展实际启用状态。

## 验证

2026-10-11 的验证结果：

| 检查 | 状态 | 结果 |
| --- | --- | --- |
| 原版 5.2.2 的恢复回归 | Failed，符合预期 | 文件、子目录及升级的短时占用均返回安装失败；同一断言用于修复副本 |
| 5.1.1 / 5.2.2 修复副本 | Passed | 每版 15 项，共 30 项；短时占用均在首次 50 毫秒重试恢复 |
| 持续占用 | Passed | 每版三种持续占用均尝试六次后保留失败，实测约 1.56–1.58 秒 |
| 完整包重复安装 | Passed | 每版 8 次，共 16 次；这一批没有自然触发重试 |
| 隔离 Blender 原生安装与启用 | Passed | 两版均完成安装、启用、禁用、重装和再次启用 |
| 仓库单元测试 | Passed | 99 项，包含 5 项部署与恢复门禁测试 |
| 系统部署 | Passed | 两个系统文件与验证副本的 SHA-256 一致，ACL 和所有权未修改 |
| 部署后系统入口复测 | Passed | 每版再跑 15 项回归、1 次完整包安装，以及默认 Blender 安装入口的安装/启用/禁用/重装 |
| GUI 点击 / MCP 服务验收 | Not Run | 本次验证范围是原生安装和后台 Blender 启用 |

`scripts/test_native_install_fix.py` 使用受控的真实 Windows 子句柄，运行官方安装函数和真实 ZIP 解压、重命名路径。短时占用、持续占用及升级使用真实句柄；路径变化等分支用明确标记的边界注入验证；取消等待测试调用原安装器的信号处理函数，不向其他进程发送信号。

随后用完整集成包重复安装，并在新建的隔离 Blender 中执行原生安装、启用、禁用、重新安装和再次启用。部署前的验证将安装器子进程指向工作副本；部署后的 `*-system` 报告使用 Blender 默认系统安装入口，没有重定向。两阶段均使用后台 Blender，不代表已完成 GUI 点击或 MCP 服务验收。

当前报告：

- `build/latest/native-install-fix-5.2-original-red-tests.json`：原版安装器的失败回归。
- `build/latest/native-install-fix-5.2.2-tests.json`：5.2.2 修复副本验证。
- `build/latest/native-install-fix-5.1.1-tests.json`：5.1.1 修复副本验证。
- `build/latest/native-install-fix-5.1.1-system-tests.json` 与 `build/latest/native-install-fix-5.2.2-system-tests.json`：部署后的系统安装器回归及默认宿主入口验证。
- `build/latest/unit-tests.json`：包含部署、恢复和哈希门禁的仓库测试。

原生安装验证报告绑定实际安装器与 ZIP 的 SHA-256。首次原生拒绝和最终恢复结果分别保留。运行环境放在 `build/.working/`，日志和报告导出后清理。

## 准备与复测

在仓库根目录的普通 PowerShell 中运行。无需下载或安装依赖。以下为 5.2.2 示例；5.1.1 使用对应宿主路径、完整版本及已验证的 5.1 ZIP。

```powershell
$python = 'C:\Users\ustcw\miniforge3\python.exe'
$blender = 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe'
$installer = 'C:\Program Files\Blender Foundation\Blender 5.2\5.2\scripts\addons_core\bl_pkg\cli\blender_ext.py'
$package = 'build/latest/validated/blender-5.2/windows-x64/dist/blender_mcp_integration-1.0.2-dev.2+integration.1-windows-x64.zip'

& $python -B scripts/prepare_native_install_fix.py --installer $installer --version 5.2.2

& $python -B scripts/test_native_install_fix.py `
    --blender $blender `
    --installer build/latest/native-install-fix/blender-5.2.2/blender_ext.py `
    --package $package --version 5.2.2 --label 5.2.2
```

准备脚本要求已知原始 SHA-256 与唯一匹配的源码片段；宿主版本发生变化时直接拒绝，不能将旧补丁套用到未知版本。系统已经打补丁时复用现有工作副本和备份，不重新准备。

## 部署与恢复

部署需要修改 `C:\Program Files\Blender Foundation\Blender 5.1\5.1\scripts\addons_core\bl_pkg\cli\blender_ext.py` 或对应的 `Blender 5.2\5.2` 文件，需要管理员权限和明确批准。它会影响所选 Blender 版本后续的扩展安装。执行时应没有正在进行的扩展安装。

先在普通 PowerShell 检查原始/修复文件和系统目标的哈希：

```powershell
& $python -B scripts/apply_native_install_fix.py --version 5.2.2 --action check
```

批准后，在管理员 PowerShell 中进入仓库根目录，显式指定同一个 Python：

```powershell
& 'C:\Users\ustcw\miniforge3\python.exe' -B scripts/apply_native_install_fix.py --version 5.2.2 --action apply
```

只有该补丁的精确字节已有 `Passed` 报告，且系统文件仍是已知原版或同一补丁，部署才继续。原文件的 ACL 和所有权保持不变；写入后再次核对完整 SHA-256。还原命令：

```powershell
& 'C:\Users\ustcw\miniforge3\python.exe' -B scripts/apply_native_install_fix.py --version 5.2.2 --action restore
```

恢复使用已校验的原始字节。若 Blender 更新或文件被其他工具修改，部署与恢复均拒绝覆盖未知内容。Blender 更新可能替换此文件，需要针对新版本重新验证。
