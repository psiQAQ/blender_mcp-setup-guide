Status: ready-for-human
Category: bug

# 原生安装目录重命名诊断

复现官方安装器 `blender_mcp_integration@` 到正式目录的 `WinError 5`。优先检验句柄占用、目录权限、目标冲突和驱动环境，改变一个变量并保留证据。修复范围限于本仓库负责的集成或测试入口。

## Comments

2026-10-09：两次已授权 WPR 记录均已停止。第二次管理员只记录，普通权限安装 12 次中捕获 3 次原生 `0xC0000022`。两次失败记录到 Pylance 或 Codex 访问暂存子对象的重叠时刻；第三次占用者未确认，记录丢失 2553 个事件。错误位于未改动的 Blender 官方安装器，早于扩展导入。

确定性子文件 / 子目录句柄实验均复现 WinError 5，关闭自己拥有的句柄后恢复。5.1 与 5.2 的有时限诊断重试共 24 次最终安装成功，其中三次首次失败保留 Failed，并在 50 毫秒后恢复。VS Code 的 build 排除配置用于减少已观察扫描；官方安装器永久修复尚未实施，不能宣称根治。

详细来源、试验及限制见 `docs/native-install-diagnosis.md`，宿主 issue 草稿位于 `docs/upstream-issues/native-extension-rename.md`。仅保留最新完整失败 ETL 的字节校验归档及全部试验报告，清理清单在 `build/latest/maintenance/mcp-tool-diagnostics-retention.json`。下一步由用户核对并提交宿主 issue；本轮未修改系统 Blender、关闭用户进程或调整 ACL / 安全设置。
