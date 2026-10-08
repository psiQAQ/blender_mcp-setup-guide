# 验证证据与适用范围

产品支持 Windows x64、Linux x64、macOS Apple Silicon；Blender 5.1.0 ≤ 版本 < 5.2.0，CPython 3.13。官方 MCP 来源为 v1.0.3 / `2cea8d566dde07fbac28a61d698909d69724e853`。

| 检查 | 证据与状态判定 |
| --- | --- |
| 本地标准库单元测试 | 26 项 Passed，覆盖平台锁、ABI、配置、清理防护、完整平台集合、证据归档、版本不可变、draft 恢复与鉴权重定向 |
| 原生最终 ZIP、MCP、鉴权和生命周期 | CI 的平台 integration-tests.json；必须为 Passed 并匹配 ZIP hash |
| GUI 事件循环、Timer、配置复制、重启及清理 | 平台 gui-tests.json，GUI 测试为必需项 |
| Blender 5.1.0 兼容 | 平台 minimum-tests.json，使用相同最终 ZIP |
| 单平台和三平台 HTTP 索引安装与升级 | upgrade-tests.json、repository-tests.json，验证偏好/凭据及平台选择 |
| 远端资产回读和正式发布 | Release 工作流日志及逐资产 hash 检查 |
| 公开索引原生安装和真实 MCP | Release 工作流 publication-<platform> 产物中的 published-tests.json |
| 人工 GUI 与三个实际 agent 验收 | Not Run；自动化测试不能替代此项 |

托管 CI 的实际结果见 [Actions](https://github.com/psiQAQ/blender_mcp-setup-guide/actions)。正式版本的来源与绑定 ZIP 的报告保存在 [Release](https://github.com/psiQAQ/blender_mcp-setup-guide/releases) 的 `blender_mcp_integration-<version>-evidence.zip` 中；只有对应平台、候选 ZIP 和提交的 Passed 报告构成该候选的验证证据。未运行、失败或其他候选的报告不能计为通过。

所有测试使用隔离配置；升级的前一修订包为同一实现生成的测试夹具，覆盖真实 Blender 索引同步、替换及状态迁移。首版没有历史正式安装包。GUI 截图属于自动测试产物，可用于视觉检查；它不构成人工操作验收。
