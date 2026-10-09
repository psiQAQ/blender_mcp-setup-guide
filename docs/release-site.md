# 发布网站维护

发布站点是现有 GitHub Pages 上的静态页面。`web/` 保存网页模板、样式和素材，`scripts/pages_render.py` 渲染页面，`scripts/pages_site.py` 汇集已发布的渠道。网站内容与下载入口使用线上已验证的 `publication.json` 和 `index.json`；修改外观不产生新的 Extension 版本。

## 更新入口

| 操作 | `Refresh release website` 的行为 |
| --- | --- |
| 向 `main` 推送网页、渲染器、渠道脚本、网页测试或本维护文档 | 自动重新渲染并部署 |
| 在 Actions 中手动运行 `Refresh release website`，不填写恢复 run ID | 使用当前 `main` 的网页代码刷新 |
| 从新的维护提交填写 `publication_run_id` | 核验并重新部署该发布流程已验证的完整网站制品 |
| 本仓库的 `Publish validated integration` 成功完成 | 从已发布渠道读取数据，使用当前 `main` 恢复统一外观 |

工作流的完整路径过滤见 `.github/workflows/pages.yml`。它只监听包发布工作流，不监听自身，因此不会形成部署循环。`workflow_run` 必须成功且来源仓库匹配；自动刷新检出 `main`，不运行触发分支的代码，也不下载触发工作流的 artifact。显式恢复使用所选维护提交，并检查原发布流程及下载制品的来源。

## 验证与部署

1. 从 GitHub Pages 配置获取站点根 URL，并用 Python 3.13 运行 `python -B scripts/run_checks.py`。
2. `pages_site.py --refresh` 获取现存渠道的原始 JSON，核对版本、平台、兼容范围及 ZIP 的大小与 SHA-256，再渲染新页面。
3. 部署前重新读取线上不可变记录与安装包；不一致或网络获取失败即停止，不以示例版本或空下载入口代替。
4. 上传静态站点并部署到现有 `github-pages` 环境。渠道 JSON 与本轮保存的校验元数据另外作为 `release-site-verification` artifact 保存 7 天。
5. 使用构建时检出的同一个 `main` 提交，先运行 `wait_deployment.py`，等待普通公开 URL 的 JSON 字节与本次部署制品完全一致；最多等待 660 秒，每 15 秒核对一次，保留缓存未更新的观察记录。超时即 Failed。随后以 `--deployed` 重新验证目标通道、根统一索引与公开下载。此步骤只消费本次网站工作流生成的元数据。

网站刷新与包发布共用 `extension-release` 并发组，且不取消正在执行的任务，避免两个部署同时覆盖渠道。网站工作流没有 Release 写权限，不创建、上传或替换安装包，也不需要下载 Blender 或执行三平台重建。现有 `Validate Extension` 工作流的推送触发范围由其自身配置独立决定。

尚未发布的可选渠道可以缺席；已发布渠道的无效 JSON、缺失索引、校验不符和下载失败必须报错。根目录 `index.json` 是 Blender v1 统一索引，自动匹配 Blender 版本和系统平台。同一 Blender 发布线优先稳定版；没有稳定版时采用预览版。当前包含 5.1 stable 与 5.2 preview 的六个平台条目。独立通道为 `blender-5.1/stable/index.json`、`blender-5.2/preview/index.json` 和可选的 `blender-5.2/stable/index.json`；独立预览索引支持主动选择预览版。各单通道保留三个条目与原始字节，下载 URL、版本、大小和 SHA-256 保持一致。首次构建从旧根索引迁移 5.1，后续使用各通道索引与发布记录生成根索引；根 `publication.json` 继续镜像 5.1 发布记录。重叠的兼容范围会阻止构建。

## 本地预览与校验

在仓库根目录执行。默认输出为 `build/latest/site`，完整生成后替换旧网站；命令会读取并验证公开安装包。指定外部输出时要求目录尚不存在。

```bash
python -B scripts/run_checks.py
python -B scripts/pages_site.py --base-url https://notes.psiqaq.cn/blender_mcp-setup-guide --refresh --site build/latest/site
python -B scripts/pages_site.py --base-url https://notes.psiqaq.cn/blender_mcp-setup-guide --site build/latest/site
python -m http.server 8000 --directory build/latest/site
```

检查首页和已发布渠道页的移动端排版、版本切换、安装步骤、下载链接及键盘操作。版本、文件大小和校验值应与 JSON 一致。失败时先检查 Actions 日志中的具体渠道或下载地址；修复后重新运行网站工作流。不要用跳过校验的方式发布。

