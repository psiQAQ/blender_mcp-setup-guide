"""Render a bilingual release site from validated publication records, without network or npm."""

import html
import json
import posixpath
import shutil
from pathlib import Path
from string import Template
from urllib.parse import quote, urlsplit


WEB = Path(__file__).resolve().parents[1] / "web"
REPOSITORY = "https://github.com/psiQAQ/blender_mcp-setup-guide"
UPSTREAM = "https://projects.blender.org/lab/blender_mcp"
OFFICIAL_PROJECT = "https://www.blender.org/lab/mcp-server/#mcp-server"
SKILL_REFERENCES = (("clean-blender-addon-template", "https://github.com/martin-lorentzon/clean-blender-addon-template"),
                    ("blender-addon-template", "https://github.com/b0o/blender-addon-template"),
                    ("blender-extension-template", "https://github.com/lokimckay/blender-extension-template"),
                    ("AdvancedBlenderAddon", "https://github.com/eliemichel/AdvancedBlenderAddon"),
                    ("BlenderAddonPackageTool", "https://github.com/xzhuah/BlenderAddonPackageTool"),
                    ("blender_vscode", "https://github.com/JacquesLucke/blender_vscode"),
                    ("BlenderTemplate", "https://github.com/ux3d/BlenderTemplate"))
PLATFORMS = (("windows-x64", "Windows", "x64 / Intel & AMD", "window"),
             ("linux-x64", "Linux", "x64 / Intel & AMD", "terminal"),
             ("macos-arm64", "macOS", "Apple Silicon / ARM64", "command"))
MCP_TOOLS = (
    ("get_objects_summary", {}, ("读取场景对象", "只读", "查看对象、集合层级、选择与可见状态。", "请读取当前 Blender 场景，概述对象与集合结构。"),
     ("Inspect scene objects", "Read", "Read objects, collection hierarchy, selection and visibility.", "Read the current Blender scene and summarize its objects and collections.")),
    ("get_object_detail_summary", {"name": "Cube"}, ("检查指定对象", "只读", "按对象名称查看变换、修改器、材质与约束。请将 Cube 替换为实际对象名。", "检查 Cube 的变换、修改器和材质，解释它当前的设置。"),
     ("Inspect one object", "Read", "Read transforms, modifiers, materials and constraints. Replace Cube with an existing object name.", "Inspect Cube's transforms, modifiers and materials, and explain its settings.")),
    ("get_screenshot_of_window_as_image", {"size_limit_in_bytes": 2000000}, ("查看 Blender 窗口", "图像", "返回窗口 PNG，让智能体结合界面检查结果；需要 Blender 图形窗口。", "获取当前 Blender 窗口截图，检查场景显示是否符合预期。"),
     ("View the Blender window", "Image", "Return a window PNG so your agent can inspect the visible result. Requires a Blender GUI window.", "Take a screenshot of the Blender window and inspect the visible scene.")),
    ("get_python_api_docs", {"identifier": "bpy.types.Object"}, ("查询 bpy API", "文档", "从服务随附的 API 文档查询类、属性或函数，辅助编写目标版本代码。", "查询 bpy.types.Object 的 API 文档，说明如何读取对象的位置。"),
     ("Look up the bpy API", "Docs", "Query bundled API documentation for a class, property or function before writing version-specific code.", "Look up bpy.types.Object and explain how to read an object's location.")),
    ("execute_blender_code", {"code": 'import bpy\nresult = {"version": bpy.app.version_string, "objects": [obj.name for obj in bpy.context.scene.objects]}'},
     ("运行 Python / bpy", "执行代码", "在连接的 Blender 内执行代码。示例读取版本与对象名；将结果写入可 JSON 序列化的 result 字典。", "用 execute_blender_code 读取 Blender 版本和场景对象名，通过 result 返回。"),
     ("Run Python / bpy", "Execute", "Execute code inside connected Blender. This example reads its version and object names; return a JSON-serializable result dictionary.", "Use execute_blender_code to return Blender's version and scene object names in result.")),
    ("render_viewport_to_path", {"output_path": "scene.png"}, ("渲染当前场景", "渲染", "使用当前场景的渲染设置。图像写入 Blender 的 MCP 临时目录，按返回的 filepath 获取实际文件。", "按当前场景设置渲染 scene.png，并报告工具实际返回的文件路径。"),
     ("Render the current scene", "Render", "Use the scene's current render settings. The image goes into Blender's MCP scratch directory; use the returned filepath to locate it.", "Render scene.png with the current scene settings and report the actual returned file path.")),
)


