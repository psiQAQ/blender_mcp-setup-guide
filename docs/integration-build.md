# 构建、验证与发布

在仓库根目录操作。集成包要求原生 Windows x64、Linux x64 或 macOS Apple Silicon，以及 Blender 5.1.x / CPython 3.13。运行时不安装依赖；构建阶段按完整版本与 SHA-256 下载 wheels，仅安装至被忽略的 `build/` 打包目录。通用开发模板支持 Blender 4.2+，其兼容范围独立于集成产品。

## 原生构建

PowerShell 示例：

```powershell
$blender = 'C:\Program Files\Blender Foundation\Blender 5.1\blender.exe'
$blenderPython = 'C:\Program Files\Blender Foundation\Blender 5.1\5.1\python\bin\python.exe'
& $blenderPython -B scripts/build_integration.py --blender $blender --platform windows-x64
```

Linux/macOS 使用 Bash，将路径替换为本机 Blender 及其配套 Python：

```bash
blender='/path/to/blender'
blender_python='/path/to/blender/python/bin/python3.13'
"$blender_python" -B scripts/build_integration.py --blender "$blender"
```

`--platform` 可选；默认检测本机。指定的平台与解释器系统、架构、CPython 3.13 不一致时拒绝构建。平台配置、官方 Blender URL/hash 和依赖锁路径统一来自 `packaging/platforms.json`。Windows 为 40 个 wheels，Linux/macOS 为 39 个；pywin32 只用于 Windows。官方 MCP 固定 v1.0.3 / `2cea8d566dde07fbac28a61d698909d69724e853`。

构建输出为 `build/dist/blender_mcp_integration-1.0.3+integration.1-<platform>.zip`、对应 `.sha256` 与 `provenance-<platform>.json`。来源包含干净仓库提交、官方提交、依赖版本、wheel hash 和两处桥接补丁 hash。ZIP 通过官方 `extension validate`，保留依赖数据与许可证，排除开发环境、缓存和构建脚本。

已核验的官方源码和 wheel 缓存可通过 `--upstream <目录> --wheelhouse <目录> --offline` 复用。构建不得从已安装插件目录复制依赖。更新依赖时，三个平台同步核对版本及独立 wheel hash。

## 本地验证与 CI

```powershell
& $blenderPython -B scripts/run_checks.py
& $blenderPython -B scripts/test_templates.py --blender $blender
$package = 'build/dist/blender_mcp_integration-1.0.3+integration.1-windows-x64.zip'
& $blenderPython -B scripts/test_integration.py --blender $blender --package $package
& $blenderPython -B scripts/test_upgrade.py --blender $blender --package $package
& $blenderPython -B scripts/test_gui.py --blender $blender --package $package
```

测试使用独立 `BLENDER_USER_RESOURCES`，保留用户现有 Blender 配置。使用真实 MCP SDK、最终 ZIP 和 GUI 事件循环；场景操作恢复对象数。升级检查从 HTTP 索引安装前一修订号夹具，再升级至实际候选，验证偏好与凭据保留。

CI 使用 windows-2022、ubuntu-24.04、macos-15 ARM64 原生 runner，hash 固定 Blender 5.1.2，并在 5.1.0 上验证相同 ZIP 的安装、MCP 与生命周期。Linux GUI 使用 Xvfb/Mesa；Windows GUI 使用 [mesa-dist-win](https://github.com/pal1000/mesa-dist-win) 的 hash 固定 26.2.4 llvmpipe，仅部署到 `build/toolchain/` 下的 CI Blender，不包含在安装包中。GUI 报告保存实际图形 renderer。三个产物汇总后，分别从统一索引选择平台、实际安装与升级。全部通过才产生 `validated-<platform>`。

报告绑定平台及 ZIP SHA-256。失败检查写入 Failed，不复用旧 Passed 报告。人工 GUI 操作及三个实际 agent 的验收与自动化测试分开记录。

## 正式发布

将 Pages 来源设置为 GitHub Actions。为完全通过 CI 的同一干净提交创建 `v1.0.3+integration.1` 标签，手动触发 `release.yml`，指定该提交的成功 CI run ID 和标签。

工作流复用三个已验证产物，核对来源、标签、完整平台集合和所有报告；先上传 draft Release 并逐资产鉴权回读大小/hash，再验证三个条目的官方 Extensions 索引。全部通过后公开正式 Release，回读公开下载，部署 Pages。三个原生 runner 随后从公开索引实际安装并调用 MCP。

相同版本资产不可变；缺少平台、错误 ABI、错误报告、版本回退或不同内容直接失败。同源 draft 可恢复补传缺失资产；已公开 Release 保留字节一致的资产，Pages 部署可单独重试。版本排序显式比较官方版本和集成修订号。

下载入口为 [GitHub Releases](https://github.com/psiQAQ/blender_mcp-setup-guide/releases)，更新索引为 [index.json](https://psiQAQ.github.io/blender_mcp-setup-guide/index.json)。用户在 Blender 中添加索引即可选择对应平台并更新；联网安装需启用 Allow Online Access。

## 模板与上游维护

`scripts/scaffold_extension.py <extension_id> <output_directory>` 生成无第三方依赖的通用模板。标识按 Extension ID 替换，拒绝覆盖现有目录；模板使用显式注册、失败回滚和逆序卸载。用法见技能中的 template-guide.md。

`scripts/upstream_sync.py` 读取官方稳定 Release API 并核对 Git tag，输出来源与差异供审查；它不更新源码或发布版本。采纳上游更新前复核官方改动、三平台依赖锁和最终 ZIP 全套验收。
