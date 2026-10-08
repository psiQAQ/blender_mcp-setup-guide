# 验证证据与适用范围

产品支持 Windows x64、Linux x64、macOS Apple Silicon 和 CPython 3.13。5.1 稳定线固定官方 v1.0.3 / `2cea8d566dde07fbac28a61d698909d69724e853`；5.2 预发布线固定官方 main / `dbbf836ad4b1025f14a2b3b504c43903f39e0b04`。兼容范围分别为 5.1.0 ≤ Blender < 5.2.0 与 5.2.0 ≤ Blender < 5.3.0。

## 本地候选验证

2026-10-08 的本地候选为 `1.0.2-dev.2+integration.1`，使用 Windows Blender 5.2.2 LTS / 配套 Python 3.13.13。源码、候选 ZIP、SHA-256、原始报告与截图保存在 `build/latest/`，报告绑定实际包 hash。候选来源由包内 provenance.json 的 integration_commit 与 integration_dirty 字段确认；正式发布要求干净提交与全部发布检查通过。

| 检查 | 状态与范围 |
| --- | --- |
| 标准库单元测试 | Passed：覆盖渠道、来源、权限、失败报告、升级基线和不可变发布回执；数量见 unit-tests.json |
| Windows 最终 ZIP 官方校验 | Passed：`extension validate` |
| 实际 MCP、CLI、鉴权与生命周期 | Passed：26 个工具；CLI 无 PATH/错误外部路径时仍使用当前宿主；异常 Timer 清理与恢复；在途 CLI 的 Stop/宿主退出清理 |
| 真实旧代码升级 | Passed：SHA-256 固定的已发布 dev.1 包经 HTTP 索引升级到 dev.2，偏好与 HTTP 凭据保留，旧服务结束 |
| 真实 GUI 事件循环 | Passed：自动启动、Timer、非法 deferred 结果后的正常请求、三种配置复制、诊断、重启、类/端口/Timer 清理 |
| 发布网站浏览器验证 | Passed：Edge，双语桌面/手机、通道和语言切换、无 JavaScript 下载入口；原始安装元数据 hash 保持一致 |
| Linux/macOS、本轮最低 Blender 版本 | Not Run：需要相应原生 runner 的候选报告 |
| 插件候选远端 CI、公开安装与回执上传 | Not Run：候选尚未发布 |
| Pages 网站部署 | Passed：网站提交 a348437，工作流 37791096376；安装包仍为既有公开版本 |
| 人工 GUI、三个实际 agent 验收 | Not Run：独立于自动化测试 |

截图用于视觉检查，不能代替人工操作。网页预览展示原先已发布的下载数据；它不宣称本地 dev.2 候选已经发布。

## 发布验收

正式发布要求同一干净提交、同一平台最终 ZIP 和以下报告全部通过。其他候选的报告、失败报告和未运行项目不能计为通过。

| 检查 | 报告与要求 |
| --- | --- |
| 单元测试、模板 | unit-tests.json、template-tests.json |
| 原生 MCP、CLI、鉴权和生命周期 | integration-tests.json |
| GUI Timer、配置与清理 | gui-tests.json，必需项 |
| 最低兼容版本 | minimum-tests.json，5.2.0 或 5.1.0，使用同一最终 ZIP |
| 旧发布包升级 | upgrade-tests.json，基线 URL、版本、大小/hash 与当前通道一致 |
| 三平台集合索引安装与机制升级 | repository-tests.json，使用明确的测试夹具，与真实旧代码升级区分 |
| 公开索引原生安装和 MCP | published-tests.json；成功/失败写入同一报告路径 |

发布前来源和七类原始报告保存在 Release 的 `blender_mcp_integration-<version>-evidence.zip`。三平台公开安装全部通过后，独立的 `blender_mcp_integration-<version>-publication-<run-id>.zip` 长期保存不可变元数据与三份公开安装报告，绑定版本、通道、集成提交、发布 run ID、包 hash 和报告 hash。既有 evidence 不被改写。

实际托管运行见 [Actions](https://github.com/psiQAQ/blender_mcp-setup-guide/actions)，已发布资产见 [Release](https://github.com/psiQAQ/blender_mcp-setup-guide/releases)。本地候选验证不授权远端发布，也不能替代三平台 CI。
