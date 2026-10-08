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

5.2 构建输出为 `build/dist/blender_mcp_integration-1.0.2-dev.1+integration.1-<platform>.zip`、对应 `.sha256` 与 `provenance-<platform>.json`。来源包含渠道、main/tag 引用、预发布序号、子模块指针、干净仓库提交、依赖版本、wheel hash 和两处桥接补丁 hash。旧稳定记录缺少渠道字段时按 5.1 stable 解析。ZIP 通过官方 `extension validate`，保留依赖数据与许可证。

已核验的官方源码和 wheel 缓存可通过 `--upstream <目录> --wheelhouse <目录> --offline` 复用。构建不得从已安装插件目录复制依赖。更新依赖时，三个平台同步核对版本及独立 wheel hash。

## 本地验证与 CI

```powershell
& $blenderPython -B scripts/run_checks.py
& $blenderPython -B scripts/test_templates.py --blender $blender
$package = 'build/dist/blender_mcp_integration-1.0.2-dev.1+integration.1-windows-x64.zip'
& $blenderPython -B scripts/test_integration.py --blender $blender --package $package
& $blenderPython -B scripts/test_upgrade.py --blender $blender --package $package
& $blenderPython -B scripts/test_gui.py --blender $blender --package $package
```

测试使用独立 `BLENDER_USER_RESOURCES`，保留用户现有 Blender 配置。使用真实 MCP SDK、最终 ZIP 和 GUI 事件循环；场景操作恢复对象数。升级检查从 HTTP 索引安装前一版本夹具，再升级至实际候选，验证偏好与凭据保留。preview 夹具优先采用前一 `dev.N`；首次 preview 使用前一源码 patch 版本的同实现夹具。

CI 使用 windows-2022、ubuntu-24.04、macos-15 ARM64 原生 runner；5.2 线 hash 固定 Blender 5.2.2，并在 5.2.0 上验证相同 ZIP 的安装、MCP 与生命周期。5.1 维护线继续使用 5.1.2/5.1.0。Linux GUI 使用 Xvfb/Mesa、Openbox 和 ImageMagick X11 桌面取景；Windows GUI 使用 [mesa-dist-win](https://github.com/pal1000/mesa-dist-win) 的 hash 固定 26.2.4 llvmpipe，仅部署到 CI Blender。GUI 报告保存实际 renderer，截图须包含可见界面。三个产物汇总后，分别从统一索引选择平台、实际安装与升级。全部通过才产生 `validated-<platform>`。

报告绑定平台及 ZIP SHA-256。失败检查写入 Failed，不复用旧 Passed 报告。人工 GUI 操作及三个实际 agent 的验收与自动化测试分开记录。

`packaging/` 的 JSON/TXT 锁文件统一使用 LF，确保三个系统计算相同的来源 hash。CI 最后在 Windows 汇总核验三个最终 ZIP、七类报告及干净提交，使用与发布相同的完整资产检查。

独立测试客户端使用最终 ZIP 中已锁定的私有 certifi 根证书，为 Blender 配套 Python 设置 `SSL_CERT_FILE`；三平台均实际验证 GitHub HTTPS 下载站点。公开索引安装测试保留 TLS 证书校验。

## 渠道发布

将 Pages 来源设置为 GitHub Actions。为完全通过 CI 的同一干净提交创建版本标签，手动触发 `release.yml`，指定对应分支、成功 CI run ID、标签和 `stable` 或 `preview` 渠道。首次 5.2 预发布标签为 `v1.0.2-dev.1+integration.1`。候选来源选择和发布前分别核对官方远端 main HEAD；若变化，重新固定子模块并完成验收。`main` 快照禁止发布为 stable；preview 显式设置 Pre-release 与 `latest=false`。

工作流复用三个已验证产物，核对来源、标签、完整平台集合和所有报告；先上传 draft Release 并逐资产鉴权回读大小/hash，再验证官方 Extensions 索引。Pages 合成完整站点并回读保留渠道的索引与 ZIP；全部通过后公开相应渠道的 Release，回读公开下载并部署 Pages。三个原生 runner 随后从公开索引实际安装并调用 MCP，并再次核对保留渠道。

Release 下载附件为三个平台安装 ZIP、三个 `.sha256` 和一个 `blender_mcp_integration-<version>-evidence.zip`。证据包按原始字节保存三个平台的来源记录及七类验证报告；使用固定文件顺序、时间戳和权限生成，支持字节一致的恢复上传。安装与更新仅使用平台安装 ZIP，证据包供审计，不作为 Blender 扩展安装。

相同版本资产不可变；缺少平台、渠道错配、错误 ABI、错误或陈旧报告、版本回退或内容替换直接失败。同源 draft 可恢复补传缺失资产；Pages 部署可单独重试。后续 preview 内容变化递增 `preview_revision`，版本排序依次比较源码版本、正式/预发布、`dev.N` 与集成修订号。

下载入口为 [GitHub Releases](https://github.com/psiQAQ/blender_mcp-setup-guide/releases)。[根索引](https://notes.psiqaq.cn/blender_mcp-setup-guide/index.json)继续提供 5.1 stable；[5.2 preview 索引](https://notes.psiqaq.cn/blender_mcp-setup-guide/blender-5.2/preview/index.json)独立发布。未来 5.2 stable 使用 `/blender-5.2/stable/index.json`。联网安装需启用 Allow Online Access。

## 模板与上游维护

`scripts/scaffold_extension.py <extension_id> <output_directory>` 生成无第三方依赖的通用模板。标识按 Extension ID 替换，拒绝覆盖现有目录；模板使用显式注册、失败回滚和逆序卸载。用法见技能中的 template-guide.md。

`scripts/upstream_sync.py` 同时检查官方 main 和稳定 Release/tag，输出审查记录，不修改源码或发布。新的官方稳定 tag 发布后，审查其 5.2 兼容性、固定提交并重新完成三平台验收，随后人工触发 stable 发布工作流。
