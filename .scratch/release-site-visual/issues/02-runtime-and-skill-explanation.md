Status: ready-for-agent
Category: enhancement
Implementation: complete

# 展示运行流程与 Extension 开发技能

根据六项网页批注增强双语页面：

1. 在安装对比中增加官方 Extension + stdio 和集成 Extension + HTTP 两张运行流程图，显示进程、协议、启动控制、安装位置和请求/结果流向。
2. 核对更新索引的版本范围，分别标注 Blender 5.1 stable 与 5.2 preview，并展示添加远程仓库、同步、安装与检查更新的操作步骤。索引能力在两个发布线都可用。
3. 使用内置 imagegen 生成 Agent、MCP、本机 Blender 双向协作的主图，保存到项目并替换现有主图引用。
4. 在官方来源区并列提供 MCP 源码仓库与 Blender Lab 项目介绍链接。
5. 对比说明下放置默认折叠的官方 Extension + stdio 安装指引，代码块给出不固定版本的官方来源安装命令与注释，说明客户端管理服务。
6. 资源区专门介绍本仓库的 blender-mcp-skills、Blender 4.2+ Extension 模板、注册回滚、依赖与跨系统流程、构建校验，并提供技能/模板和 GitHub 参考来源链接。

沿用静态 HTML/CSS/JS 与 Python 渲染；不新增网站依赖。下载链接和发布元数据保持一致。验证覆盖相关网页测试、四个双语渠道页面、桌面/700px/窄屏、默认折叠和键盘展开、版本切换、复制与图像加载、流程和引用的事实核对。

## Comments

Blender 5.1 官方扩展仓库文档已确认远程仓库与更新能力；5.2 preview 索引只对应 5.2 发布线，页面按每个通道的兼容范围显示索引说明。

六项页面改进已在中英文主页与 preview 渠道页实现。11 项网页测试 Passed；1440/1107/874/768/700/390/320px × 两种语言 × 两种渠道共 28 种浏览器组合 Passed；禁用 JavaScript 的四个页面、默认折叠与键盘展开、真实浏览器剪贴板、图像加载和固定导航 Passed。四份发布元数据原始字节及六个下载 URL 保持一致。

流程与命令依据本地官方子模块的 `README.md`、`mcp/README.md`、`mcp/pyproject.toml` 及集成进程、偏好面板实现核对；未执行安装示例。技能介绍依据本仓库模板、参考说明与 `.gitmodules`。主图保存为 `web/agent-blender.png`，内置 imagegen 的完整提示词与生成来源记录在 `build/visual-refresh/runtime-skill/image-generation.json`。浏览器报告和截图位于同目录；人工视觉验收与远端部署 Not Run。
