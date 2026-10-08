# 构建、验证与发布

在仓库根目录操作。集成包要求原生 Windows x64、Linux x64 或 macOS Apple Silicon，以及对应发布线的 Blender / CPython 3.13。`release/blender-5.1` 固定官方 v1.0.3，范围为 5.1.0 ≤ Blender < 5.2.0；`main` 与 `release/blender-5.2` 固定官方 main 快照，范围为 5.2.0 ≤ Blender < 5.3.0。运行时不安装依赖；构建阶段按版本与 SHA-256 下载 wheels，仅安装至被忽略的 `build/` 打包目录。通用开发模板支持 Blender 4.2+。

## 原生构建

PowerShell 示例：

```powershell
$blender = 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe'
$blenderPython = 'C:\Program Files\Blender Foundation\Blender 5.2\5.2\python\bin\python.exe'
git submodule update --init submodules/blender_mcp
& $blenderPython -B scripts/build_integration.py --blender $blender --platform windows-x64
```

Linux/macOS 使用 Bash，将路径替换为本机 Blender 及其配套 Python：

```bash
blender='/path/to/blender'
blender_python='/path/to/blender/python/bin/python3.13'
"$blender_python" -B scripts/build_integration.py --blender "$blender"
```

`--platform` 可选；默认检测本机。指定的平台与解释器系统、架构、CPython 3.13 不一致时拒绝构建。平台配置、官方 Blender URL/hash 和依赖锁路径来自 `packaging/platforms.json`。Windows 为 40 个 wheels，Linux/macOS 为 39 个；pywin32 只用于 Windows。5.1 来源为 v1.0.3 / `2cea8d566dde07fbac28a61d698909d69724e853`；5.2 来源为 main / `dbbf836ad4b1025f14a2b3b504c43903f39e0b04`，上游服务器版本为 1.0.2。构建验证已提交的子模块指针、干净源码与原远端，不自动拉取浮动 main。

当前 5.2 候选构建输出为 `build/latest/dist/blender_mcp_integration-1.0.2-dev.2+integration.1-<platform>.zip`、对应 `.sha256` 与 `provenance-<platform>.json`。版本来自 `packaging/upstream.json`。来源包含渠道、main/tag 引用、预发布序号、子模块指针、仓库提交和 dirty 状态、依赖版本、wheel hash 与桥接补丁 hash。旧稳定记录缺少渠道字段时按 5.1 stable 解析。ZIP 通过官方 `extension validate`，保留依赖数据与许可证；发布仍要求干净提交。

已核验的官方源码和 wheel 缓存可通过 `--upstream <目录> --wheelhouse <目录> --offline` 复用。构建不得从已安装插件目录复制依赖。更新依赖时，三个平台同步核对版本及独立 wheel hash。

## 本地验证与 CI

```powershell
& $blenderPython -B scripts/run_checks.py
& $blenderPython -B scripts/test_templates.py --blender $blender
$package = 'build/latest/dist/blender_mcp_integration-1.0.2-dev.2+integration.1-windows-x64.zip'
& $blenderPython -B scripts/test_integration.py --blender $blender --package $package
& $blenderPython -B scripts/test_upgrade.py --blender $blender --package $package
& $blenderPython -B scripts/test_gui.py --blender $blender --package $package
```

测试使用独立 `BLENDER_USER_RESOURCES`，保留用户现有 Blender 配置。使用真实 MCP SDK、最终 ZIP 和 GUI 事件循环；场景操作恢复对象数。CLI 检查清空 PATH 并设置错误外部 `BLENDER_PATH`，验证当前宿主路径覆盖；在途 CLI 分别覆盖 Stop 和宿主退出。GUI 检查非法 deferred 结果返回错误后正常请求仍成功。

升级检查默认从 `packaging/upgrade-baselines.json` 选择同一 Blender 通道和平台的上一已发布包，核验版本、大小、SHA-256，再经真实 HTTP 索引安装与升级，验证旧代码、偏好和凭据。已有本地旧包时使用 `--previous-package <路径>`，仍必须匹配锁定值。新通道没有历史包时显式使用 `--fixture`，其 `0.0.0` 测试版本只验证安装替换机制，不能代表旧代码迁移。三平台集合索引检查保留机制夹具，与单平台真实升级报告分别记录。

