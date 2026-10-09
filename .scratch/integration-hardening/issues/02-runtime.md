Status: ready-for-agent
Category: bug
Implementation: complete

# 运行时恢复与资源清理

deferred 序列化失败返回工具错误，Timer 保留诊断并清理；CLI 固定当前宿主；凭据用户专属权限；sidecar 与后台任务归入受控进程组/Job Object。

验收：Windows 候选 ZIP 的真实 MCP/CLI、在途 Stop/宿主退出、异常清理、旧代码升级与 GUI Timer Passed。Linux/macOS 实际运行 Not Run。
