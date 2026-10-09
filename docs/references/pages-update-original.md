# Blender MCP 发布页面改版与实现复审

日期：2026-10-08。仓库：<https://github.com/psiQAQ/blender_mcp-setup-guide>。

## 交付状态

网页源码与发布工作流已经实现，并在本地提交为 `0739eb0b2fe5060de5fcf7b8da4d63c0a562909f`，基于 `main@7f281466d9ef01a957f872906c0bc468198a0635`。本包提供可应用补丁、真实发布数据生成的静态预览、验证记录与复审建议。

**远端尚未改动。** GitHub 连接创建分支时返回 `403: Resource not accessible by integration`，因此本轮没有成功创建远端分支、PR、CI 运行或线上部署。这是连接的实际写权限限制；没有尝试其他凭据或浏览器写入。

## 文件内容

| 文件 | 用途 |
| --- | --- |
| `blender-mcp-pages.patch` | 完整 Git format-patch，含 13 个文件的源码与文档改动 |
| `site-preview/index.html` | 中文首页；解压整个目录后在自己的浏览器打开 |
| `site-preview/en/index.html` | 英文首页 |
| `site-preview/blender-5.2/preview/index.html` | 默认选择 5.2 preview 的中文页面 |
| `site-preview/blender-5.2/preview/en/index.html` | 对应英文页面 |
| `site-preview/assets/` | 原生 CSS、JavaScript、自绘 SVG 立方体场景和标记 |
| `verification.json` | 基线/本地提交、测试状态、来源产物与保留 JSON 的 SHA-256 |
| `unit-tests.log` | 本轮 46 项 Python 测试的完整输出 |

预览页面使用真实发布下载链接。点击安装包按钮会访问 GitHub Release 资产。预览不是 Blender 插件安装包，也不会在本机启动 MCP。浏览器从磁盘打开时可能限制自动复制；复制失败会选中索引供手动复制。

## 应用改动

在仓库的干净工作目录中，从当前 main 创建分支；将补丁路径替换为实际解压位置：

```bash
git switch main
git pull --ff-only
git switch -c feat/release-pages-design
git am /path/to/blender-mcp-pages.patch
python -B scripts/run_checks.py
git push -u origin feat/release-pages-design
```

如果 main 已在基线之后修改同一批文件，需要正常处理补丁冲突，不能直接覆盖现有工作。补丁已在 `7f281466` 的干净 checkout 上通过 `git apply --check`。通过本仓库常规审查合并 main 后，`Refresh release website` 会自动运行；亦可在 Actions 手动运行它。

网站刷新会重新核对当前线上索引和 ZIP，然后部署。不能把本包里的旧时间点预览目录直接上传覆盖未来更新后的站点。

## 本次网页改动

### 内容与外观

页面使用深色三维工作空间的视觉、橙色下载入口和独立立方体场景示意，包含：

1. 插件由来：Blender Lab 官方 MCP 提供核心工具与桥接，本仓库维护社区集成发行版。
2. 与本仓库保留的官方 Extension + stdio 指南对照：安装内容、运行环境、进程启动与客户端连接方式。
3. 按 Blender 版本/发布通道选择，再展示 Windows x64、Linux x64、macOS Apple Silicon 三个安装包。
4. 每包大小、真实下载链接、SHA-256 与来源提交；构建证据明确区别于安装 ZIP。
5. 安装三步、客户端配置复制说明、首个只读场景验证提示词、FAQ、Skills 与开发文档入口。
6. 中英文页面、响应式 CSS、键盘焦点、跳过导航、状态播报、减少动态效果设置。

JavaScript 只增强通道切换、语言/阅读位置同步及复制索引。关闭 JavaScript 后，各通道和下载链接仍在 HTML 中。没有外部字体、广告/分析服务或浏览器端 GitHub API 请求。

### 发布流程

`scripts/pages_render.py` 从已经验证的发布记录渲染；`web/` 保存模板与资源；`scripts/pages_site.py` 保留安装元数据，重新生成外观。

根目录仍保留 Blender 5.1 stable 的 `index.json`。5.2 preview 的索引仍在 `blender-5.2/preview/index.json`。历史 5.1 记录缺失的通道与兼容字段只使用展示默认值，不修改原始 JSON。

新增 `pages.yml` 支持 main 的网页相关路径推送、手动刷新及本仓库成功发布后的 `workflow_run`。构建使用可信 main，不执行触发发布分支的代码，不消费其 artifact。网站与包发布共用 `extension-release` 并发组。刷新前、部署前与部署后检查元数据与下载，不创建新的 Extension Release。

旧发布分支可能先生成旧页面，再由 main 的刷新工作流恢复新外观，期间存在短暂窗口。如果旧分支的 Pages 部署成功但后续公开安装测试失败，成功事件不会触发；应检查故障后按需手动刷新。长期可将网站生成器回移维护分支。

## 验证范围

