# 发布网站维护

发布站点是现有 GitHub Pages 上的静态页面。`web/` 保存网页模板、样式和素材，`scripts/pages_render.py` 渲染页面，`scripts/pages_site.py` 汇集已发布的渠道。网站内容与下载入口使用线上已验证的 `publication.json` 和 `index.json`；修改外观不产生新的 Extension 版本。

## 更新入口

| 操作 | `Refresh release website` 的行为 |
| --- | --- |
| 向 `main` 推送网页、渲染器、渠道脚本、网页测试或本维护文档 | 自动重新渲染并部署 |
| 在 Actions 中手动运行 `Refresh release website` | 使用当前 `main` 的网页代码刷新 |
| 本仓库的 `Publish validated integration` 成功完成 | 从已发布渠道读取数据，使用当前 `main` 恢复统一外观 |

工作流的完整路径过滤见 `.github/workflows/pages.yml`。它只监听包发布工作流，不监听自身，因此不会形成部署循环。`workflow_run` 必须成功且来源仓库匹配；构建始终检出 `main`，不运行触发分支的代码，也不下载触发工作流的 artifact。

## 验证与部署

1. 从 GitHub Pages 配置获取站点根 URL，并用 Python 3.13 运行 `python -B scripts/run_checks.py`。
2. `pages_site.py --refresh` 获取现存渠道的原始 JSON，核对版本、平台、兼容范围及 ZIP 的大小与 SHA-256，再渲染新页面。
3. 部署前重新读取线上不可变记录与安装包；不一致或网络获取失败即停止，不以示例版本或空下载入口代替。
4. 上传静态站点并部署到现有 `github-pages` 环境。渠道 JSON 与本轮保存的校验元数据另外作为 `release-site-verification` artifact 保存 7 天。
5. 使用构建时检出的同一个 `main` 提交，在部署后重新验证渠道 JSON 与公开下载。此步骤只消费本次网站工作流生成的元数据。

网站刷新与包发布共用 `extension-release` 并发组，且不取消正在执行的任务，避免两个部署同时覆盖渠道。网站工作流没有 Release 写权限，不创建、上传或替换安装包，也不需要下载 Blender 或执行三平台重建。现有 `Validate Extension` 工作流的推送触发范围由其自身配置独立决定。

尚未发布的可选渠道可以缺席；已发布渠道的无效 JSON、缺失索引、校验不符和下载失败必须报错。根目录的 Blender 5.1 stable 索引及 5.2 preview/stable 子路径仍由既有渠道规则管理。页面应从记录生成下载链接与版本信息，按 Blender 版本和平台展示，不将两个渠道合并成一个“最新版”。

## 本地预览与校验

在仓库根目录执行。输出目录必须尚不存在；命令会读取并验证公开安装包，但不会部署网站。

```bash
python -B scripts/run_checks.py
python -B scripts/pages_site.py --base-url https://notes.psiqaq.cn/blender_mcp-setup-guide --refresh --site build/release-site-preview
python -B scripts/pages_site.py --base-url https://notes.psiqaq.cn/blender_mcp-setup-guide --site build/release-site-preview
python -m http.server 8000 --directory build/release-site-preview
```

检查首页和已发布渠道页的移动端排版、版本切换、安装步骤、下载链接及键盘操作。版本、文件大小和校验值应与 JSON 一致。失败时先检查 Actions 日志中的具体渠道或下载地址；修复后重新运行网站工作流。不要用跳过校验的方式发布。

## 旧发布分支的短暂外观恢复窗口

旧发布分支可能仍携带早期 HTML 生成器。它完成包发布和 Pages 部署后，页面可能短暂显示旧样式；随后成功的发布完成事件触发本网站工作流，使用 `main` 的渲染器恢复外观。恢复需要等待该工作流构建和部署完成，不是即时切换。