COPY = {
    "zh": {
        "lang": "zh-Hans", "other_lang": "en", "language_label": "EN", "page_title": "下载与安装",
        "description": "基于 Blender Lab 官方 MCP 的社区集成版。下载匹配 Blender 版本的 Extension ZIP，无需另装 uv 或 Python，连接 Codex、Claude Code 与 OpenCode。",
        "skip": "跳转到内容", "navigation": "主导航", "nav_about": "功能", "nav_download": "下载", "nav_install": "安装", "nav_faq": "常见问题", "nav_skill": "Extension 开发 Skill",
        "community_label": "Blender Lab MCP 社区集成版",
        "hero_title": "让想法，<br>直接进入 Blender。",
        "hero_description": "把 AI 智能体接入你的三维工作空间。插件、服务与依赖随一个 Extension 提供，在 Blender 内完成启动和连接配置。",
        "choose_download": "选择版本下载", "quick_start": "快速开始", "scene_label": "本机连接示意", "scene_alt": "Agent 经 MCP 向 Blender 的三维场景发出请求，Blender 经 MCP 向 Agent 返回结果的双向连接示意",
        "scene_caption": "智能体发出工具请求，Blender 执行并返回场景结果。", "stat_zip": "一个 Extension 安装包", "stat_platforms": "三种原生系统平台", "stat_runtime": "无需另装 uv / Python", "official_source": "MCP 源码仓库", "official_project_label": "Blender Lab 项目介绍",
        "about_title": "保留官方能力，让安装更轻松。", "about_description": "本项目从安装指南出发，将重复的环境配置收进发布包，让你在 Blender 里完成服务启动与连接配置。",
        "origin_heading": "源于 Blender Lab", "origin_text": "MCP 工具与桥接能力来自 Blender Lab 官方项目。每条发布线固定上游来源，保留原始版权与许可证。",
        "integration_heading": "安装一个 Extension ZIP", "integration_text": "运行依赖与文档预先打包。选择与你的 Blender 版本和系统匹配的 ZIP，在偏好设置中安装并启用。", "architecture_link": "了解集成架构",
        "service_heading": "在 Blender 内管理服务", "service_text": "在插件偏好面板查看服务状态、启动或停止 MCP。服务使用当前 Blender 自带的 Python 与包内依赖。",
        "agent_heading": "连接你已有的智能体", "agent_text": "在插件面板选择客户端，复制对应连接配置。通过本机连接，让智能体读取场景、执行代码并辅助开发。",
        "comparison_title": "与本仓库保留的官方 stdio 安装方案相比", "comparison_item": "使用环节", "comparison_original": "官方 Extension + stdio", "comparison_integrated": "本仓库集成版",
        "comparison_rows": [("安装内容", "Extension 与外部 MCP 工具分别配置", "一个匹配平台的 Extension ZIP"), ("运行环境", "另外准备 Git / uv 与 MCP 工具", "包内依赖 + Blender 自带 Python"), ("服务启动", "由客户端启动 stdio 进程", "由 Blender 管理配套服务"), ("连接方式", "配置工具启动命令", "选择智能体，复制本机 HTTP 配置"), ("离线安装", "需提前备齐 Extension、工具与运行依赖", "提前下载匹配的 ZIP，安装时无需下载依赖")],
        "comparison_heading": "安装方式对比", "comparison_hint": "窄屏可横向滚动，查看完整对比。",
        "official_setup_heading": "展开官方 Extension + stdio 安装方法", "official_extension_step": "先在 Blender 的 Get Extensions → Repositories → ＋ → Add Remote Repository 中添加 Blender Lab 仓库，搜索 MCP 并安装启用。仓库地址：",
        "official_tool_step": "在系统终端使用 Git 和 uv 安装官方 Python MCP 服务到独立工具环境。以下命令适用于 PowerShell / Bash，不固定版本或提交；请让官方 Extension 与服务保持兼容。",
        "official_commands": "# 检查 Git 和 uv 已安装\ngit --version\nuv --version\n\n# 从 Blender Lab 官方源码安装 MCP 服务到 uv 工具环境\nuv tool install \"git+https://projects.blender.org/lab/blender_mcp.git#subdirectory=mcp\"\n\n# 检查命令可执行；此命令不连接 Blender\nblender-mcp --help\n\n# 查询命令所在目录，供客户端配置绝对路径\nuv tool dir --bin",
        "official_client_step": "在 Blender 偏好面板允许网络访问，启动 MCP Bridge Server；在智能体的 MCP 配置中选择 stdio，填写以下启动命令和环境变量，然后重新加载客户端。",
        "official_setup_note": "客户端负责启动 blender-mcp 进程，无需先在终端手动运行常驻服务。安装步骤与包入口依据官方源码说明：", "official_readme_label": "官方安装说明",
        "runtime_heading": "安装后，程序如何协作？", "runtime_note": "背景框表示安装区域，节点注明运行进程。绿色实线表示工具请求与执行，灰色实线表示结果返回或配置、依赖读取，紫色虚线表示服务启动与停止；端口为默认值，路径以实际配置为准。图表使用 Archify 绘制。",
        "diagram_open": "查看交互原图", "diagram_svg": "打开 SVG", "diagram_scroll": "窄屏可横向滚动，或打开原图放大查看安装位置和接口细节。",
        "stdio_flow_title": "官方 Extension + stdio", "stdio_flow_summary": "客户端读取 command 与环境变量，启动外部 uv 环境中的 blender-mcp，以 stdio 收发 MCP 请求。服务通过 localhost:9876 的 TCP 桥接访问 Blender；官方 Extension 与外部工具分别安装，桥接在 Blender 内单独启用。",
        "http_flow_title": "集成 Extension + HTTP", "http_flow_summary": "客户端通过 http://127.0.0.1:8000/ 和 Bearer token 连接。Blender 管理独立 MCP 子进程，使用宿主自带 Python 与 Extension 内的 _vendor/runtime 依赖，再经 TCP 桥接执行 bpy；桥接、工具和依赖随一个 ZIP 安装，日志与 token 保存在 Extension 用户数据目录。",
        "tools_heading": "连接后，先试这几个 MCP 工具", "tools_description": "将工具名和参数交给智能体调用，或直接使用下方提示语。实际可用工具以当前服务向客户端提供的工具列表为准。", "tools_arguments": "参数示例", "tools_prompt": "可以这样说", "tools_source_label": "查看官方完整工具文档",
        "offline_heading": "一个 ZIP，支持离线安装", "offline_advantages": "运行依赖已随包交付。提前下载匹配 Blender 版本和系统的 ZIP 后，可保存或复制到兼容电脑，在没有互联网连接时从磁盘安装；无需现场配置 Git、uv 或额外 Python，也无需再次下载依赖。",
        "offline_scope": "离线安装适用于已下载的集成包。智能体的模型服务、在线资源与后续更新是否需要互联网连接，取决于各自的运行方式；本机 MCP 连接仍需允许 Blender 的网络权限。",
        "original_note": "需要客户端管理 stdio 进程？", "original_guide": "查看官方 stdio 配置指南",
        "downloads_title": "选对版本，开始连接。", "downloads_description": "先确认 Blender 版本，再选择操作系统。稳定版与预览版使用独立更新通道。", "channel_label": "选择 Blender 版本与发布通道",
        "stable": "稳定版", "preview": "预览版", "release_notes": "发行说明", "download_zip": "下载 ZIP", "package": "安装包", "compatibility": "适用范围", "source": "官方来源",
        "preview_note": "这是基于官方 main 固定快照的预发布包。请在测试环境中使用，并为该 Blender 版本保留独立的扩展目录。",
        "stable_note": "基于官方稳定标签构建。请选择与你当前 Blender 版本和系统架构匹配的安装包。",
        "repository_title": "在 Blender 内安装与检查更新", "repository_help": "这是本发布通道的 Extensions 仓库索引。Blender 按当前系统选择安装包，并可检查该通道的更新。", "repository_available": "适用版本", "repository_steps": ["打开 Edit → Preferences → System → Network，启用 Allow Online Access。", "进入 Get Extensions → Repositories → ＋ → Add Remote Repository，将下方完整索引地址粘贴到 URL 并添加。", "同步远程仓库，搜索 Blender MCP Integrated，然后点击 Install。", "以后在仓库菜单中检查并安装可用更新。已从磁盘安装的包如位于其他仓库，应先停用原包，再安装此仓库中的包，避免重复。"], "repository_scope": "5.1 稳定版与 5.2 预览版各用独立索引。请为不同 Blender 发布线保留独立扩展目录。", "copy": "复制索引", "index_label": "Blender Extensions 索引地址",
        "technical_details": "校验与来源详情", "checksum": "安装包 SHA-256", "evidence_note": "Release 中的 evidence.zip 保存构建验证证据，不是插件安装包。发布后安装报告见 Actions；人工 GUI 与实际客户端验收另见验证文档。", "validation_link": "验证范围", "actions_link": "查看 Actions",
        "compatibility_note": "Blender 5.0 不兼容本集成包。当前包使用 CPython 3.13；macOS 包仅支持 Apple Silicon。客户端与 Blender 应运行在同一台电脑的原生系统中。",
        "history_note": "历史包、校验文件与构建证据均保留在 GitHub Releases。", "all_releases": "查看所有发行版",
        "install_title": "四步，接入你的 AI 智能体。", "install_description": "准备好 Blender，以及支持本机 HTTP MCP 的客户端。按顺序完成安装、启动、配置和验证。",
        "steps": [("安装匹配的 Extension", "在上方选择 Blender 版本和系统，下载 ZIP，无需解压。进入 Edit → Preferences → Add-ons → 菜单 → Install from Disk，安装并启用 Blender MCP Integrated。"), ("启动 MCP 服务", "启用后服务默认自动启动。在插件偏好面板等待 MCP: Running；未自动启动时，点击 Start MCP。"), ("配置你的 AI 智能体", "选择 Agent，点击 Copy Connection Configuration，将配置合并到对应客户端并重新加载。"), ("读取场景，验证连接", "让智能体通过 blender MCP 读取 Blender 版本和当前对象列表。检查工具实际返回的结果，确认连接正常。")],
        "prompt_heading": "用一次场景读取确认连接。", "first_prompt": "请使用 blender MCP 读取 Blender 版本和当前场景对象列表，并报告实际返回结果。", "full_guide": "完整安装与排障指南",
        "prompt_note": "在完成客户端配置后发送这段请求。连接失败时，先查看 MCP 状态，再核对客户端配置与排障指南。",
        "faq_description": "关于来源、版本选择与连接配置的常见问题。",
        "resources_title": "让智能体从可靠模板开始开发 Extension。", "skill_heading": "blender-mcp-skills", "skill_description": "仓库中的开发 skill 把 Blender 4.2+ Extension 模板、生命周期规则与打包检查交给智能体，让新扩展沿用可验证的开发流程。",
        "skill_benefits": [("清晰的扩展结构", "manifest、操作、面板、属性与偏好设置分别组织；默认模板不引入第三方依赖。"), ("可恢复的注册与卸载", "显式注册类，失败时回滚，卸载时逆序清理，并核对真实注册状态。"), ("从源码到可安装 ZIP", "生成模板、静态检查、官方构建与校验；按 Blender 所在系统处理路径，依赖按 wheels 交付，用户数据写入扩展用户目录。")],
        "skill_source_label": "查看 skill 的 GitHub 源码", "template_source_label": "查看 Extension 模板", "skill_install_heading": "把 skill 安装给你的智能体", "skill_install_note": "随后描述要开发的功能与最低 Blender 版本，让智能体使用模板生成扩展。模板生成和静态检查可离线完成，实际 Blender 操作前查询目标运行环境。", "template_guide_label": "阅读模板使用指南",
        "skill_references_heading": "模板与开发流程的参考项目", "skill_references_note": "本仓库整理以下开源项目的模板、打包和开发工具实践；当前模板与生命周期规则由本仓库维护。以下链接直达对应 GitHub 源码。",
        "faq_heading": "你可能还想知道", "faq": [("这是 Blender 官方发布的集成包吗？", "这是 psiQAQ 维护的社区集成发行版，基于 Blender Lab 官方 MCP。官方项目提供核心能力，本仓库提供集成安装、服务管理、界面和发布流程。"), ("已经安装了官方 MCP，应该怎么切换？", "先停止并禁用原版 MCP Extension，再启用集成版，避免桥接端口冲突。客户端原有 stdio 条目也应替换为集成版复制的 HTTP 配置。"), ("为什么没有一个通用的“最新版”下载按钮？", "不同 Blender 版本使用不同发布线。5.1 的官方稳定来源和 5.2 的 main 预览来源不能按版本数字直接比较；安装时以 Blender 兼容范围与通道为准。"), ("网站能替我生成连接 token 吗？", "连接凭据由本机插件生成。请在 Blender 偏好面板复制配置；网站不会读取或保存你的 token。配置文件包含凭据，不应提交到公开仓库。")],
        "footer_note": "由 psiQAQ 维护的社区集成版 · 核心能力来自 Blender Lab 官方 MCP", "copy_success": "索引已复制", "copy_failure": "无法自动复制，请选中索引地址并手动复制",
    },
    "en": {
        "lang": "en", "other_lang": "zh-Hans", "language_label": "中文", "page_title": "Download & install",
        "description": "A community integration of Blender Lab's official MCP. Install one Extension ZIP for your Blender version, without separate uv or Python setup. Connect Codex, Claude Code and OpenCode.",
        "skip": "Skip to content", "navigation": "Main navigation", "nav_about": "Features", "nav_download": "Download", "nav_install": "Install", "nav_faq": "FAQ", "nav_skill": "Extension Dev Skill",
        "community_label": "A community integration of Blender Lab MCP",
        "hero_title": "From an idea.<br>Into Blender.",
        "hero_description": "Connect your AI agent to your 3D workspace. The extension, service and dependencies ship together. Start the service and configure your connection inside Blender.",
        "choose_download": "Choose your download", "quick_start": "Get started", "scene_label": "Local connection illustration", "scene_alt": "An agent sends requests through MCP to a Blender 3D scene; Blender returns results through MCP to the agent",
        "scene_caption": "Your agent requests a tool. Blender executes it and returns the scene result.", "stat_zip": "One Extension package", "stat_platforms": "Three native platforms", "stat_runtime": "No separate uv / Python", "official_source": "MCP source repository", "official_project_label": "Blender Lab project overview",
        "about_title": "Official capabilities. A simpler setup.", "about_description": "This project began as an installation guide. It now packages the repeated setup work, so you can start the service and copy connection settings inside Blender.",
        "origin_heading": "Built on Blender Lab", "origin_text": "The MCP tools and bridge come from Blender Lab's official project. Every release line pins its upstream source and retains the original copyright and licenses.",
        "integration_heading": "Install one Extension ZIP", "integration_text": "Dependencies and documentation ship together. Choose the ZIP for your Blender version and system, then install and enable it in preferences.", "architecture_link": "Explore the architecture",
        "service_heading": "Manage the service in Blender", "service_text": "Check the service status, start or stop MCP in the extension preferences. The service uses the current Blender's Python and bundled dependencies.",
        "agent_heading": "Bring your own agent", "agent_text": "Select your client in the extension panel and copy its configuration. A local connection lets your agent inspect scenes, execute code and help build extensions.",
        "comparison_title": "Compared with this repository's official stdio setup guide", "comparison_item": "Setup", "comparison_original": "Official Extension + stdio", "comparison_integrated": "This integration",
        "comparison_rows": [("Installation", "Configure the Extension and external MCP tool separately", "One Extension ZIP for your platform"), ("Runtime", "Set up Git / uv and the MCP tool", "Bundled dependencies + Blender's Python"), ("Service startup", "The client launches a stdio process", "Blender manages the bundled service"), ("Client connection", "Configure a tool launch command", "Select your agent and copy local HTTP settings"), ("Offline installation", "Prepare the Extension, tool and runtime dependencies in advance", "Download the matching ZIP first; no dependency downloads during installation")],
        "comparison_heading": "Compare installation options", "comparison_hint": "On narrow screens, scroll horizontally to read the full comparison.",
        "official_setup_heading": "Show official Extension + stdio setup", "official_extension_step": "In Blender, open Get Extensions → Repositories → ＋ → Add Remote Repository and add the Blender Lab repository. Search for MCP, install and enable it. Repository URL:",
        "official_tool_step": "Use Git and uv in your system terminal to install the official Python MCP service into an isolated tool environment. These PowerShell / Bash commands do not pin a version or commit. Keep the official Extension and service compatible.",
        "official_commands": "# Check that Git and uv are installed\ngit --version\nuv --version\n\n# Install the MCP service from Blender Lab's official source\nuv tool install \"git+https://projects.blender.org/lab/blender_mcp.git#subdirectory=mcp\"\n\n# Check the executable; this does not connect to Blender\nblender-mcp --help\n\n# Find the executable directory for an absolute client command path\nuv tool dir --bin",
        "official_client_step": "Allow network access in Blender preferences and start the MCP Bridge Server. In your agent's MCP configuration, choose stdio and set the command and environment variables below, then reload the client.",
        "official_setup_note": "The client launches blender-mcp; you do not need to start a persistent process in the terminal first. Package and entry point details come from the official source:", "official_readme_label": "Official installation README",
        "runtime_heading": "How the installed programs work together", "runtime_note": "Background frames mark installation areas; nodes identify processes. Green lines show tool requests and execution; gray lines show results or access to configuration and dependencies; purple dashed lines control service startup and shutdown. Ports are defaults; use your actual paths. Drawn with Archify.",
        "diagram_open": "Open interactive diagram", "diagram_svg": "Open SVG", "diagram_scroll": "Scroll horizontally on narrow screens, or open the full diagram to zoom into installation locations and interfaces.",
        "stdio_flow_title": "Official Extension + stdio", "stdio_flow_summary": "The client reads its command and environment, launches blender-mcp in an external uv tool environment and exchanges MCP messages over stdio. The service reaches Blender through the TCP bridge at localhost:9876. The official Extension and external tool are installed separately; enable the bridge inside Blender.",
        "http_flow_title": "Integrated Extension + HTTP", "http_flow_summary": "The client connects to http://127.0.0.1:8000/ with a Bearer token. Blender manages a separate MCP child process using its bundled Python and the Extension's _vendor/runtime dependencies, then executes bpy through the TCP bridge. One ZIP installs the bridge, tools and dependencies; logs and tokens live in the Extension user data directory.",
        "tools_heading": "Useful MCP tools to try after connecting", "tools_description": "Ask your agent to call a tool with these arguments, or use the suggested prompt. The tools available to your client depend on the current MCP service's tool list.", "tools_arguments": "Example arguments", "tools_prompt": "Suggested prompt", "tools_source_label": "Read the complete official tool documentation",
        "offline_heading": "One ZIP for offline installation", "offline_advantages": "Runtime dependencies are bundled. Download the ZIP for your Blender version and system in advance, then keep it or copy it to compatible computers for installation from disk without an internet connection. No Git, uv, extra Python setup or further dependency downloads are needed during installation.",
        "offline_scope": "Offline installation applies to an already downloaded package. Your agent's model service, online resources and future updates may require internet access depending on how they run. The local MCP connection still requires Blender's network permission.",
        "original_note": "Prefer a client-managed stdio process?", "original_guide": "Read the official stdio setup guide",
        "downloads_title": "The right version. Ready to connect.", "downloads_description": "Choose your Blender version first, then your operating system. Stable and preview releases have separate update channels.", "channel_label": "Choose Blender version and release channel",
        "stable": "Stable", "preview": "Preview", "release_notes": "Release notes", "download_zip": "Download ZIP", "package": "Extension package", "compatibility": "Compatible with", "source": "Official source",
        "preview_note": "A pre-release built from a pinned official main snapshot. Use a test environment and a separate extensions directory for this Blender version.",
        "stable_note": "Built from an official stable tag. Match the package to your current Blender version and system architecture.",
        "repository_title": "Install and check updates inside Blender", "repository_help": "This is the Extensions repository index for this release channel. Blender selects a package for your system and can check for updates in the same channel.", "repository_available": "Available for", "repository_steps": ["Open Edit → Preferences → System → Network and enable Allow Online Access.", "Go to Get Extensions → Repositories → ＋ → Add Remote Repository. Paste the full index URL below into the URL field and add it.", "Sync the remote repository, search for Blender MCP Integrated and click Install.", "Use the repository menu to check for and install updates later. If a disk-installed copy is in another repository, disable that copy before installing from this repository to avoid duplicates."], "repository_scope": "5.1 stable and 5.2 preview use separate indexes. Keep separate extension directories for different Blender release lines.", "copy": "Copy index", "index_label": "Blender Extensions index URL",
        "technical_details": "Checksums & provenance", "checksum": "Package SHA-256", "evidence_note": "The Release evidence.zip contains build validation records; it is not an installable extension. Post-publication install reports are in Actions. Human GUI and client acceptance are documented separately.", "validation_link": "Validation scope", "actions_link": "View Actions",
        "compatibility_note": "Blender 5.0 is incompatible. Current packages use CPython 3.13; the macOS build is for Apple Silicon only. Run your client and Blender natively on the same computer.",
        "history_note": "Past packages, checksums and build evidence remain available in GitHub Releases.", "all_releases": "All releases",
        "install_title": "Four steps to your AI agent.", "install_description": "Bring Blender and a client that supports local HTTP MCP. Install, start, configure and verify in order.",
        "steps": [("Install your Extension", "Choose your Blender version and system above. Download the ZIP without extracting it. Open Edit → Preferences → Add-ons → menu → Install from Disk. Install and enable Blender MCP Integrated."), ("Start the MCP service", "The service starts automatically by default when enabled. Wait for MCP: Running in the extension preferences. If it has not started, click Start MCP."), ("Configure your AI agent", "Select your Agent and click Copy Connection Configuration. Merge the settings into your client configuration and reload the client."), ("Read the scene to verify", "Ask your agent to read the Blender version and current objects through blender MCP. Check the actual tool results to confirm the connection.")],
        "prompt_heading": "Check the connection with a scene read.", "first_prompt": "Use the blender MCP to read the Blender version and list the current scene objects. Report the actual results.", "full_guide": "Full installation & troubleshooting guide",
        "prompt_note": "Send this request after configuring your client. If the connection fails, check the MCP status, then your client settings and the troubleshooting guide.",
        "faq_description": "Common questions about the source, release versions and connection settings.",
        "resources_title": "Give your agent a reliable Extension template.", "skill_heading": "blender-mcp-skills", "skill_description": "This repository's development skill gives your agent a Blender 4.2+ Extension template, lifecycle rules and packaging checks for a verifiable development workflow.",
        "skill_benefits": [("A clear Extension structure", "Separate the manifest, operators, panels, properties and preferences. The default template has no third-party dependencies."), ("Recoverable registration and cleanup", "Register classes explicitly, roll back on failure, clean up in reverse order and check the actual registration state."), ("Source to installable ZIP", "Scaffold, run static checks, build and validate with Blender. Adapt paths to the Blender host, bundle dependencies as wheels and store writable data in the Extension user directory.")],
        "skill_source_label": "Skill source on GitHub", "template_source_label": "Explore the Extension template", "skill_install_heading": "Install the skill for your agent", "skill_install_note": "Describe your extension's features and minimum Blender version, then ask your agent to scaffold it from the template. Scaffolding and static checks work offline; query the target runtime before operating Blender.", "template_guide_label": "Read the template guide",
        "skill_references_heading": "Reference projects for templates and development", "skill_references_note": "This repository draws on these open-source templates, packaging and development tools. The current template and lifecycle rules are maintained here. Each link opens its GitHub source.",
        "faq_heading": "A few things to know", "faq": [("Is this integration an official Blender release?", "This is a community integration maintained by psiQAQ, based on Blender Lab's official MCP. The upstream project supplies the core capabilities; this repository provides integrated installation, service management, the interface and release process."), ("How do I switch from the official MCP Extension?", "Stop and disable the original MCP Extension before enabling the integration to avoid bridge port conflicts. Replace your client's old stdio entry with the HTTP configuration copied from the integration."), ("Why is there no universal latest-version download?", "Blender versions have separate release lines. The official stable source used for 5.1 and the main preview source used for 5.2 cannot be compared by their version numbers alone. Choose by Blender compatibility and channel."), ("Can this website generate my connection token?", "The extension generates credentials on your computer. Copy the configuration from Blender's preferences panel. This website does not read or store your token. Keep configuration files containing credentials out of public repositories.")],
        "footer_note": "A community integration by psiQAQ · Powered by Blender Lab's official MCP", "copy_success": "Index copied", "copy_failure": "Automatic copy unavailable. Select the index URL and copy it manually.",
    },
}