| 项目 | 结果 |
| --- | --- |
| 现有测试基线 | 37 项通过 |
| 改动后 Python 测试 | 46 项通过，0 failure / 0 error |
| JavaScript 语法 | `node --check web/site.js` 通过 |
| Git whitespace 检查 | `git diff --check` 通过 |
| 补丁可应用性 | 原始提交上 `git apply --check` 通过 |
| 实际发布数据 | 最新成功发布的 verified-extension-index artifact，ID 11532708065 |
| 生成页面 | 4 个 HTML 页面、4 个本地资源 |
| 索引保留 | 两通道的 4 个 JSON 文件 SHA-256 均保持一致 |
| 下载映射 | 两条通道、每条 3 个平台，大小/hash/URL 与 Release 元数据一致 |
| 浏览器视觉与手机截图 | 未完成，不能视作通过 |
| 新改动远端 CI / 部署 | 未运行，GitHub 写权限不足 |

真实数据来源为 [发布工作流 37738381105](https://github.com/psiQAQ/blender_mcp-setup-guide/actions/runs/37738381105)。本地未重新下载并执行全部六个安装包。原有已发布包的三平台结论来自成功的原始发布工作流，不能冒充本轮重新执行。

当前环境无法访问线上 Pages，自带浏览器也不允许打开本地 file URL；未绕过限制。页面视觉尚需在具备访问条件的真实浏览器中完成最终验收。

## 当前实现复审

审查针对上述基线。当前独立 Python 服务、私有依赖、双层凭据、Host/Origin 检查、固定官方来源、三平台构建、最终 ZIP 与报告绑定、发布后真实安装验证都已经落实。以下是仍存在的具体改进点；这些运行时问题没有混入本次网页补丁。

### P1：延迟工具异常可能让 Blender Timer 消失

[`src/blender_mcp_integration/__init__.py`](https://github.com/psiQAQ/blender_mcp-setup-guide/blob/7f281466d9ef01a957f872906c0bc468198a0635/src/blender_mcp_integration/__init__.py) 的 `_poll_service()` 只捕获 `ServiceError`、`OSError`。如果 deferred `check_is_finished()` 返回含 set 等无法直接 JSON 序列化的值，真实上游 bridge 的序列化错误会逃出 Timer 回调。

针对性复现输入：

```python
def check_is_finished():
    return {"values": {1, 2}}
```

本轮使用锁定上游真实 bridge、真实 socket 与当前回调逻辑，替代 bpy 接口和服务状态对象，观察到 `TypeError`、状态仍 Running、未执行清理、bridge 仍监听。没有在真实 Blender 中运行该复现。

建议在 Timer 最外层捕获普通 Exception，记录错误并进入可恢复状态；同时修正 deferred 序列化，将无效结果返回为工具失败。回归测试应在异常请求后继续发一个正常请求，确认没有挂死整个服务。

### P1：后台 CLI 工具未固定当前 Blender 可执行文件

[`runtime.py`](https://github.com/psiQAQ/blender_mcp-setup-guide/blob/7f281466d9ef01a957f872906c0bc468198a0635/src/blender_mcp_integration/runtime.py) 的 `Service.start()` 没有传递 `BLENDER_PATH`。锁定官方源码中的 CLI helper 仍回退到 PATH 里的 `blender`。

这影响 `execute_blender_code_for_cli` 和 5 个 `get_blendfile_summary_*_for_cli` 工具。清空 PATH 调用真实 helper 能复现 executable not found；多版本 PATH 也可能命中错误 Blender。当前集成测试检查工具数量并调用在线场景工具，未实际调用这些 CLI 工具。

建议将 `bpy.app.binary_path` 明确传给子进程的 `BLENDER_PATH`，在移除外部 PATH 依赖的环境里执行一次真实 CLI 工具，并核对返回版本。

### P2：秘密文件未独立保证用户专属权限

`runtime.py` 创建目录与 token/session 文件，[`preferences.py`](https://github.com/psiQAQ/blender_mcp-setup-guide/blob/7f281466d9ef01a957f872906c0bc468198a0635/src/blender_mcp_integration/preferences.py) 导出 `client-config.txt`，均继承默认权限。真实文件操作在 umask 022 下得到目录 0755、token/session 文件 0644；session 内含两层凭据。

如果祖先目录允许其他本机用户遍历，这些凭据可以被读取。用户主目录已经是 0700 时会有上层保护，因此不能描述成远程无鉴权漏洞。

建议 Unix 目录 0700、秘密文件 0600，并迁移旧文件权限；首次 token 创建采用 exclusive/atomic 方式。Windows 则验证用户目录 ACL，不能以 chmod 替代 ACL。导出的客户端配置遵守同样的秘密文件规则。

### P2：在途 CLI 子进程未纳入 Stop 与父进程退出清理

`Service.stop()` 只 terminate/kill 直接 sidecar；官方 CLI helper 的后台进程未登记为受控进程树。用真实 Linux 进程树和测试子进程替代后台 Blender，观察到 sidecar 已退出、状态 Stopped，但其后代仍存活；测试进程随后已清理。

建议 Unix 受控进程组、Windows Job Object 或明确子进程登记方案，并增加“CLI 任务进行中 Stop”和“任务进行中宿主退出”的真实测试。现有空闲服务的 parent-exit 测试不能覆盖这种状态。

### P2：公开安装失败报告写入错误文件名

[`scripts/test_repository.py`](https://github.com/psiQAQ/blender_mcp-setup-guide/blob/7f281466d9ef01a957f872906c0bc468198a0635/scripts/test_repository.py) 的 public-index 成功路径写 `published-tests.json`，外层却始终使用 `run_check("repository", main)`。失败时报告落到 `repository-tests.json`，而发布工作流上传的是 `published-tests.json`。

流程仍会失败，但结构化失败报告丢失，本地重跑还可能保留旧 Passed 文件。建议先解析模式，统一成功与失败报告名称，并测试公开模式失败会覆盖旧 Passed。

### P2：升级夹具对首次 preview 的 patch=0 会失败

[`scripts/test_upgrade.py`](https://github.com/psiQAQ/blender_mcp-setup-guide/blob/7f281466d9ef01a957f872906c0bc468198a0635/scripts/test_upgrade.py) 首次 preview 通过 patch 减 1 构造旧版本。对 `1.1.0-dev.1` 的内存包复现了明确 ValueError；`2.0.0-dev.1` 同样无可减 patch。

现在每条通道都有真实首发包，建议下一版升级测试锁定上一已发布包的 URL、版本与 SHA-256。没有历史包的第一版使用明确测试旧版本，不对官方 patch 做算术。当前同实现改版本号的夹具仍可检验安装/替换机制，但不能代表真实旧代码、依赖、设置迁移；原文档已披露这一限制。

### P2：发布后公开安装报告应长期归档

当前 Release evidence ZIP 长期保存发布前证据。公开索引安装发生在之后，仅保存为 Actions 的 publication-* artifact；本轮 API 返回其到期时间为 2027-01-06T06:38:46Z。

建议生成独立不可变发布后回执，绑定版本、通道、三个包 hash、run ID 与三份 published-tests.json。若放到同一 Release 增加附件，须同时调整 `publish_assets()` 对附件集合的约束，否则额外回执会阻止后续幂等重试。不要重写历史 evidence ZIP。

### P3：默认分支的上游巡检缺少稳定基线 commit

[`scripts/upstream_sync.py`](https://github.com/psiQAQ/blender_mcp-setup-guide/blob/7f281466d9ef01a957f872906c0bc468198a0635/scripts/upstream_sync.py) 的移动 tag 检查比较 `pinned["tag"]`。当前 main 为 preview，该字段为 null；`stable_baseline_tag` 有值却没有对应 commit。

建议同时锁定 `stable_baseline_commit`，分别判断新稳定版本、main 更新和已有 tag 移动。稳定发布自身仍有 tag/commit 检查，因此这是巡检缺口，不是错误包已被放行的证据。

## 可选模板和技能

本次保留原生 HTML/CSS/Python 流程，以降低发布链变动。以下可作为后续选择：

| 选择 | 更适合什么 | 本仓库采用成本 |
| --- | --- | --- |
| [Astro Starlight](https://github.com/withastro/starlight) / [演示与文档](https://starlight.astro.build/) | 产品首页 + 大量双语安装/开发文档；Markdown/MDX、搜索、国际化、splash 页面 | 增加 Astro/Node 构建；长期文档化首选 |
| [AstroWind](https://github.com/arthelokyo/astrowind) / [演示](https://astrowind.vercel.app/) | Hero、特性、对比、步骤、FAQ 等产品宣传页 | 增加 Astro/Tailwind；当前更适合参考版式与组件 |
| [Just the Docs Template](https://github.com/just-the-docs/just-the-docs-template) / [演示](https://just-the-docs.github.io/just-the-docs/) | 文档导航、搜索与 Markdown 维护优先 | 增加 Jekyll/Ruby；视觉首页需另做 |

模板均为 MIT；栈和入口已于本轮查阅维护者资料。AstroWind 原 onwidget 地址目前指向上表仓库，采用时应固定实际提交并重新核对依赖与许可。

适合的技能：[Anthropic frontend-design](https://github.com/anthropics/skills/tree/main/skills/frontend-design) 用于视觉方向、字体层级与重设计；[Vercel web-design-guidelines](https://github.com/vercel-labs/agent-skills/tree/main/skills/web-design-guidelines) 用于语义、键盘、响应式、图片与动画规范审查。这些是推荐选项，本轮没有将其安装进你的仓库，也没有迁移托管服务。

官方来源与项目内容以原始许可证为准；本包附带仓库 GPL-3.0-or-later LICENSE。
