Status: ready-for-agent
Category: enhancement
Completion: complete

# 对齐运行图布局并调整文字排版

按用户反馈，四份中英文运行图使用相同组件位置：客户端配置左上、工具依赖右上、智能体左中、MCP 服务右中、Blender 宿主左下、Extension 桥接右下。背景框继续表达两种安装方式的不同区域；请求、结果和进程控制保持实际方向。

黄色安装区域标题增大；节点中的三行文字整体垂直居中；流程线标签使用透明背景，并调整标签位置防止文字与线条重叠。SVG 与交互原图同步更新。

验收四份 Archify showcase 产物、916px 实际显示与默认原图、对应组件坐标、文字居中和标签背景；运行现有网页测试及响应式回归。固定来源、下载、发布 JSON 和既有 JavaScript 保持一致。

## Comments

- 2026-10-08：依据新的布局与文字反馈开始实施，保留此前检查记录，生成新的本地证据目录。
- 2026-10-08：实施与本地验证完成。四图共用 1000×720 画布与六个组件坐标；区域标题增大，节点三行文字居中，连线文字无底色，HTTP 请求与控制线分别绘制。四份 Archify showcase 的四个 gate 全部 Passed；11 项网页测试、32 组响应式页面、四个禁用 JavaScript 页面、真实剪贴板与四个原图打开和放大检查 Passed。916px 实际测量的区域标题最小 14.904px，文字中心最大偏差 1.516 SVG 单位；四图来源、关系和安装分组与基线一致。截图由智能体检查 Passed，证据见 `build/visual-refresh/aligned-diagrams/`、`aligned-diagrams-page/` 和 `delivery.json`。人工视觉验收、真实 Blender 工具执行、远端部署 Not Run。
