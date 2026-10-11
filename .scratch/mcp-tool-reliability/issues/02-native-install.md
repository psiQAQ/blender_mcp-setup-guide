Status: ready-for-human
Category: bug

# 原生安装目录重命名诊断

当前修复与部署流程见 `docs/native-install-fix.md`；2026-10-11 已经用户批准应用到两版系统安装器，并通过默认系统安装入口复测。本地副本验证和系统部署状态分别记录。

官方安装器将 `blender_mcp_integration@` 改为正式目录时的 `WinError 5`，已经用真实子句柄占用复现。修复限定为两个已核验版本的暂存目录重命名重试，保留持续拒绝与取消语义。`ready-for-human` 对应后续核对和提交上游宿主 issue；本地系统部署已经完成。

## Comments

2026-10-09：两次已授权 WPR 记录均已停止。第二次管理员只记录，普通权限安装 12 次中捕获 3 次原生 `0xC0000022`。两次失败记录到 Pylance 或 Codex 访问暂存子对象的重叠时刻；第三次占用者未确认，记录丢失 2553 个事件。错误位于未改动的 Blender 官方安装器，早于扩展导入。

确定性子文件 / 子目录句柄实验均复现 WinError 5，关闭自己拥有的句柄后恢复。5.1 与 5.2 的有时限诊断重试共 24 次最终安装成功，其中三次首次失败保留 Failed，并在 50 毫秒后恢复。VS Code 的 build 排除配置用于减少已观察扫描；官方安装器永久修复尚未实施，不能宣称根治。

详细来源、试验及限制见 `docs/native-install-diagnosis.md`，宿主 issue 草稿位于 `docs/upstream-issues/native-extension-rename.md`。仅保留最新完整失败 ETL 的字节校验归档及全部试验报告，清理清单在 `build/latest/maintenance/mcp-tool-diagnostics-retention.json`。下一步由用户核对并提交宿主 issue；本轮未修改系统 Blender、关闭用户进程或调整 ACL / 安全设置。

2026-10-11：继续修复。原版安装器在真实子句柄的短时占用及升级用例中返回失败；同一恢复断言在 5.1.1 / 5.2.2 工作副本通过。补丁仅在 Windows WinError 5 且源目录存在、目标不存在时累计等待最多 1.55 秒；路径变化、其他错误、持续占用和取消保留失败语义。每版 15 项回归、8 次完整包安装，以及隔离 Blender 安装/启用/禁用/重装均 Passed；99 项仓库单元测试 Passed。系统安装器原始字节备份与补丁保存在 build/latest/native-install-fix，实际部署仍为 Not Run，等待管理员应用批准。升级失败回滚不在该补丁范围。

2026-10-11：用户明确批准应用到 5.1 和 5.2。管理员进程仅写入两个已验证的系统安装器，写入后完整 SHA-256 与工作副本一致。每版实际系统文件的 15 项回归、1 次完整包安装、默认 Blender 安装入口的安装/启用/禁用/重装均 Passed，见 native-install-fix-5.1.1-system-tests.json 与 native-install-fix-5.2.2-system-tests.json。保留恢复脚本与原始字节备份；系统部署完成，不再等待审批。GUI 点击、黑图问题和特定内核驱动归因仍未完成。
