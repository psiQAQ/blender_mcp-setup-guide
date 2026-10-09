Status: ready-for-agent
Category: bug
Completion: complete

# 对齐集成 ZIP 安装区域的顶部

让 showcase 背景框顶部跟随标题栏，修复 HTTP 中英文运行图中集成 ZIP 标题上方的空白。保留左右留白、组件坐标、文字字号、请求和控制方向，以及单列折叠工具列表。

使用现有 Archify 重新检查并原生导出四份原图与 SVG。检查 1057px HTTP 实际预览、默认原图和标题间距，以及 916px 四图布局，核对图表规格和发布数据保持一致。

## Comments

- 2026-10-08：依据用户对集成 ZIP 背景框顶部留白的反馈开始修复。
- 2026-10-08：修复完成。showcase 背景框跟随标题栏，其顶部与标题栏间距为 4 SVG 单位；左右留白独立保留。四份规格的 SHA-256 与基线一致，原生 SVG 与交互 HTML 同步生成，四个 Archify gate 全部 Passed。1057px 中英文 HTTP 的实际预览、默认原图及 916px 四图布局检查 Passed；智能体截图检查 Passed。补丁与固定来源的对应关系检查 Passed，汇总见 `build/visual-refresh/delivery.json`。人工视觉验收、真实 Blender 执行和远端部署 Not Run。