def escape(value):
    return html.escape(str(value), quote=True)


def https_url(value):
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError("Website links require an absolute HTTPS URL without credentials")
    return escape(value)


def channel_id(path):
    return "release-" + (path.replace("/", "-").replace(".", "-") if path else "blender-5-1-stable")


def version_line(record):
    return ".".join(record.get("blender_min", "5.1.0").split(".")[:2])


def platform_icon(kind):
    paths = {"window": '<path d="M3 3h8v8H3zm10 0h8v8h-8zM3 13h8v8H3zm10 0h8v8h-8z"/>',
             "terminal": '<rect x="2" y="4" width="20" height="16" rx="3"/><path d="m6 9 3 3-3 3m6 0h5"/>',
             "command": '<path d="M8 8V5a3 3 0 1 0-3 3h14a3 3 0 1 0-3-3v14a3 3 0 1 0 3-3H5a3 3 0 1 0 3 3V8z"/>'}
    return f'<svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" aria-hidden="true">{paths[kind]}</svg>'


def runtime_diagram(mode, copy, language, asset_base):
    """Embed an Archify SVG with an accessible description and full viewer link."""
    title = escape(copy[mode + "_flow_title"])
    summary = escape(copy[mode + "_flow_summary"])
    base = escape(f"{asset_base}/diagrams/{mode}.{language}")
    owner = "client" if mode == "stdio" else "blender"
    return f'''<figure class="runtime-diagram {mode}" aria-labelledby="{mode}-flow-heading" data-transport="{mode}" data-control-owner="{owner}">
      <figcaption><div class="diagram-heading"><h5 id="{mode}-flow-heading">{title}</h5><div class="diagram-links"><a href="{base}.html?theme=dark" target="_blank" rel="noopener">{escape(copy['diagram_open'])} ↗</a><a href="{base}.svg" target="_blank" rel="noopener">{escape(copy['diagram_svg'])} ↗</a></div></div><p id="{mode}-flow-description">{summary}</p></figcaption>
      <p class="diagram-scroll-hint">{escape(copy['diagram_scroll'])}</p><div class="diagram-preview" role="region" aria-labelledby="{mode}-flow-heading" aria-describedby="{mode}-flow-description" tabindex="0"><img src="{base}.svg" alt="{title}。{summary}" loading="lazy"></div>
    </figure>'''