若自动刷新失败，已发布安装包保持原状，页面可能继续显示旧样式。查看失败日志并手动重跑刷新。长期方案是将当前渲染器及必要的渠道组合逻辑回移到维护中的发布分支，使包发布直接生成同一套页面；不要改变历史版本的安装包和渠道记录。

若包发布已完成 Pages 部署，但后续公开安装验证失败，整个发布工作流会失败，自动网站刷新不会触发。此时先检查公开安装失败原因；只需恢复外观时，可单独手动运行 `Refresh release website`，它仍会重新验证线上安装资产与不可变记录。

## 页面文件与兼容约定

- `web/index.html` 定义语义化页面结构；`web/site.css` 提供响应式布局；`web/site.js` 仅增强版本切换与复制索引。
- `web/agent-blender.png` 是通过内置 imagegen 生成的 Agent → MCP → Blender 请求与结果返回示意，并非真实客户端运行截图；`web/mark.svg` 是本集成项目的独立标记。图像提示词与生成来源保存在本地 `build/visual-refresh/runtime-skill/image-generation.json`。
- `scripts/pages_render.py` 保存中英文文案，生成首页、`en/` 与已发布渠道的中英文页面。每个页面都包含全部真实下载链接，禁用 JavaScript 后仍可使用。
- 版本、下载 URL、大小和 SHA-256 从验证通过的发布记录取得。历史 5.1 记录缺少的通道与 Blender 范围只在展示层使用兼容默认值，不回写 JSON。
- 外观文件可重新生成。`index.json`、`publication.json` 和安装 ZIP 保持各自的不可变校验边界。
- CSS、脚本、PNG 与 SVG 均为站内资源，不依赖外部字体、分析服务、CDN 或浏览器端 GitHub API。

页面按 Hero、功能与安装方式对比、渠道下载、四步安装、FAQ 和 Extension 开发技能专区组织。顶部导航在“常见问题”后提供“Extension 开发 Skill”入口，在滚动时保持可见；比较表在自己的容器内横向滚动。官方安装方法默认折叠，代码示例从官方来源安装且不固定版本；FAQ 与安装折叠区使用原生 `details/summary`。

两套 Archify 运行图说明 stdio / Streamable HTTP、TCP 桥接、请求与结果方向、MCP 进程控制归属和安装位置。背景框表示安装区域；运行进程在节点中注明。两图共用 1000×720 画布与组件坐标：客户端配置左上、智能体左中、Blender 宿主左下；工具依赖、MCP 服务和 Extension 桥接依次位于右侧。节点标题使用 18–20px 字号，说明、安装位置和接口使用 13–15px 字号，三行内容整体垂直居中；黄色区域标题使用 16–18px 字号。流程线标签为透明背景，独立的文字测量边界用于检查遮挡；请求与控制线使用不同路径。网页使用 SVG 预览，916px 页面可完整横向显示；更窄屏幕可在图内横向滚动。完整 HTML 原图默认显示安装位置，并支持交互放大。中文与英文各有独立原图，文件位于 `web/diagrams/`，由渲染器复制到 `assets/diagrams/`。正文同时解释关键关系，禁用 JavaScript 时仍可读取。

图下提供六个实用 MCP 工具，每个工具使用一行原生 `details/summary`，默认折叠，展开后显示名称、用途、参数与提示语。条目可以分别展开，支持鼠标、键盘与禁用 JavaScript 的浏览器。工具名称和参数来自两条发布线的实际上游注册函数。`render_viewport_to_path` 的输出位于 Blender 的 MCP 临时目录，应使用返回的 `filepath`；窗口截图工具需要 Blender GUI。

5.1 stable 与 5.2 preview 各自提供兼容范围对应的 Extensions 索引，更新区显示版本标签和添加仓库、同步、安装、检查更新的步骤。此功能在两条发布线中均可用，安装包与索引以对应通道为准。

