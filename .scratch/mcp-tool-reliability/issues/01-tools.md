Status: ready-for-human
Category: bug

# 全部 MCP 工具检查与责任定位

使用真实、隔离的 Blender GUI 与 HTTP MCP 服务检查两个发布线。保留每次失败，复测截图、渲染、API 文档和长会话响应。集成问题在本仓库修复，上游问题整理复现报告。

## Comments

2026-10-09：完成两版本全部 26 个工具的真实 GUI / HTTP SDK 检查，常规用例各 25 Passed / 1 Failed，并完成两个版本的原始上游桥接对照及连续 33 次调用。5.1 发布包的六个 CLI 失败由当前集成代码构建的本地候选修复，复测 Passed；候选未发布。

缩略图异步渲染尺寸和 API 类成员查询已确认来自锁定 MCP 上游。两份最小复现草稿位于 `docs/upstream-issues/`，供用户后续提交。其他历史截图、SDK 超时与测试夹具失败均记录分类和验证限制，见 `docs/mcp-tool-checks.md`；完整失败汇总在 `build/latest/mcp-tool-failures.json`。标准库测试 73 项 Passed。外部 issue、发布及独立人工验收未执行。