def mcp_tool_cards(copy, language):
    cards = []
    for index, (name, arguments, chinese, english) in enumerate(MCP_TOOLS, 1):
        title, kind, description, prompt = chinese if language == "zh" else english
        params = escape(json.dumps(arguments, ensure_ascii=False, indent=2))
        cards.append(f'''<details class="mcp-tool-card" data-mcp-tool="{name}"><summary class="tool-heading"><span class="tool-index" aria-hidden="true">{index:02}</span><span class="tool-title">{escape(title)}</span><span class="tool-kind">{escape(kind)}</span></summary><div class="tool-content"><code class="tool-name">{name}</code><p>{escape(description)}</p><div class="tool-arguments"><span>{escape(copy['tools_arguments'])}</span><pre><code>{params}</code></pre></div><p class="tool-prompt"><span>{escape(copy['tools_prompt'])}</span>{escape(prompt)}</p></div></details>''')
    return "".join(cards)


def release_panel(path, record, copy, base_url):
    identifier = channel_id(path)
    channel = record.get("channel", "stable")
    line, version = version_line(record), escape(record["extension_version"])
    release_url = f"{REPOSITORY}/releases/tag/{quote('v' + record['extension_version'], safe='')}"
    index_url = base_url.rstrip("/") + "/" + (path + "/" if path else "") + "index.json"
    source_ref = record.get("source_ref") or "v" + record.get("version", record["extension_version"].split("+")[0])
    cards, checksums = [], []
    for platform, name, architecture, icon in PLATFORMS:
        item = record["packages"][platform]
        url = https_url(item["archive_url"])
        size = item["size"] / (1024 * 1024)
        label = escape(f"{copy['download_zip']} · {name} {architecture} · Blender {line} {copy[channel]} · {record['extension_version']}")
        cards.append(f'<article class="platform-card"><div class="platform-heading">{platform_icon(icon)}<div><h4>{name}</h4><p>{escape(architecture)}</p></div></div><p class="package-meta">{size:.1f} MiB <span>·</span> .zip</p><a class="button download-button" href="{url}" aria-label="{label}">{copy["download_zip"]}<span aria-hidden="true">↓</span></a></article>')
        checksums.append(f'<div><dt>{name} {escape(architecture)}</dt><dd><code>{escape(item["sha256"])}</code></dd></div>')
    compatibility = f'{escape(record.get("blender_min", "5.1.0"))} ≤ Blender &lt; {escape(record.get("blender_max", "5.2.0"))}'
    commit = escape(record.get("commit", ""))
    source_url = f"{UPSTREAM}/src/commit/{commit}" if commit else UPSTREAM
    repository_steps = "".join(f'<li>{escape(step)}</li>' for step in copy["repository_steps"])
    return f'''<section class="release-panel" id="{identifier}" data-channel-panel aria-labelledby="{identifier}-heading">
      <div class="release-heading"><div><span class="badge {channel}">{copy[channel]}</span><h3 id="{identifier}-heading">Blender {escape(line)}</h3></div><a class="text-link" href="{https_url(release_url)}">{copy['release_notes']} ↗</a></div>
      <p class="release-compatibility">{copy['compatibility']} <strong>{compatibility}</strong></p>
      <p class="release-version">{copy['package']} {version}</p>
      <p class="channel-note {channel}">{copy[channel + '_note']}</p>
      <div class="platform-grid">{''.join(cards)}</div>
      <div class="repository-box"><div><h4>{copy['repository_title']}</h4><p class="repository-available">{copy['repository_available']}: Blender {escape(line)} · {copy[channel]}</p><p>{copy['repository_help']}</p></div><div class="copy-field"><input type="text" id="{identifier}-index" readonly value="{https_url(index_url)}" aria-label="{copy['index_label']} · Blender {escape(line)} {copy[channel]}"><button type="button" data-copy-target="{identifier}-index" hidden>{copy['copy']}</button></div><ol class="repository-steps">{repository_steps}</ol><p class="repository-scope">{copy['repository_scope']}</p></div>
      <details class="technical-details"><summary>{copy['technical_details']}</summary><p>{copy['source']}: <a href="{https_url(source_url)}">{escape(source_ref)} · <code>{commit[:12]}</code> ↗</a></p><p>{copy['checksum']}</p><dl class="checksums">{''.join(checksums)}</dl><p>{copy['evidence_note']}</p><p><a href="{REPOSITORY}/blob/main/docs/integration-validation.md">{copy['validation_link']} ↗</a> · <a href="{REPOSITORY}/actions">{copy['actions_link']} ↗</a></p></details>
    </section>'''


