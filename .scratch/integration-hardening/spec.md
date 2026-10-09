# Blender MCP 集成改进

来源：用户指定的《Blender MCP集成改进方案》对话与 `blender-mcp-pages-update.zip`。

## 交付范围

1. 应用双语发布网站补丁，保留安装索引元数据，维持原生静态构建。
2. deferred 非法结果返回工具失败；轮询异常清理服务并保留诊断。
3. CLI 使用当前宿主 Blender 可执行文件。
4. 凭据目录和文件采用用户专属权限，迁移旧权限并安全写入。
5. Stop、sidecar 崩溃和宿主退出清理在途 CLI 子进程。
6. 公开安装失败覆盖 `published-tests.json` 中的旧通过记录。
7. 每通道锁定真实旧发布包；首次发布支持明确的机制测试夹具。
8. 生成独立不可变发布后回执，支持 Release 附件幂等重试。
9. 上游巡检验证稳定基线 tag 与 commit。
10. 使用仓库级 `frontend-design` 技能增强产品展示，以固定提交的 AstroWind 为首选视觉参考；具体计划见[发布网站视觉改进](../release-site-visual/spec.md)。

## 验收与交付

- 本地标准库测试、真实 Windows Blender 最终 ZIP、MCP/CLI、生命周期和升级检查。
- GUI Timer 自动化与人工视觉验收分别记录。
- Linux/macOS 实际运行、远端 CI 和部署未运行时标为 `Not Run`。
- 交付源码、项目内候选包和验证记录；在 main 上按逻辑变化提交并推送。
- 网页视觉改进与本地自动检查已完成；人工视觉验收和远端部署按独立任务记录。
