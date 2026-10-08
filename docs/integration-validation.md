# 验证证据与适用范围

产品支持 Windows x64、Linux x64、macOS Apple Silicon 和 CPython 3.13。5.1 稳定线固定官方 v1.0.3 / `2cea8d566dde07fbac28a61d698909d69724e853`；5.2 预发布线固定官方 main / `dbbf836ad4b1025f14a2b3b504c43903f39e0b04`。兼容范围分别为 5.1.0 ≤ Blender < 5.2.0 与 5.2.0 ≤ Blender < 5.3.0。

| 检查 | 证据与状态判定 |
| --- | --- |
| 本地标准库单元测试 | 36 项 Passed，覆盖渠道与来源保护、版本排序、Pages 保留、平台锁、ABI、报告环境、配置、清理、证据归档、不可变资产、draft 恢复与鉴权重定向 |
| 原生最终 ZIP、MCP、鉴权和生命周期 | CI 的平台 integration-tests.json；必须为 Passed 并匹配 ZIP hash |
| GUI 事件循环、Timer、配置复制、重启及清理 | 平台 gui-tests.json，GUI 测试为必需项 |
| 最低版本兼容 | 平台 minimum-tests.json，5.2 线使用 5.2.0，5.1 线使用 5.1.0；使用相同最终 ZIP |
| 单平台和三平台 HTTP 索引安装与升级 | upgrade-tests.json、repository-tests.json，验证偏好/凭据及平台选择 |
| 远端资产回读和正式发布 | Release 工作流日志及逐资产 hash 检查 |
| 公开索引原生安装和真实 MCP | Release 工作流 publication-<platform> 产物中的 published-tests.json |
| 人工 GUI 与三个实际 agent 验收 | Not Run；自动化测试不能替代此项 |

托管 CI 的实际结果见 [Actions](https://github.com/psiQAQ/blender_mcp-setup-guide/actions)。正式版本的来源与绑定 ZIP 的报告保存在 [Release](https://github.com/psiQAQ/blender_mcp-setup-guide/releases) 的 `blender_mcp_integration-<version>-evidence.zip` 中；只有对应平台、候选 ZIP 和提交的 Passed 报告构成该候选的验证证据。未运行、失败或其他候选的报告不能计为通过。

本机 Blender 5.2.2 LTS / Python 3.13.13 的初始候选已通过两个模板、ZIP 校验、26 个 MCP 工具、鉴权、生命周期、预发布升级以及真实 GUI Timer、配置复制、重启、退出清理和截图检查。首次安装测试发现兼容范围硬编码，修复后重建；一次 Windows 安装目录重命名失败，在新的隔离目录重测通过。最终发布依据同一干净候选提交的三平台 CI 产物；本地初始候选不授权最终资产发布。CI 和公开安装的实际状态以绑定 ZIP hash 的报告为准。

自动化使用隔离配置；升级的前一版本包为同一实现生成的测试夹具，覆盖真实 Blender 索引同步、替换和状态迁移。首次 preview 使用前一源码 patch 版本夹具；后续采用前一 `dev.N`。GUI 截图可用于视觉检查，不构成人工操作验收。最终本机安装在公开索引验证后执行，并先备份 5.2 配置；共享扩展目录使用独立的 5.2 预发布仓库。
