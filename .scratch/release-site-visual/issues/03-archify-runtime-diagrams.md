Status: ready-for-agent
Category: enhancement
Completion: complete

# Archify 运行图、开发 Skill 导航与实用 MCP 工具

在顶部导航的“常见问题”后加入“Extension 开发 Skill”，跳转到现有开发技能区。中英文导航在桌面和手机滚动、锚点跳转时保持可见。

使用用户指定的 [tt-a1i/archify](https://github.com/tt-a1i/archify) 绘制官方 Extension + stdio 和集成 Extension + HTTP 两套运行图。固定 v3.0.1 的 tag 对象 `679f195584e4216fd582c073d8964b3a9f59107e` 与提交 `2ab3cae7ac2c2a55d7386ca789d03c4fcd31816c`。背景框区分安装区域，节点明确运行进程，箭头分别标注请求、结果和进程控制。说明默认端口、客户端配置、外部工具环境、随包依赖、桥接和 bpy 执行关系。

网页提供 SVG 预览和可交互的完整原图，附上双语文字说明。列出六个实际注册的常用 MCP 工具，给出用途、参数和智能体使用示例。

## 实施与验收

1. 核对 Archify skill、许可证和执行范围；源码放在已忽略的 `build/visual-refresh/archify-source/`。使用已有 Node 和 Edge，生成过程的临时目录位于本次任务目录。
2. 完成四份中英文候选，运行 Archify showcase finalize，包括来源校验、产物校验和真实浏览器检查；用其原生导出功能产生 SVG。
3. 接入现有静态渲染器，更新导航、运行图和工具说明；保存 MIT 与字体许可，记录来源提交和资产 hash。
4. 运行现有网页测试，验证七种宽度的中英文主页与渠道页、键盘导航、无 JavaScript 正文、原图访问和复制功能。检查截图，确保没有页面横向溢出或锚点标题遮挡。
5. 六个下载链接与四份发布 JSON 保持一致。人工视觉验收和远端部署为独立状态。

## Comments

- 2026-10-08：依据用户最新两条网页评论开始实施，沿用现有发布页，不变更项目依赖。
- 2026-10-08：五个导航入口、两套 Archify 图及六个实用 MCP 工具已完成。四份中英文候选均通过 showcase 的 validate、deliver、check、browser-check；网页使用原生深色 SVG 导出与完整 HTML 原图，许可随资产复制。
- 验证 Passed：11 项网页测试；七种宽度、两种语言、两个页面入口共 28 种组合；四个禁用 JavaScript 页面；实际原图新标签页打开、四个原图的放大交互及本地资源检查；真实剪贴板。工具名称、参数和 Python 示例语法在两条实际上游提交中核对。
- 截图检查 Passed，由智能体检查页面和原图；HTTP 图保留一个已处理的线交叉，无连接节点，已检查其控制与结果路径。人工视觉验收、真实 Blender 工具执行和远端部署 Not Run。
- 证据：`build/visual-refresh/delivery.json`、`archify/finalize-report.json`、`archify/mcp-tools.json`、`archify-page/report.json` 和 `archify-page/interaction-report.json`。四份渠道 JSON 与六个下载 URL 保持一致。
