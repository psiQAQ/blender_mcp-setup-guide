# 验证证据与适用范围

产品支持 Windows x64、Linux x64、macOS Apple Silicon 和 CPython 3.13。5.1 稳定线固定官方 v1.0.3 / `2cea8d566dde07fbac28a61d698909d69724e853`；5.2 预发布线固定官方 main / `dbbf836ad4b1025f14a2b3b504c43903f39e0b04`。兼容范围分别为 5.1.0 ≤ Blender < 5.2.0 与 5.2.0 ≤ Blender < 5.3.0。

## 本地候选验证

2026-10-08 的本地候选为 `1.0.2-dev.2+integration.1`，使用 Windows Blender 5.2.2 LTS / 配套 Python 3.13.13。源码、候选 ZIP、SHA-256、原始报告与截图保存在 `build/latest/`，报告绑定实际包 hash。候选来源由包内 provenance.json 的 integration_commit 与 integration_dirty 字段确认；正式发布要求干净提交与全部发布检查通过。

| 检查 | 状态与范围 |
| --- | --- |
| 标准库单元测试 | Passed：覆盖渠道、来源、权限、失败报告、升级基线和不可变发布回执；数量见 unit-tests.json |
| Windows 最终 ZIP 官方校验 | Passed：`extension validate` |
| 实际 MCP、CLI、鉴权与生命周期 | Passed：发现 26 个工具及代表性行为；CLI 无 PATH/错误外部路径时仍使用当前宿主；异常 Timer 清理与恢复；在途 CLI 的 Stop/宿主退出清理。逐工具检查见下文 |
| 真实旧代码升级 | Passed：SHA-256 固定的已发布 dev.1 包经 HTTP 索引升级到 dev.2，偏好与 HTTP 凭据保留，旧服务结束 |
| 真实 GUI 事件循环 | Passed：自动启动、Timer、非法 deferred 结果后的正常请求、三种配置复制、诊断、重启、类/端口/Timer 清理 |
| 发布网站浏览器验证 | Passed：Edge，双语桌面/手机、通道和语言切换、无 JavaScript 下载入口；原始安装元数据 hash 保持一致 |
| Linux/macOS、本轮最低 Blender 版本 | Not Run：需要相应原生 runner 的候选报告 |
| 插件候选远端 CI、公开安装与回执上传 | Not Run：候选尚未发布 |
| Pages 网站部署 | Passed：网站提交 a348437，工作流 37791096376；安装包仍为既有公开版本 |
| 人工 GUI、三个实际 agent 验收 | Not Run：独立于自动化测试 |

截图用于视觉检查，不能代替人工操作。网页预览展示原先已发布的下载数据；它不宣称本地 dev.2 候选已经发布。

2026-10-09 的[双版本逐工具检查](mcp-tool-checks.md)分别真实调用全部 26 个工具，常规用例均为 25 Passed / 1 Failed，另有 API 类成员参数失败。原始上游桥接对照复现了两个工具缺陷。5.1 发布包的六个 CLI 工具失败，当前集成代码构建的 `1.0.3+integration.2` 本地候选已通过这六项；候选没有发布。工具发现数量不能替代逐工具行为验收。

[原生安装目录诊断](native-install-diagnosis.md)在两版本复现 WinError 5，并保留首次失败及诊断恢复。既有一次升级或 GUI 检查通过不能消除这个间歇安装失败；官方安装器的永久修复和新的正式发布验收仍未完成。

## 当前测试入口

常规 HTTP MCP 客户端显式设置读取期限 60 秒、SDK 等待期限 90 秒，见 `scripts/mcp_checks.py`。生命周期中断用例的 SDK 15 秒用于验证取消与进程清理；定向诊断的 `--http-read-timeout` 可以故意复现短读取期限，不是常规默认值。

原生集成检查通过已保存场景、一个真实链接库和一个有 fake user 的缺失图片，调用全部六个 CLI 工具。在 PATH 为空且传入错误 BLENDER_PATH 的条件下，核对工具实际使用宿主 Blender。安装器报告 ERROR 时直接失败，不导入未安装的 Extension。重试会保留原 Failed 报告和必要日志；候选替换只使对应输出目录旧包的证据失效。

部署后使用 `scripts/test_index_sync.py --blender <可执行文件> --index-url <统一索引> --output <报告>` 验证实际官方同步与选包。增加 `--previous-package <真实旧发布 ZIP> --expected-version <新版本>` 时，入口先核对发布基线的大小和 SHA-256，在隔离仓库安装旧包，再切换到公开统一索引，并要求 Blender 官方更新统计恰好发现一个更新。此检查不会启用旧插件或修改系统配置。

官方分体复测使用 `scripts/test_upstream_split.py`，安装原版 `mcp` Extension 并使用独立 uv 环境的 stdio 服务。每版本三个 GUI 会话、九次缩略图调用与三组文档查询，报告不计入集成发布门槛的 Passed 项。完整脱敏证据和两个待用户发布的英文 issue 位于 `docs/upstream-issues/`。官方复测确认的失败继续保留为 Failed，网站与新 Release 注明其限制。

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
