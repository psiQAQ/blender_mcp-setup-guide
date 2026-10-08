# 网站与集成开发参考

- [原始改进方案](pages-update-original.md)：用户下载的改进包说明原文，供溯源使用。
- [主图生成记录](hero-image-generation.json)：完整提示词、工具与图像来源；主图是关系示意。
- [固定参考来源](website-sources.lock.json)：AstroWind、网页 Skill 和 Archify 的实际提交、许可证与校验值。
- 图表补丁位于 `web/diagrams/archify-readability.patch`，对应固定 Archify 提交；增大文字、居中节点内容、透明接口标签、对齐背景框顶部，没有依赖变更。

最终图表规格、交互 HTML 与 SVG 位于 `web/diagrams/`。固定工具的唯一输入快照保存在 `build/latest/inputs/archify/<commit>/`；工作副本按维护规则临时创建。最终导出使用 `scripts/export_diagrams.cjs`，网页检查使用 `scripts/test_pages.cjs`，本地预览使用 `scripts/preview_server.py`。这些浏览器工具复用已安装的 Playwright 与 Chromium；自定义路径通过 `PLAYWRIGHT_MODULE`、`BROWSER_BINARY` 和 `TEST_PYTHON` 设置。