CI 使用 windows-2022、ubuntu-24.04、macos-15 ARM64 原生 runner；5.2 线 hash 固定 Blender 5.2.2，并在 5.2.0 上验证相同 ZIP 的安装、MCP 与生命周期。5.1 维护线继续使用 5.1.2/5.1.0。Linux GUI 使用 Xvfb/Mesa、Openbox 和 ImageMagick X11 桌面取景；Windows GUI 使用 [mesa-dist-win](https://github.com/pal1000/mesa-dist-win) 的 hash 固定 26.2.4 llvmpipe，仅部署到 CI Blender。GUI 报告保存实际 renderer，截图须包含可见界面。三个产物汇总后，分别从统一索引选择平台、实际安装与升级。全部通过才产生 `validated-<platform>`。

报告绑定平台及 ZIP SHA-256。失败检查写入 Failed，不复用旧 Passed 报告。人工 GUI 操作及三个实际 agent 的验收与自动化测试分开记录。

`packaging/` 的 JSON/TXT 锁文件统一使用 LF，确保三个系统计算相同的来源 hash。CI 最后在 Windows 汇总核验三个最终 ZIP、七类报告及干净提交，使用与发布相同的完整资产检查。

独立测试客户端使用最终 ZIP 中已锁定的私有 certifi 根证书，为 Blender 配套 Python 设置 `SSL_CERT_FILE`；三平台均实际验证 GitHub HTTPS 下载站点。公开索引安装测试保留 TLS 证书校验。

## 渠道发布

将 Pages 来源设置为 GitHub Actions。为完全通过 CI 的同一干净提交创建版本标签，手动触发 `release.yml`，指定对应分支、成功 CI run ID、标签和 `stable` 或 `preview` 渠道。首次 5.2 预发布标签为 `v1.0.2-dev.1+integration.1`。候选来源选择和发布前分别核对官方远端 main HEAD；若变化，重新固定子模块并完成验收。`main` 快照禁止发布为 stable；preview 显式设置 Pre-release 与 `latest=false`。

工作流复用三个已验证产物，核对来源、标签、完整平台集合和所有报告；先上传 draft Release 并逐资产鉴权回读大小/hash，再验证官方 Extensions 索引。Pages 合成完整站点并回读保留渠道的索引与 ZIP；全部通过后公开相应渠道的 Release，回读公开下载并部署 Pages。三个原生 runner 随后从公开索引实际安装并调用 MCP，并再次核对保留渠道。

Release 首次公开附件为三个平台安装 ZIP、三个 `.sha256` 和一个 `blender_mcp_integration-<version>-evidence.zip`。证据包按原始字节保存三个平台的来源记录及七类发布前报告；使用固定文件顺序、时间戳和权限生成，支持字节一致的恢复上传。三平台公开安装验证全部通过后，`archive-publication` 增加 `blender_mcp_integration-<version>-publication-<run-id>.zip`，保存不可变 publication 元数据、三份原始 `published-tests.json` 与绑定版本、通道、提交、run ID 和包/report hash 的回执。重复上传先回读，不覆盖同名内容。安装与更新仅使用平台安装 ZIP。

相同版本资产不可变；缺少平台、渠道错配、错误 ABI、错误或陈旧报告、版本回退或内容替换直接失败。同源 draft 可恢复补传缺失资产；Pages 部署可单独重试。后续 preview 内容变化递增 `preview_revision`，版本排序依次比较源码版本、正式/预发布、`dev.N` 与集成修订号。

下载入口为 [GitHub Releases](https://github.com/psiQAQ/blender_mcp-setup-guide/releases)。[根索引](https://notes.psiqaq.cn/blender_mcp-setup-guide/index.json)按 Blender 版本与平台自动匹配，稳定版优先；[5.1 stable 索引](https://notes.psiqaq.cn/blender_mcp-setup-guide/blender-5.1/stable/index.json)和[5.2 preview 索引](https://notes.psiqaq.cn/blender_mcp-setup-guide/blender-5.2/preview/index.json)独立发布。未来 5.2 stable 使用 `/blender-5.2/stable/index.json`。联网安装需启用 Allow Online Access。

## 模板与上游维护

`scripts/scaffold_extension.py <extension_id> <output_directory>` 生成无第三方依赖的通用模板。标识按 Extension ID 替换，拒绝覆盖现有目录；模板使用显式注册、失败回滚和逆序卸载。用法见技能中的 template-guide.md。

`scripts/upstream_sync.py` 同时检查官方 main、最新稳定 Release 与已锁定的 `stable_baseline_tag` / `stable_baseline_commit`；即使出现新稳定标签，也独立验证旧基线标签未移动。输出审查记录，不修改源码或发布。新的官方稳定 tag 发布后，审查其 5.2 兼容性、固定提交并重新完成三平台验收，随后人工触发 stable 发布工作流。
