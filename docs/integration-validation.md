# 验证证据与适用范围

产品支持 Windows x64、Linux x64、macOS Apple Silicon 和 CPython 3.13。5.1 稳定线固定官方 v1.0.3 / `2cea8d566dde07fbac28a61d698909d69724e853`；5.2 预发布线固定官方 main / `dbbf836ad4b1025f14a2b3b504c43903f39e0b04`。兼容范围分别为 5.1.0 ≤ Blender < 5.2.0 与 5.2.0 ≤ Blender < 5.3.0。

## 本轮 CI 与发布验证

2026-10-10，两条线均由干净发布提交的三平台 CI 重建，七类必需报告全部 Passed。包内 provenance.json 记录实际集成提交与 `integration_dirty: false`，各报告绑定相应 ZIP 的 SHA-256。本地完整成果位于 `build/latest/validated/blender-5.1/` 和 `build/latest/validated/blender-5.2/`。

| 发布线 | 版本与构建提交 | 成功 CI |
| --- | --- | --- |
| 5.1 stable | `1.0.3+integration.2` / `bb3319d6ad8bb58be3fcc10009c8578be5f82209` | [37960368325](https://github.com/psiQAQ/blender_mcp-setup-guide/actions/runs/37960368325) |
| 5.2 preview | `1.0.2-dev.2+integration.1` / `d71ee1ea43b6720212f161fad4c9ac468fd66e92` | [37960367844](https://github.com/psiQAQ/blender_mcp-setup-guide/actions/runs/37960367844) |

| 检查 | 状态与范围 |
| --- | --- |
| 标准库单元测试 | Passed：81 项，三个原生平台分别运行并绑定实际包 |
| 六个最终 ZIP 官方校验、模板 | Passed：三平台 `extension validate` 与两个模板的验证 |
| 实际 MCP、六个 CLI、鉴权与生命周期 | Passed：真实保存场景、缺失文件、链接库；错误外部路径与空 PATH 下使用实际宿主；在途调用 Stop/宿主退出、异常恢复与清理 |
| 真实旧代码升级 | Passed：六个已发布旧平台包均通过真实 HTTPS 大小/hash 校验，再经 HTTP 索引升级，偏好与凭据保留，旧服务结束 |
| 真实 GUI 事件循环 | Passed：三平台自动启动、Timer、非法 deferred 结果后的正常请求、配置复制、诊断、重启与清理 |
| 最低兼容 Blender | Passed：同一最终 ZIP 在 5.1.0 或 5.2.0 上安装并执行 MCP/生命周期；常规 CI 版本分别为 5.1.2 / 5.2.2 |
| 集合索引选包、安装与机制升级 | Passed：两条线各三个原生平台；机制夹具与上述真实旧代码升级分别记录 |
| 公开安装与不可变回执 | Passed：两条线各三平台；发布流程 [37961815677](https://github.com/psiQAQ/blender_mcp-setup-guide/actions/runs/37961815677) / [37969368609](https://github.com/psiQAQ/blender_mcp-setup-guide/actions/runs/37969368609)，各自 Release 保留不可变回执 |
| Pages、三个公开索引、六个下载回读 | Passed：恢复部署及自动刷新完成；六份索引/发布记录与制品字节一致，六个公开 ZIP 的大小/hash 与正式 CI 成果一致 |
| 本机官方统一索引选包 | Passed：Blender 5.1.1 / 5.2.2 实际同步六条统一索引，各选择正确的新版 Windows 包 |
| 本机从真实旧版发现更新 | 5.1 Passed：官方统计恰好一个更新；5.2 的旧基线安装 Failed（WinError 5），更新发现 Not Run，不重复安装或实施缓解 |
| 双语桌面/手机浏览器检查 | Passed：1270px / 390px，版本切换、下载/hash、索引复制、固定导航、无页面横向溢出，以及禁用 JavaScript 后的六个下载入口 |
| 人工 GUI、三个实际 agent 验收 | Not Run：独立于自动化测试 |

截图用于视觉检查，不能代替人工操作。

2026-10-09 的[双版本逐工具检查](mcp-tool-checks.md)分别真实调用全部 26 个工具，常规用例均为 25 Passed / 1 Failed，另有 API 类成员参数失败。2026-10-10 的干净官方分体安装确认：5.1 缩略图尺寸 8/9 Failed，5.2 为 7/9 Failed；标准类成员查询各 3/3 Failed，正常操作符和重复类名前缀对照全部 Passed。两项上游问题作为已知限制保留，见两个[英文 issue 文档](upstream-issues/)。工具发现数量不能替代逐工具行为验收。

[原生安装目录诊断](native-install-diagnosis.md)曾在两版本复现 WinError 5；本轮 5.2 本机候选和公开更新发现检查中的旧基线包安装也 Failed，原始失败与日志继续保留。后者失败发生在安装 `1.0.2-dev.1+integration.1` 时，尚未验证本机更新发现。CI 通过不能消除这个本机间歇问题。WinError 5 与历史窗口黑图按约定暂缓，未修改系统 Blender、增加管理员跟踪或实施缓解措施。

## 当前测试入口

常规 HTTP MCP 客户端显式设置读取期限 60 秒、SDK 等待期限 90 秒，见 `scripts/mcp_checks.py`。生命周期中断用例的 SDK 15 秒用于验证取消与进程清理；定向诊断的 `--http-read-timeout` 可以故意复现短读取期限，不是常规默认值。

原生集成检查通过已保存场景、一个真实链接库和一个有 fake user 的缺失图片，调用全部六个 CLI 工具。在 PATH 为空且传入错误 BLENDER_PATH 的条件下，核对工具实际使用宿主 Blender。安装器报告 ERROR 时直接失败，不导入未安装的 Extension。重试会保留原 Failed 报告和必要日志；候选替换只使对应输出目录旧包的证据失效。

部署后使用 `scripts/test_index_sync.py --blender <可执行文件> --index-url <统一索引> --output <报告>` 验证实际官方同步与选包。增加 `--previous-package <真实旧发布 ZIP> --expected-version <新版本>` 时，入口先核对发布基线的大小和 SHA-256，在隔离仓库安装旧包，再切换到公开统一索引，并要求 Blender 官方更新统计恰好发现一个更新。此检查不会启用旧插件或修改系统配置。

当前维护代码的 94 项单元测试与正式包构建时的 81 项分别记录。统一索引入口使用共享安装捕获器，在原生安装器返回 ERROR 时直接报告原错误，阻止后续读取尚未安装的 manifest；这属于测试维护，不是 WinError 5 的修复。完整交付与剩余限制见[本轮更新记录](release-reliability-update.md)。

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
