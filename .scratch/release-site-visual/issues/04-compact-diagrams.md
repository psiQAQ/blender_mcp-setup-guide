Status: ready-for-agent
Category: enhancement
Completion: complete

# 提高运行图字号并收紧卡片布局

按照用户在 916px 页面上的反馈，增大两套运行图的节点标题、说明、安装位置与接口字号，减少节点之间的空白。SVG 预览和可交互的 HTML 原图同时更新；原图默认视图可读取安装位置。

保留六个组件、九条有向关系、安装区域和来源证据。沿用固定提交的 Archify，使用可审查的局部字号补丁；文字遮罩和测量同步增大，继续通过完整 showcase 检查。

验收包括四份中英文 Archify 产物的 validate、deliver、check、browser-check；916px 页面与默认原图的截图检查；现有网页测试和响应式回归。发布 JSON、下载 URL 与网页 JavaScript 保持一致。

## Comments

- 2026-10-08：开始实施用户的文字与布局反馈，复用已有绘图工具与本地浏览器。
- 2026-10-08：四张原图和 SVG 已同步更新。标题 18–20px，说明 14–15px，安装位置 13–14px，接口 14px；图表面积分别减少约 30%（stdio）和 43%（HTTP）。页面卡片间距由 28px 调整为 20px，内边距由 24px 调整为 18px。
- 验证 Passed：四份候选的 validate、deliver、check、browser-check；11 项网页测试；八种宽度的双语主页和渠道页共 32 种组合；四个禁用 JavaScript 页面；原图访问、真实放大控件、复制与本地资源检查。
- 916px 的四个 SVG 预览和四个默认原图均通过实际浏览器测量；预览标题最小约 14.93px，说明至少 11px，安装位置至少 10px，九个接口标签至少 11px。预览在容器内完整横向显示，原图默认可见安装位置。
- 四套图的截图由智能体检查 Passed。六个组件、九条有向关系、安装区域成员和代码来源保留；四份渠道 JSON 和六个下载 URL 校验通过。人工视觉验收、真实 Blender 工具执行和远端部署 Not Run。
- 证据位于 `build/visual-refresh/compact-diagrams/`、`compact-diagrams-page/readability-report.json`、`compact-diagrams-page/report.json` 和 `delivery.json`。