生成 `build/latest/site` 后，运行 `node scripts/test_public_pages.cjs` 检查实际公开网站。入口使用已安装的 Playwright 和浏览器，通过真实导航读取六份公开 JSON，与本地部署制品逐字节比较；同时检查中英文的桌面/手机布局、版本切换、下载与校验值、索引复制、固定导航及禁用 JavaScript 的下载入口。`PAGES_BASE_URL` 和 `PAGES_SITE` 可指定站点与期望制品。报告位于 `build/latest/public-browser-tests.json`，元数据和截图位于 `build/latest/evidence/browser-public/`。若已有 Failed 报告，先按构建缓存规则保留报告和诊断，再重新运行；这些检查不替代 ZIP 的完整下载哈希校验。

## 发布分支与网站刷新

两条维护分支使用与 `main` 一致的渲染器和渠道组合逻辑。包发布先核对草稿资产的认证下载，以及线上保留通道的公开下载；新草稿包尚无公开 URL，此时不进行公开下载。发布 Release 后，再核对全部新资产的公开大小与 SHA-256，部署索引并执行三平台公开安装。

GitHub API 创建草稿后的可见性可能延迟。发布器只创建一次草稿，随后最多查询六次，间隔为 1、2、4、8、16 秒；仍不可见则直接失败，不上传或公开资产。来源标记、提交、通道与完整资产哈希仍须匹配。

Pages 部署成功与缓存更新是两个可观察状态。发布工作流在三平台公开安装前等待根索引、根发布记录及各通道 JSON 与部署制品一致，再执行大小/hash、官方安装和真实 MCP 检查；不会使用加查询参数的地址代替用户实际使用的 URL。

发布工作流成功后，自动刷新使用当前 `main` 重新生成统一页面；等待该工作流完成后再发布另一条线。若自动刷新失败，检查日志后重跑刷新，保留已发布安装包和渠道记录。

若包发布已完成 Pages 部署，但后续公开安装验证失败，整个发布工作流会失败，自动网站刷新不会触发。此时先检查公开安装失败原因；只需恢复外观时，可单独手动运行 `Refresh release website`，它仍会重新验证线上安装资产与不可变记录。

如果部署制品已包含新版元数据、普通公开 URL 仍返回旧文件，不能用读取旧渠道的常规刷新代替恢复。选择一个新的维护提交，运行 `Refresh release website` 并填写原发布 run ID。`deployment_recovery.py` 要求原流程的资产发布和部署均已成功，三个平台的原报告全部仅为安装前的索引哈希不匹配；安装失败、已开始的工具检查以及其他错误均不能走此路径。脚本重新核对 Release 来源、通道索引、根统一索引、六个平台资产的大小及完整 SHA-256，使用原完整网站制品部署，不改写安装包或已发布标签。新部署提交必须与原发布提交不同，避免复用其 Pages 部署标识。部署后的等待与下载校验仍然执行。

普通公开 URL 与恢复制品一致后，再重跑原发布流程失败的公开检查，保存新的报告和不可变回执。原 Failed 报告继续保留；不能把网站恢复本身记作原生安装通过。

## 页面文件与兼容约定

- `web/index.html` 定义语义化页面结构；`web/site.css` 提供响应式布局；`web/site.js` 仅增强版本切换与复制索引。
- `web/agent-blender.png` 是通过内置 imagegen 生成的 Agent → MCP → Blender 请求与结果返回示意，并非真实客户端运行截图；`web/mark.svg` 是本集成项目的独立标记。图像提示词与生成来源保存在本地 `docs/references/hero-image-generation.json`。
- `scripts/pages_render.py` 保存中英文文案，生成首页、`en/` 与已发布渠道的中英文页面。每个页面都包含全部真实下载链接，禁用 JavaScript 后仍可使用。
- 版本、下载 URL、大小和 SHA-256 从验证通过的发布记录取得。历史 5.1 记录缺少的通道与 Blender 范围只在展示层使用兼容默认值，不回写 JSON。
- 外观文件可重新生成。单通道 `index.json`、`publication.json` 和安装 ZIP 保持各自的不可变校验边界；根索引随通道选择规则重新生成。
- CSS、脚本、PNG 与 SVG 均为站内资源，不依赖外部字体、分析服务、CDN 或浏览器端 GitHub API。

页面按 Hero、功能与安装方式对比、渠道下载、四步安装、FAQ 和 Extension 开发技能专区组织。顶部导航在“常见问题”后提供“Extension 开发 Skill”入口，在滚动时保持可见；比较表在自己的容器内横向滚动。官方安装方法默认折叠，代码示例从官方来源安装且不固定版本；FAQ 与安装折叠区使用原生 `details/summary`。

