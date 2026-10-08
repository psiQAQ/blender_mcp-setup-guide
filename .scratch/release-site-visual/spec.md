# 发布网站视觉改进

目标：增强 Blender MCP Integrated 的产品展示，让访问者理解产品、选择与 Blender 版本兼容的安装包，并完成首次连接。视觉参考首选用户指定的 AstroWind，实施使用现有 `web/` 与 Python 静态渲染器。

## 来源与工具

| 对象 | 固定来源 | 本项目用途 |
| --- | --- | --- |
| frontend-design | [anthropics/skills，683bc88e56f3e09ba94f7055977f3d3aa499f202](https://github.com/anthropics/skills/tree/683bc88e56f3e09ba94f7055977f3d3aa499f202/skills/frontend-design) | 页面视觉设计，已安装到 `.agents/skills/frontend-design/` |
| AstroWind | [arthelokyo/astrowind，14e1a691f80548dcc36370847b1a02c0d0b12821](https://github.com/arthelokyo/astrowind/tree/14e1a691f80548dcc36370847b1a02c0d0b12821) | Hero、功能、对比、步骤和 FAQ 的布局与组件参考 |
| AstroWind 演示 | [astrowind.vercel.app](https://astrowind.vercel.app/) | 2026-10-08 桌面与手机视觉观察；演示部署与源码提交的对应关系未验证 |

安装方式：在仓库根目录执行项目级安装，只选择 `frontend-design` 和 `codex`，CLI 固定为 `skills@1.7.1`。

```powershell
npx --yes skills@1.7.1 add https://github.com/anthropics/skills/tree/683bc88e56f3e09ba94f7055977f3d3aa499f202/skills/frontend-design --skill frontend-design --agent codex --copy --yes
```

安装记录保存在 `skills-lock.json`，包含来源提交和内容 hash。现有 `.gitignore` 的 `.agents/skills/*` 覆盖新技能目录，`build/` 覆盖参考源码、截图、安装器缓存与检查记录。执行时将安装器的 `TEMP`、`TMP` 和 npm cache 指向 `build/site-visual/tool-temp/`；这些设置仅用于该安装进程。技能源码保留其 Apache-2.0 许可证。

## 依赖核对

固定提交的 [package.json](https://github.com/arthelokyo/astrowind/blob/14e1a691f80548dcc36370847b1a02c0d0b12821/package.json) 和 [package-lock.json](https://github.com/arthelokyo/astrowind/blob/14e1a691f80548dcc36370847b1a02c0d0b12821/package-lock.json) 已核对：模板版本 `1.0.0-beta.66`，锁文件格式 3；11 项生产依赖和 29 项开发依赖的声明与锁定版本一致，直接包具有 HTTPS npm registry 地址和 SHA-512 integrity。主要锁定版本为 Astro `7.3.1`、Tailwind CSS `4.3.3`、TypeScript `5.9.3`、Sharp `0.35.4`。

`engines.node` 要求 `>=22.22.3`，本机 Node `v24.19.0` 满足；`.nvmrc` 仅声明主版本 `22`，未来若构建原模板应同时遵守完整的 engines 要求。模板采用 MIT 许可证。参考来源与文件摘要见 [references.lock.json](references.lock.json)。

本阶段借鉴布局、留白、内容层次和交互结构。页面继续使用现有本机字体回退、本地 CSS/JS/SVG 与 Python 构建。模板依赖保持在参考记录中；网站依赖无需变更。若后续移植模板源码，保留对应版权及许可证；完整模板安装、构建和依赖公告审计另行记录。

## 视觉方向

以 Blender 工作现场的三维场景作为主要视觉元素，内容围绕安装包、服务启动和客户端连接展开。采用 AstroWind 清晰的标题层次、充足留白和分区节奏，突出可操作的下载入口。

沿用现有项目色彩：背景 `#10171b`、内容表面 `#172126`、正文 `#f1f4f1`、次级文字 `#a9b8bd`、主要操作 `#ff984f`、连接提示 `#a7d7b1`。系统 sans-serif 用于正文与标题，monospace 用于索引 URL、命令和校验值；正文行宽与中文断行分别检查。内容左对齐，Hero 在桌面并列展示文案与场景，手机按文案、操作、场景顺序排列。

| 页面部分 | 固定版本参考组件 | 改进目标 |
| --- | --- | --- |
| Hero | `src/components/widgets/Hero.astro` | 强化产品标题、简短说明及主次操作层次；呈现项目自有三维场景，并说明其为示意 |
| 功能介绍 | `Features.astro`、`Content.astro` | 使用具体能力组织内容：集成安装、宿主内服务管理、客户端配置；明确上游来源与本项目职责 |
| 对比 | `Comparison.astro` | 保持实际安装方式对比，改善表头、行标题和手机阅读；使用文字说明能力与限制 |
| 下载 | `CallToAction.astro` 的操作层次 | 保留 Blender 版本、通道与平台的选择关系，突出真实发布记录生成的下载入口 |
| 安装步骤 | `Steps.astro`、`QuickStart.astro` | 展示完整顺序：安装 Extension、启动服务、配置客户端、验证连接；编号仅用于操作顺序 |
| FAQ | `FAQs.astro` | 使用原生 `details/summary`，使兼容范围、索引安装和连接问题容易查找；键盘与禁用 JavaScript 均可使用 |

页面文案使用真实功能与验证状态；涉及客户端、平台或性能的陈述须有对应证据。视觉素材与功能说明在中英文页面保持一致。

## 实施顺序

1. 使用已安装的 `frontend-design` 阅读本规格与现有网页，完成 Hero、分区、字体和间距的具体设计。
2. 在 `web/index.html`、`web/site.css` 与必要的双语文案中实施；交互变化按需修改 `web/site.js`。版本信息和下载链接继续由发布记录生成。
3. 运行相关渲染与渠道测试，在 1440px、768px、390px 和 320px 视口检查中英文首页与渠道页。检查键盘焦点、FAQ、通道/语言切换、复制反馈、减少动画设置和禁用 JavaScript 的下载入口。
4. 用改进后的页面生成本地预览与截图，并记录 `Passed`、`Failed`、`Not Run`；人工视觉验收与远端部署单独记录。

## 验收边界

- Hero、功能、对比、步骤、FAQ 层次清晰，手机无页面横向溢出；比较表在必要时可在容器内滚动。
- 中英文、全部真实下载链接及安装入口可用；`index.json` 与 `publication.json` 原始字节保持一致。
- JavaScript 缺席时，下载、正文和 FAQ 仍可使用。减少动画设置得到尊重。
- 页面及工作流改动通过相关本地检查；线上部署须按已授权的发布流程执行。

## 当前状态

| 检查 | 状态 | 证据 |
| --- | --- | --- |
| 单技能审查、项目级安装、来源提交及 Git 忽略 | Passed | `build/site-visual/skill-vetting.md`、`preparation-check.json`；原有 38 项技能锁记录保留 |
| 固定模板来源与 40 项直接依赖核对 | Passed | `build/site-visual/references/manifest.json`、`dependency-check.json`；49 个参考文件有 SHA-256 |
| 演示桌面/手机读取与视觉观察 | Passed | `build/site-visual/demo/observation.json` 及截图 |
| 本规格中的页面改进实施与本地检查 | Passed | [实施任务](issues/01-visual-refresh.md)；`build/visual-refresh/delivery.json` |
| 原模板安装、构建、依赖公告审计 | Not Run | 当前使用范围为视觉参考 |
| 人工视觉验收、远端部署 | Not Run | 按独立验收与发布流程执行 |

页面已完成整体重排：Hero、三项功能、安装方式对比、版本与通道下载、四步安装、独立 FAQ 和资源入口。中文使用“智能体”，英文使用“agent”；桌面和手机顶部导航在滚动时保持可见，锚点跳转为导航栏预留空间，比较表在容器内滚动。现有 JavaScript 内容保持一致，三个修改源文件保留 UTF-8 无 BOM 与 CRLF。

本地检查包含 11 项网页测试、1440/768/390/320px 中英文首页和 preview 渠道页共 16 种组合，以及展开校验详情后的窄屏检查。预览使用压缩包内已校验发布记录；四份 JSON 的原始字节与六个下载 URL 保持一致。复制失败检查在浏览器 API 边界注入权限拒绝，其余复制成功检查使用真实浏览器剪贴板。

术语和固定导航的检查覆盖 1440/1107/874/768/390/320px 中英文页面共 12 种组合：页面不再使用“助手 / assistant”，导航栏在页首、页中和页尾保持可见，直接访问安装锚点和点击四个导航入口时标题均未被遮挡。11 项网页测试已重新运行；证据位于 `build/visual-refresh/browser-comments/report.json`。

安装方式对比以“使用环节 / 官方 Extension + stdio / 本仓库集成版”为三列表头，表头使用独立底色与粗体。对比说明位于表格外，并通过 ARIA 关联表格；新增离线安装一行及优势说明，明确已下载 ZIP 的依赖随包交付、兼容电脑间保存与复制、网络权限和模型服务的适用范围。本地预览返回 `Cache-Control: no-store`。11 项网页测试重新运行 Passed；四个中英文主页与 preview 渠道页面在六种宽度共 24 种组合检查 Passed，见 `build/visual-refresh/comparison-refinements/report.json`。

运行流程与技能说明按[实施任务](issues/02-runtime-and-skill-explanation.md)组织：两套流程图标明 stdio / HTTP 接口、独立服务、进程控制与安装位置；官方安装命令默认折叠且不固定版本。Hero 使用 `web/agent-blender.png` 的本机双向协作示意。官方来源区包含源码仓库与项目介绍链接，资源区专门介绍 Extension 开发 skill、模板优势和七个 GitHub 参考来源。两个发布线的索引均标注适用版本和使用步骤。

图表布局阶段的 11 项网页测试与八种宽度、两种语言、两种渠道共 32 种浏览器组合 Passed，包含用户的 916px 和 700px 视口；禁用 JavaScript 的四个页面及真实剪贴板检查 Passed，见 `build/visual-refresh/aligned-diagrams-page/report.json`。四个原图的真实新标签页打开与放大交互检查 Passed，见同目录的 `interaction-report.json`。生成主图的提示词、来源与项目路径保存在 `build/visual-refresh/runtime-skill/image-generation.json`。

[Archify、导航与工具实施任务](issues/03-archify-runtime-diagrams.md)使用固定提交的 Archify 生成两套中英文原图与 SVG 预览。背景框表达安装区域，节点说明运行进程；请求、结果与控制线独立标注。五个导航入口包含 Extension 开发 Skill。图下列出六个常用 MCP 工具，名称、参数和示例语法在 5.1 与 5.2 的真实上游源码中核对。来源记录保存在 `references.lock.json`，许可随产物交付。网站构建继续复制本地资产，项目依赖保持一致。

[图表可读性任务](issues/04-compact-diagrams.md)增大节点、安装位置与接口文字，并减少卡片间距；四张原图和 SVG 同步更新。固定 Archify 的局部可读性补丁随源码保存，文字测量边界与字号同步调整，安装位置在默认原图中可见。

[布局与文字对齐任务](issues/05-aligned-diagrams.md)统一四图的 1000×720 画布与组件坐标：客户端配置左上、智能体左中、Blender 宿主左下；右侧依次为依赖、服务和桥接。黄色安装区标题使用 16–18px 字号，卡片三行内容整体垂直居中，流程线文字没有底色，HTTP 请求与进程控制线路分别绘制。四份候选的 validate、deliver、check、browser-check 均 Passed。916px 实际浏览器测量显示安装区标题最小 14.904px，三行内容中心最大偏差 1.516 SVG 单位；图中关系、来源和安装分组与基线一致。测量和截图记录在 `build/visual-refresh/aligned-diagrams-page/layout-report.json`，四图产物与校验在 `build/visual-refresh/aligned-diagrams/finalize-report.json`。人工视觉验收、真实 Blender 工具执行和远端部署仍为 Not Run。

[工具折叠任务](issues/06-collapsed-mcp-tools.md)将六个工具改为一行一个的原生 details/summary，默认关闭，展开后显示原有工具名称、用途、参数和提示语。各条目独立操作，支持鼠标、Enter、Space 和禁用 JavaScript。当前 11 项网页测试及 1440/914/390/320px × 两种语言 × 两种渠道共 16 组操作检查 Passed，四个禁用 JavaScript 页面 Passed；工具参数与已核对的上游注册内容一致，页面无横向溢出。实际页面截图由智能体检查，证据见 `build/visual-refresh/collapsed-tools/report.json`。

[安装背景框顶部任务](issues/07-aligned-installation-frame.md)让 showcase 背景框顶部跟随标题栏，标题栏与框顶部的间距为 4 SVG 单位，左右空间独立保留。四份图表规格保持原始字节，Archify 的四个 gate 均 Passed；中英文 HTTP 在 1057px 的实际预览与默认原图检查 Passed，916px 四图布局检查 Passed。证据为 `build/visual-refresh/frame-top/report.json`，补丁来源及 SHA-256 同步到 `references.lock.json`。
