# Blender MCP 集成设计

产品为三个平台的 Extension ZIP：Windows x64、Linux x64、macOS Apple Silicon。5.1 稳定线范围为 5.1.0 ≤ Blender < 5.2.0；5.2 预发布线范围为 5.2.0 ≤ Blender < 5.3.0；两者使用 CPython 3.13。Blender 5.0 使用 Python 3.11，不适用。通用模板保持 Blender 4.2+。

5.1 官方来源固定 v1.0.3 / `2cea8d566dde07fbac28a61d698909d69724e853`，集成版本为 `1.0.3+integration.1`。5.2 来源固定 main / `dbbf836ad4b1025f14a2b3b504c43903f39e0b04`，集成版本为 `1.0.2-dev.1+integration.1`。来源通过 `submodules/blender_mcp` 固定；每个包包含桥接、26 个工具、提示词、API/手册数据、许可证和锁定依赖。Windows 使用 40 个依赖，Linux/macOS 使用 39 个。

## 服务与状态

Blender 主进程导入标准库集成代码和官方桥接，使用配套 Python 的 `-I -S -B` 子进程运行 MCP SDK 与 HTTP。服务通过 `site.addsitedir` 初始化私有依赖目录，保留 `.pth`、`.dist-info`、包数据和动态库布局；原生导入位置必须位于该目录。pywin32 只在 Windows 初始化。

HTTP 与桥接仅监听同机 loopback，分别检查凭据；HTTP 同时检查 Host/Origin。用户目录保存日志、凭据和导出的 Codex、Claude Code、OpenCode 配置。凭据与偏好在升级后保留。

生命周期覆盖重复启动、端口冲突、异常退出、禁用启用和停止清理。Windows 使用父进程句柄；Linux/macOS 监测父进程关系变化。Blender 突然退出后服务结束并清理会话文件。清理逐项尝试资源，保留错误和未释放资源引用，完成清理前禁止重启。

## 构建与发布

构建按本机系统、架构和 CPython ABI 验证平台配置。依赖从固定 wheels 构建，校验来源版本、SHA-256 和最终 ZIP；不使用用户已安装的依赖或系统全局 site-packages。

每个渠道的 Release 包含三个平台安装 ZIP、各自的校验文件和一个证据 ZIP，共七个附件。证据 ZIP 保存原始来源 JSON 及验证报告。渠道索引包含同一 ID/版本的三个互斥平台条目；publication.json 记录渠道、版本和完整资产集合。同版本的单个平台资产也不可替换。根目录服务 5.1 stable，5.2 使用独立的 preview/stable 路径；部署保留其他渠道的原始索引与资产 hash。

发布复用同一提交的原生 CI 产物。所有平台、报告和来源通过核对后，draft 资产逐一回读，验证完整索引，再公开 Release 并部署 Pages。公开索引安装由三个原生 runner 验证。人工 GUI/客户端验收与自动化 CI 分开记录。