两套 Archify 运行图说明 stdio / Streamable HTTP、TCP 桥接、请求与结果方向、MCP 进程控制归属和安装位置。背景框表示安装区域；运行进程在节点中注明。两图共用 1000×720 画布与组件坐标：客户端配置左上、智能体左中、Blender 宿主左下；工具依赖、MCP 服务和 Extension 桥接依次位于右侧。节点标题使用 18–20px 字号，说明、安装位置和接口使用 13–15px 字号，三行内容整体垂直居中；黄色区域标题使用 16–18px 字号。流程线标签为透明背景，独立的文字测量边界用于检查遮挡；请求与控制线使用不同路径。网页使用 SVG 预览，916px 页面可完整横向显示；更窄屏幕可在图内横向滚动。完整 HTML 原图默认显示安装位置，并支持交互放大。中文与英文各有独立原图，文件位于 `web/diagrams/`，由渲染器复制到 `assets/diagrams/`。正文同时解释关键关系，禁用 JavaScript 时仍可读取。

图下提供六个实用 MCP 工具，每个工具使用一行原生 `details/summary`，默认折叠，展开后显示名称、用途、参数与提示语。条目可以分别展开，支持鼠标、键盘与禁用 JavaScript 的浏览器。工具名称和参数来自两条发布线的实际上游注册函数。`render_viewport_to_path` 的输出位于 Blender 的 MCP 临时目录，应使用返回的 `filepath`；窗口截图工具需要 Blender GUI。

5.1 stable 与 5.2 preview 各自提供兼容范围对应的 Extensions 索引，更新区显示版本标签和添加仓库、同步、安装、检查更新的步骤。此功能在两条发布线中均可用，安装包与索引以对应通道为准。

技能专区专门介绍 `.agents/skills/blender-mcp-skills/` 与 Blender 4.2+ Extension 模板、注册回滚、构建校验和跨系统开发，提供技能/模板源码及 `.gitmodules` 中七个 GitHub 参考项目的入口。

视觉参考固定为 AstroWind 提交 `14e1a691f80548dcc36370847b1a02c0d0b12821`，来源与依赖核对记录见[视觉改进规格](../.scratch/release-site-visual/spec.md)。外观继续由本仓库原生静态模板渲染。

## 更新运行图

绘图工具基于 [Archify v3.0.1](https://github.com/tt-a1i/archify/tree/2ab3cae7ac2c2a55d7386ca789d03c4fcd31816c)，固定提交为 `2ab3cae7ac2c2a55d7386ca789d03c4fcd31816c`。原始源码位于已忽略的 `build/latest/inputs/archify/2ab3cae7ac2c2a55d7386ca789d03c4fcd31816c/`。工作副本应用 `web/diagrams/archify-readability.patch`：增大节点、区域和接口字号，居中节点文字，移除流程线标签底色并同步文字测量边界，让安装位置在默认 READ 视图显示。showcase 背景框顶部跟随标题栏，左右空间按安装区域的 padding 保留，避免标题上方因宽侧边距出现空白。补丁只修改 Architecture 渲染器及标签定位，没有依赖变更。来源和补丁 SHA-256 记录在 `docs/references/website-sources.lock.json` 中。

修改 web/diagrams/{stdio,http}.{zh,en}.json 时，核对 meta.repository 与 sources 指向的已提交代码。使用 scripts/render_diagrams.py 完成四图的 showcase finalize：脚本核验固定补丁，在临时目录建立唯一工作副本，通过后把原图与 gate 记录替换到 build/latest/diagrams，结束后清理工作副本。

将通过全部 gate 的 HTML 复制到 web/diagrams/，运行 node scripts/export_diagrams.cjs 使用原生深色 SVG 导出，再重新生成网站并运行 node scripts/test_pages.cjs 检查双语索引复制、版本切换、手机布局与固定导航。浏览器路径使用 ARCHIFY_CHROME 或 BROWSER_BINARY；Playwright 路径使用 PLAYWRIGHT_MODULE。这些入口复用已安装工具。

原图保留 Archify 的交互与本地字体。MIT 版权及许可见 `web/diagrams/LICENSE.archify.txt`，内嵌 JetBrains Mono 的 OFL-1.1 许可见 `JetBrainsMono-OFL.txt`，来源见 `NOTICE.txt`。这些文件随图表一起复制，图表不使用第三方品牌标志。
