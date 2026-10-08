# Blender MCP integration

来源：用户于 2026-10-08 要求按照“Blender MCP集成改进方案”审查并实现。
审查基线：`a0d921d730f312ea926bee653b4a6feb4cce0fb0`。

## 交付范围

- 修复旧技能路径、缺失 schema 与入口的 validator 漏检。
- 默认模板采用显式注册、失败回滚、逆序卸载，取消运行时 pip 和全局 sys.path 修改。
- 生成器替换类、Operator、Panel 和 Scene 属性标识，两个项目可同时启用。
- 精简双语本地安装说明，删除 remote 双语教程及失效引用，统一 GPL-3.0-or-later 说明。
- 固定 Blender Lab 官方稳定标签、提交和 三平台 CPython 3.13 依赖校验值。
- Windows x64、Linux x64、macOS Apple Silicon、Blender 5.1 系列首版：各自独立的 Extension ZIP 随包交付官方桥接、服务端、文档数据和依赖。
- 使用 Blender 配套 Python 启动独立服务，默认 loopback Streamable HTTP，HTTP 与桥接均验证会话凭据。
- 服务支持启动、停止、重复启动防护、端口冲突、异常退出诊断、父进程退出后清理。
- 用户目录保存日志和客户端配置；提供 Codex、Claude Code、OpenCode 配置复制及诊断。
- 创建 CI、发布、上游同步工作流；显式比较上游版本与集成修订号，先验证产物再发布更新索引。

## 验收

- 标准库单元测试及缺失必需字段的失败场景通过。
- 最终 ZIP 通过官方 extension validate，产物不包含开发环境和构建脚本。
- 隔离配置真实安装两个模板，测试注册、卸载、回滚和命名隔离。
- 集成最终 ZIP 在隔离 Blender 中完成 MCP initialize、tools/list、场景读取及可回滚操作。
- 验证身份鉴别、端口冲突、服务异常退出、停止、再次启用和升级。
- 自动化 GUI 场景与人工验收分开记录；云端 CI、main 推送、Pages 配置与远端正式发布已获授权，全部必需验证通过后发布。
