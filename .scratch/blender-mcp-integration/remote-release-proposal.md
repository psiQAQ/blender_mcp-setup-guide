# 三平台正式发布流程

目标仓库为 psiQAQ/blender_mcp-setup-guide，用户已授权全部现有修改分批提交、推送 main、执行三平台 CI、设置 Pages 为 Actions 来源，并在验证成功后发布 v1.0.3+integration.1。

发布覆盖 Windows x64、Linux x64、macOS Apple Silicon，Blender 5.1.x / CPython 3.13。使用同一干净提交和成功 CI run 的三个不可变产物。先上传 draft 资产并回读，再验证统一 Extensions 索引，公开 Release、部署 Pages，最后从公开索引执行三平台实际安装与 MCP 检查。

人工 GUI/客户端验收单独记录。凭据、用户配置与构建缓存不进入 Git。