def render_site(site, records, base_url):
    """Write replaceable presentation files; never write release metadata or archives.

    `records` must come from pages_site.validate_index. Older 5.1 records omit
    channel and compatibility fields; preserve their bytes and apply display defaults.
    """
    https_url(base_url)
    if not records:
        raise ValueError("Cannot render a download site without published channels")
    site = Path(site)
    assets = site / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    for name in ("site.css", "site.js", "mark.svg", "agent-blender.png"):
        shutil.copyfile(WEB / name, assets / name)
    diagrams = assets / "diagrams"
    diagrams.mkdir(exist_ok=True)
    for name in ("stdio.zh.html", "stdio.en.html", "http.zh.html", "http.en.html", "stdio.zh.svg", "stdio.en.svg", "http.zh.svg", "http.en.svg", "LICENSE.archify.txt", "JetBrainsMono-OFL.txt", "NOTICE.txt"):
        shutil.copyfile(WEB / "diagrams" / name, diagrams / name)
    template = Template((WEB / "index.html").read_text(encoding="utf-8"))
    # The homepage always exists, including before the first stable publication.
    page_paths = list(dict.fromkeys(["", *records.keys()]))
    for path in page_paths:
        selected = path if path in records else next(iter(records))
        for language, copy in COPY.items():
            folder = posixpath.join(path, "en" if language == "en" else "").rstrip("/")
            alternate_folder = posixpath.join(path, "en" if language == "zh" else "").rstrip("/")
            base = base_url.rstrip("/") + "/"
            canonical_zh = base + (path + "/" if path else "")
            canonical_en = canonical_zh + "en/"
            values = {key: escape(value) for key, value in copy.items() if isinstance(value, str)}
            values["hero_title"] = copy["hero_title"]  # Trusted, repository-owned markup.
            values.update(repository=REPOSITORY, upstream=UPSTREAM, official_project_url=OFFICIAL_PROJECT,
                          official_readme_url=UPSTREAM + "/src/branch/main/mcp/README.md", canonical=https_url(canonical_en if language == "en" else canonical_zh),
                          canonical_zh=https_url(canonical_zh), canonical_en=https_url(canonical_en), initial_channel=channel_id(selected),
                          asset_base=posixpath.relpath("assets", folder or "."),
                          home_url=posixpath.relpath("en/index.html" if language == "en" else "index.html", folder or "."),
                          language_url=posixpath.relpath(posixpath.join(alternate_folder, "index.html"), folder or "."))
            doc_language = "zh" if language == "zh" else "en"
            values.update(setup_url=f"{REPOSITORY}/blob/main/docs/blender_mcp-setup_{doc_language}.md",
                          stdio_url=f"{REPOSITORY}/blob/main/docs/blender_mcp-stdio-setup_{doc_language}.md",
                          design_url=f"{REPOSITORY}/blob/main/docs/integration-design.md",
                          build_url=f"{REPOSITORY}/blob/main/docs/integration-build.md",
                          skill_url=f"{REPOSITORY}/tree/main/.agents/skills/blender-mcp-skills",
                          template_url=f"{REPOSITORY}/tree/main/.agents/skills/blender-mcp-skills/templates/extension_addon",
                          template_guide_url=f"{REPOSITORY}/blob/main/.agents/skills/blender-mcp-skills/references/template-guide.md")
            values["runtime_diagrams"] = "".join(runtime_diagram(mode, copy, language, values["asset_base"]) for mode in ("stdio", "http"))
            values["mcp_tool_cards"] = mcp_tool_cards(copy, language)
            values["tools_source_url"] = UPSTREAM + "/src/branch/main/readme_tools.rst"
            values["skill_benefits"] = "".join(f'<li><h4>{escape(title)}</h4><p>{escape(description)}</p></li>' for title, description in copy["skill_benefits"])
            values["skill_references"] = "".join(f'<li><a href="{https_url(url)}">{escape(name)} <span aria-hidden="true">↗</span></a></li>' for name, url in SKILL_REFERENCES)
            values["comparison_rows"] = "".join(f'<tr><th scope="row">{escape(row[0])}</th><td>{escape(row[1])}</td><td>{escape(row[2])}</td></tr>' for row in copy["comparison_rows"])
            buttons = []
            for key, record in records.items():
                target = posixpath.join(key, "en" if language == "zh" else "", "index.html")
                language_target = posixpath.relpath(target, folder or ".")
                buttons.append(f'<button type="button" data-channel="{channel_id(key)}" data-language-url="{escape(language_target)}" aria-controls="{channel_id(key)}" aria-pressed="false">Blender {escape(version_line(record))}<span class="badge {record.get("channel", "stable")}">{copy[record.get("channel", "stable")]}</span></button>')
            values["channel_buttons"] = "".join(buttons)
            values["release_panels"] = "".join(release_panel(key, record, copy, base_url) for key, record in records.items())
            values["install_steps"] = "".join(f'<li><span class="step-number" aria-hidden="true">{i}</span><div><h3>{escape(step[0])}</h3><p>{escape(step[1])}</p></div></li>' for i, step in enumerate(copy["steps"], 1))
            values["faq_items"] = "".join(f'<details><summary>{escape(question)}</summary><p>{escape(answer)}</p></details>' for question, answer in copy["faq"])
            destination = site / folder / "index.html"
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(template.substitute(values), encoding="utf-8")
    (site / ".nojekyll").touch()
