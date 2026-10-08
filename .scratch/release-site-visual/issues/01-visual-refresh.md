Status: ready-for-agent
Category: enhancement
Implementation: complete

# 增强发布网站的产品展示

依据[规格](../spec.md)使用已安装的 `frontend-design` 技能和固定版本的 AstroWind 视觉参考，改进 Hero、功能介绍、安装方式对比、操作步骤与 FAQ。

实现范围：`web/index.html`、`web/site.css`、必要的 `web/site.js` 与 `scripts/pages_render.py` 双语文案，按实际行为变化补充现有渲染/渠道检查。发布记录继续决定版本信息和下载入口，保留原生静态构建。

验收：中英文桌面与手机布局、键盘操作、减少动画、FAQ、复制反馈、语言/通道切换、禁用 JavaScript 的真实下载入口，以及安装元数据字节一致性。人工视觉验收和远端部署分别标记。

当前状态：整体视觉重排已实现。11 项网页回归测试与 16 种浏览器视口/语言/渠道组合 Passed；四份发布元数据 SHA-256 保持一致。键盘跳转、手机表格滚动、原生 FAQ、真实浏览器剪贴板、注入拒绝复制后的手动选择、减少动画与禁用 JavaScript 检查 Passed。

本地预览和截图保存在 `build/visual-refresh/`，汇总报告为 `delivery.json`。人工视觉验收与远端部署 Not Run。

## Comments

页面术语统一为中文“智能体”与英文“agent”；桌面和手机顶部导航在滚动时保持可见，锚点标题避开导航栏。11 项网页测试重新运行 Passed；1440/1107/874/768/390/320px 中英文页面共 12 种组合的术语、滚动和锚点检查 Passed，见 `build/visual-refresh/browser-comments/report.json` 与同目录截图。

安装对比说明已移到表格外，三列表头采用独立底色、粗体和列标题语义；新增离线安装对比与优势、适用条件。本地预览禁用缓存。当前四个页面均无旧术语；11 项网页测试与六种宽度、中英文、首页/preview 渠道共 24 种组合检查 Passed，包含表头、外部说明、离线内容、固定导航、锚点与窄屏键盘滚动。证据与截图见 `build/visual-refresh/comparison-refinements/`。
