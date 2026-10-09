Status: ready-for-agent
Category: enhancement
Completion: complete

# 将 MCP 工具改为默认折叠的单列条目

六个工具在全部中英文页面中一行一个，默认关闭。使用原生 details/summary，点击或键盘操作后显示现有用途、工具名称、参数与提示语；多个条目可以独立展开。保持原有工具内容与下载数据，复用页面颜色和焦点样式。

检查默认状态、实际鼠标和键盘展开/收起、禁用 JavaScript 后的操作、桌面与窄屏单列布局，并运行现有网页测试。原图不重新生成。

## Comments

- 2026-10-08：依据用户对工具卡片的折叠和单列反馈开始实施。
- 2026-10-08：实施完成。11 项网页测试、四种宽度的双语首页与渠道页共 16 组默认状态、单列布局、鼠标/键盘操作、独立展开、内容和下载保留检查 Passed；四个禁用 JavaScript 页面 Passed。914px 中文折叠状态及 390px 中英文展开/折叠截图由智能体检查 Passed。证据为 `build/visual-refresh/collapsed-tools/report.json` 与 `delivery.json`。既有 JavaScript、图表和发布 JSON 保持一致；人工视觉验收、真实 Blender 工具执行和远端部署 Not Run。
