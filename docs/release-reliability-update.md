# 两条发布线可靠性更新

2026-10-10，集成修复已发布到 Blender 5.1 stable 与 5.2 preview，旧 Release、标签及安装资产保留。两个已确认上游问题继续作为已知限制；本机 5.2 的旧包安装仍触发 WinError 5，因此该机的更新发现验收未完成。

## 发布与网站

| 发布线 | 新 Release | 干净构建提交 | 成功三平台 CI | 公开安装与回执 |
| --- | --- | --- | --- | --- |
| 5.1 stable | [1.0.3+integration.2](https://github.com/psiQAQ/blender_mcp-setup-guide/releases/tag/v1.0.3%2Bintegration.2) | `bb3319d6ad8bb58be3fcc10009c8578be5f82209` | [37960368325](https://github.com/psiQAQ/blender_mcp-setup-guide/actions/runs/37960368325) | [37961815677](https://github.com/psiQAQ/blender_mcp-setup-guide/actions/runs/37961815677) Passed |
| 5.2 preview | [1.0.2-dev.2+integration.1](https://github.com/psiQAQ/blender_mcp-setup-guide/releases/tag/v1.0.2-dev.2%2Bintegration.1) | `d71ee1ea43b6720212f161fad4c9ac468fd66e92` | [37960367844](https://github.com/psiQAQ/blender_mcp-setup-guide/actions/runs/37960367844) | [37969368609](https://github.com/psiQAQ/blender_mcp-setup-guide/actions/runs/37969368609) Passed，保留首次失败证据 |

每条 Release 的 evidence ZIP 保存发布前七类报告；独立 publication ZIP 保存三个平台的公开安装报告及不可变元数据。正式包均为 CI 重建结果，`integration_dirty: false`。后续维护提交不改写这些包或标签。

- [中文网站](https://notes.psiqaq.cn/blender_mcp-setup-guide/)、[English](https://notes.psiqaq.cn/blender_mcp-setup-guide/en/)。
- [统一索引](https://notes.psiqaq.cn/blender_mcp-setup-guide/index.json)：六个平台条目，按 Blender 版本和平台匹配，同一发布线优先稳定版。
- [5.1 stable 独立索引](https://notes.psiqaq.cn/blender_mcp-setup-guide/blender-5.1/stable/index.json)、[5.2 preview 独立索引](https://notes.psiqaq.cn/blender_mcp-setup-guide/blender-5.2/preview/index.json)：各三个条目。
- 各通道 `publication.json` 与索引同步；根 `publication.json` 镜像 5.1 stable。

网站的版本、URL、大小及 SHA-256 来自验证后的发布记录。两条线都注明缩略图尺寸和 API 类成员解析限制。

## 验证结果

| 检查 | 状态 | 证据与范围 |
| --- | --- | --- |
| 维护代码单元测试 | Passed | 94 项；正式包的三平台 CI 各运行当时的 81 项，分别绑定实际包 |
| 六个正式包的必需发布检查 | Passed | 官方格式、两个模板、真实 MCP/六个 CLI、鉴权/生命周期、GUI 自动化、最低版本、集合索引安装；七类报告保存在 `build/latest/validated/` |
| 六个真实旧发布包升级 | Passed | CI 通过真实 HTTPS 大小/hash 校验，升级后配置与凭据保留 |
| 六个公开包安装与真实 MCP | Passed | 两条发布流程均完成三平台检查，并上传不可变回执 |
| 三个索引及三个发布记录 | Passed | 普通 HTTPS URL 的完整字节与已验证网站制品一致；统一索引与通道记录一致 |
| 六个公开 ZIP 回读 | Passed | 下载大小、完整 SHA-256、CI ZIP 和所有包绑定报告一致；`build/latest/public-readback-tests.json` |
| 本机 Blender 5.1.1 更新发现 | Passed | 安装真实 `1.0.3+integration.1` 基线后同步统一索引，官方统计一个更新，选择 `1.0.3+integration.2` |
| 本机 Blender 5.2.2 同步与选包 | Passed | 只读同步与官方筛选选择 `1.0.2-dev.2+integration.1`；`index-sync-5.2-selection-tests.json` |
| 本机 Blender 5.2.2 旧基线安装 | Failed | `1.0.2-dev.1+integration.1` 安装目录重命名 WinError 5；`index-sync-5.2-tests.json` 及原始日志保留 |
| 本机 Blender 5.2.2 更新发现 | Not Run | 前置旧基线安装失败后停止；没有重复安装或实施缓解 |
| 双语公开网页 | Passed | 1270px / 390px：切换、下载/hash、复制、固定导航、无溢出；禁用 JavaScript 仍有六个下载入口；`public-browser-tests.json` |
| 人工 GUI、三个实际 agent 验收 | Not Run | 自动化结果不代表用户人工验收 |
| WinError 5 根因处理、历史窗口黑图排查 | Not Run | 按约定暂缓；保留历史证据和最新失败，不修改系统 Blender 或新增管理员跟踪 |

一次浏览器独立 HTTP 请求连接重置、两次本机 Python HTTPS 握手失败以及测试入口的导入路径错误均保留了原 Failed 报告。最终元数据由浏览器真实 HTTPS 导航取得，包由 HTTPS 完整下载校验；没有关闭 TLS 校验或用示例数据替代公开响应。

## 上游复测与待发布 issue

使用未修改的官方 `mcp` Extension、独立 uv 外部工具环境与真实 stdio 客户端，每版本三个隔离 GUI 会话。5.1 固定 v1.0.3 / `2cea8d566dde07fbac28a61d698909d69724e853`，5.2 固定 `dbbf836ad4b1025f14a2b3b504c43903f39e0b04`。

| 问题 | 5.1 | 5.2 | 交付 |
| --- | --- | --- | --- |
| 缩略图使用原始分辨率 | Failed 8/9 | Failed 7/9 | [英文标题与正文](upstream-issues/thumbnail-deferred-render.md) |
| `bpy.types.Object.location` 无法解析 | Failed 3/3 | Failed 3/3 | [英文标题与正文](upstream-issues/api-class-member-resolution.md) |

场景读取、正常操作符查询和重复类名前缀查询对照均 Passed。全部 PNG 均检查实际尺寸、像素内容和设置恢复。脱敏证据位于 `docs/upstream-issues/evidence/`。

两份 issue 未发布，交由用户注册账号后自行提交。固定 Git 树没有仓库级模板；网页创建表单不可读，因此文档明确服务器模板未核实，并提供 Environment、Reproduction、Expected、Actual、Evidence 结构。

## main 的功能与维护提交

| 提交 | 内容 |
| --- | --- |
| `1153950` | 常规 MCP 期限、真实 CLI 夹具、原生安装失败和报告维护 |
| `a4f801a` | 干净官方分体安装复测与两个本地 issue 文档 |
| `aa300d1` | 两条发布线说明与双语已知限制 |
| `bb448c8` | 原生仓库升级检查的仓库选择夹具 |
| `0fde39d` | 包绑定的前置失败报告与官方更新发现入口 |
| `d71ee1e` | 草稿认证校验与公开发布后回读的边界 |
| `1cd1138` | 草稿 API 可见性等待与普通 URL 元数据就绪检查 |
| `950f0cb` | 从新提交恢复已验证的网站制品，限定安装前元数据失败 |
| `f170d57` | 统一索引原生错误捕获、公开浏览器元数据与界面验证 |

维护分支同步公共修复、测试和网站逻辑，同时保留各自固定上游、兼容范围和平台配置。发布标签继续指向上表的已验证构建提交。

## 本地成果与缓存

最新正式成果位于 `build/latest/validated/blender-5.1/` 与 `build/latest/validated/blender-5.2/`；网站位于 `build/latest/site/`，失败证据位于 `build/latest/evidence/`。当前输入缓存与暂缓诊断的压缩 ETL 保留。dirty 候选和被替换的 CI 成果先记录大小/SHA-256，再清理；旧候选报告的来源与失效状态保留。

清理清单和精确字节统计位于 `build/latest/maintenance/`：`retired-dirty-candidates.json`、`ci-artifacts-5.1.json`、`ci-artifacts-5.2.json` 及 `release-delivery-cleanup.json`。临时运行环境按 `docs/agents/build-cache.md` 清理。未验证的 `.vscode/` 设置保持未提交。

最终清理时实测 build 从 1,463,483,105 降至 1,452,745,044 字节，`.working` 从 10,974,150 字节归零；1004 个保留文件的 SHA-256 在清理前后一致，没有占用或权限残留。此外，本轮先前已核验并淘汰 dirty 候选 49,116,620 字节和被替换 CI 成果 119,694,409 字节。保留的暂缓诊断压缩 ETL 为 965,364,407 字节，属于必要证据。