技能专区专门介绍 `.agents/skills/blender-mcp-skills/` 与 Blender 4.2+ Extension 模板、注册回滚、构建校验和跨系统开发，提供技能/模板源码及 `.gitmodules` 中七个 GitHub 参考项目的入口。

视觉参考固定为 AstroWind 提交 `14e1a691f80548dcc36370847b1a02c0d0b12821`，来源与依赖核对记录见[视觉改进规格](../.scratch/release-site-visual/spec.md)。外观继续由本仓库原生静态模板渲染。

## 更新运行图

绘图工具基于 [Archify v3.0.1](https://github.com/tt-a1i/archify/tree/2ab3cae7ac2c2a55d7386ca789d03c4fcd31816c)，固定提交为 `2ab3cae7ac2c2a55d7386ca789d03c4fcd31816c`。原始源码位于已忽略的 `build/visual-refresh/archify-source/`。工作副本应用 `web/diagrams/archify-readability.patch`：增大节点、区域和接口字号，居中节点文字，移除流程线标签底色并同步文字测量边界，让安装位置在默认 READ 视图显示。showcase 背景框顶部跟随标题栏，左右空间按安装区域的 padding 保留，避免标题上方因宽侧边距出现空白。补丁只修改 Architecture 渲染器及标签定位，没有依赖变更。来源和补丁 SHA-256 记录在视觉规格的 `references.lock.json` 中。

首次创建工作副本时，在仓库根目录运行以下命令；已有副本直接使用，不重复复制或应用补丁。生成使用已有 Node 与 Chromium 浏览器，网站日常构建直接复制已检查的产物。

```powershell
New-Item -ItemType Directory -Path build/visual-refresh/aligned-diagrams -Force
Copy-Item -LiteralPath build/visual-refresh/archify-source/archify `
  -Destination build/visual-refresh/aligned-diagrams/archify -Recurse
git apply --directory=build/visual-refresh/aligned-diagrams `
  --ignore-space-change web/diagrams/archify-readability.patch
```

修改 `web/diagrams/{stdio,http}.{zh,en}.json` 时，核对 `meta.repository` 的提交与 `sources` 指向的已提交代码；不要把未提交文件当作旧提交证据。修改候选后，从仓库根目录运行完整的 showcase finalize，并为新版本选用新的证据目录。例如：

```powershell
$diagramCandidate = 'web/diagrams/stdio.zh.json'
$diagramOutput = (Get-Content -Raw -Encoding UTF8 $diagramCandidate | ConvertFrom-Json).meta.output
$diagramEvidence = 'build/visual-refresh/aligned-diagrams/stdio-zh/review-next'
node build/visual-refresh/aligned-diagrams/archify/bin/archify.mjs `
  finalize architecture $diagramCandidate $diagramOutput `
  --repo-root . --quality showcase --out-dir $diagramEvidence --json
```

浏览器不在默认位置时，将 `ARCHIFY_CHROME` 指向本机 Chromium 浏览器，例如 Windows 的 Edge。生成进程的 `TEMP` / `TMP` 应指向独立的项目临时目录；本轮使用 `build/visual-refresh/aligned-diagrams/tool-temp/`，且通过 `ARCHIFY_UPDATE_CHECK_DISABLED=1` 关闭可选更新查询。

四个 gate 全部通过后，将完整 HTML 复制到 `web/diagrams/`，在原图的导出菜单选择 **SVG · 深色 / SVG · Dark**，保存对应 SVG，再重新生成并检查网页。检查请求、返回和控制线，以及背景框是否包含正确组件；自动校验和截图检查分别记录。

原图保留 Archify 的交互与本地字体。MIT 版权及许可见 `web/diagrams/LICENSE.archify.txt`，内嵌 JetBrains Mono 的 OFL-1.1 许可见 `JetBrainsMono-OFL.txt`，来源见 `NOTICE.txt`。这些文件随图表一起复制，图表不使用第三方品牌标志。
