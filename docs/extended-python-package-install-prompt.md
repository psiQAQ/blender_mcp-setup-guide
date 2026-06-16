你需要修改当前仓库中的 Blender 插件模板与对应 skills，使其支持“插件私有 Python 依赖管理”，目标是：插件需要的第三方 Python 包只安装到插件自己的目录，不污染 Blender 自带 Python 环境；插件启用时依赖可用，插件停用后私有依赖路径不再参与 import；插件偏好设置面板中显示依赖是否满足，缺失时提示用户手动点击安装；安装时默认使用清华 PyPI 镜像，但用户可关闭。

请先阅读并理解仓库结构，重点检查以下目录和文件：

- `.agents/skills/blender-mcp-skills/SKILL.md`
- `.agents/skills/blender-mcp-skills/references/template-guide.md`
- `.agents/skills/blender-mcp-skills/references/extension-workflow.md`
- `.agents/skills/blender-mcp-skills/references/pitfalls-and-fixes.md`
- `.agents/skills/blender-mcp-skills/templates/extension_addon/__init__.py`
- `.agents/skills/blender-mcp-skills/templates/extension_addon/auto_load.py`
- `.agents/skills/blender-mcp-skills/templates/extension_addon/preferences.py`
- `.agents/skills/blender-mcp-skills/templates/extension_addon/blender_manifest.toml`
- `.agents/skills/blender-mcp-skills/templates/extension_addon/scripts/validate_extension.py`

修改目标如下。

第一，新增插件私有依赖管理模块：

在模板目录中新增：

`.agents/skills/blender-mcp-skills/templates/extension_addon/utils/dependency_manager.py`

该模块负责：

- 定义插件私有依赖路径：`deps/site-packages`
- 使用 `sys.executable -m pip install --target deps/site-packages` 安装依赖
- 不允许无 `--target` 的全局 pip install
- 支持默认清华 PyPI 镜像：`https://pypi.tuna.tsinghua.edu.cn/simple`
- 支持用户关闭清华镜像
- 支持 `--no-cache-dir` 选项
- 提供 `add_private_deps_path()`
- 提供 `remove_private_deps_path()`
- 提供 `private_deps_path_enabled()`
- 提供 `get_dependency_status()`
- 提供 `get_missing_requirements()`
- 提供 `all_dependencies_ready()`
- 提供 `install_missing_dependencies()`
- 提供 `assert_dependencies_ready()`

注意依赖配置应集中写在 `dependency_manager.py` 中，示例依赖可以使用：

- `requests==2.32.3`
- `PyYAML==6.0.2`

但要写成易于后续修改的结构，例如 `DependencySpec(import_name, pip_requirement, display_name)`。

第二，修改模板 `__init__.py`。

当前模板如果在模块导入阶段直接执行 `auto_load.init()`，需要改掉。要求：

- 不要在文件顶层直接调用 `auto_load.init()`
- 在 `register()` 中先调用 `dependency_manager.add_private_deps_path()`
- 然后调用 `auto_load.init()`
- 然后调用 `auto_load.register()`
- 在 `unregister()` 中先调用 `auto_load.unregister()`
- 最后调用 `dependency_manager.remove_private_deps_path()`

目标是：已经安装在 `deps/site-packages` 中的依赖，在插件启用和 `auto_load` 扫描时可见；插件停用后该路径从 `sys.path` 移除。

第三，修改 `preferences.py`。

扩展 AddonPreferences，使插件设置页显示依赖状态。要求：

- 保留原有 `show_debug` 设置
- 新增 `use_tsinghua_mirror: BoolProperty(default=True)`
- 新增 `pip_no_cache_dir: BoolProperty(default=False)`
- 在设置面板中显示：
  - 私有依赖路径 `deps/site-packages`
  - 当前私有依赖路径是否已经加入 `sys.path`
  - 每个依赖包是否已安装
  - 每个依赖包的实际导入来源 `spec.origin`
- 如果依赖缺失，显示“Install Missing Dependencies”按钮
- 点击按钮后才安装缺失依赖
- 不允许插件启用时静默自动安装
- 安装成功或失败需要通过 `self.report()` 给出反馈，并在 Blender console 打印详细错误

新增一个 Operator，例如：

`EXAMPLE_OT_install_missing_dependencies`

其功能是调用：

`dependency_manager.install_missing_dependencies(use_tsinghua_mirror=prefs.use_tsinghua_mirror, no_cache_dir=prefs.pip_no_cache_dir)`

第四，修改 `auto_load.py`。

确保 `auto_load.py` 不会递归扫描第三方依赖目录。需要排除以下目录：

- `deps`
- `wheels`
- `scripts`
- `.venv`
- `venv`
- `__pycache__`

如果当前 `auto_load.py` 使用 `pkgutil.iter_modules()` 递归扫描所有子模块，请在遍历时加入排除逻辑，避免错误导入 `deps/site-packages` 中的第三方包。

第五，修改 `blender_manifest.toml`。

在 manifest 模板中补充注释说明：

- 如果插件允许从 PyPI 或镜像源安装依赖，应声明 network 权限
- 私有 pip 安装适合开发期或内部工具
- 正式发布 extension 时，更推荐使用 `wheels = [...]` 打包离线依赖

可以加入示例：

```toml
[permissions]
network = "Install missing Python packages into the extension private dependency directory"
````

但不要破坏现有 manifest 的基本结构。

第六，新增依赖策略文档。

新增文件：

`.agents/skills/blender-mcp-skills/references/dependency-policy.md`

内容要说明以下规则：

* 不要把包安装到 Blender 自带 Python 的全局环境
* 开发期或内部插件可以使用 `deps/site-packages` + `pip --target`
* 插件启用时加入私有依赖路径
* 插件停用时移除私有依赖路径
* 不允许在 `register()`、模块 import 阶段、插件启用阶段静默安装依赖
* 只能在用户明确点击安装按钮后安装
* 不要在模块顶部导入可选第三方依赖
* 第三方依赖应延迟导入，例如在 operator 的 `execute()` 或具体业务函数内部导入
* 正式发布时优先考虑 `wheels` 和 `blender_manifest.toml`
* 对 `torch`、`opencv-python`、`scipy`、`open3d`、CUDA 相关包，应优先建议外部 Python 环境，而不是塞进 Blender Python

第七，修改 `SKILL.md`。

在 skill 的规则中加入依赖管理规则，并引用 `references/dependency-policy.md`。要求 agent 在创建或修改 Blender 插件时遵守：

* 不要执行无 `--target` 的 pip install
* 不要污染 Blender 自带 Python 环境
* 不要在顶层导入可选第三方包
* 不要在插件启用时自动安装依赖
* 默认通过偏好设置面板显示依赖状态并由用户点击安装
* 默认清华镜像可用但必须可关闭
* 重型依赖建议外部 Python 环境

第八，修改 `extension-workflow.md`。

把原来的 “No auto-install policy” 修改得更精确：

* 禁止 silent auto-install
* 允许用户在 AddonPreferences 中点击按钮后安装
* 安装位置必须是插件私有 `deps/site-packages`
* 安装命令必须使用 `--target`
* 不允许把依赖装进 Blender bundled Python 的全局 site-packages
* 不允许插件启用阶段隐藏联网安装

第九，修改 `template-guide.md`。

更新模板目录说明，加入：

* `utils/dependency_manager.py`
* `deps/site-packages`
* `wheels`

并说明：

* `deps/site-packages` 用于开发期或内部插件的私有依赖安装
* release build 默认不应直接打包 `deps/site-packages`
* 正式发布推荐使用 `wheels` 和 manifest 中的 `wheels = [...]`

第十，修改 `pitfalls-and-fixes.md`。

新增常见坑：

1. 插件停用后从 `sys.path` 移除私有路径，不代表已经 import 的模块会自动从 `sys.modules` 卸载。
2. 如果在 operator/panel 顶层导入第三方包，缺包时会导致插件启用失败，用户连安装按钮都看不到。
3. `auto_load.py` 如果扫描 `deps/site-packages`，会误导入第三方包，应排除 `deps`、`wheels`、`.venv`、`venv`、`scripts`。
4. 在线安装依赖必须是用户显式点击，不能在 `register()` 阶段自动联网。
5. `numpy`、`opencv-python`、`scipy`、`torch` 等二进制包可能出现 ABI、DLL、Python 版本不匹配问题。
6. 重型依赖应优先用外部 Python 环境，通过 subprocess、socket、HTTP 或 MCP 与 Blender 插件通信。

第十一，增强 `validate_extension.py`。

增加轻量检查：

* 如果发现 Python 文件中有类似 `pip install` 且没有 `--target`，给出 warning 或 error
* 如果发现模板中存在 `deps/site-packages`，提示 release build 应考虑排除或改用 wheels
* 如果发现顶层导入常见第三方包，例如 `requests`、`yaml`、`numpy`、`cv2`、`PIL`、`scipy`、`torch`、`open3d`，给出 warning，建议延迟导入
* 如果插件代码中存在在线 pip 安装逻辑，但 manifest 未声明 network 权限，给出 warning

注意：这里优先做 warning，不要过度阻止开发期使用。

第十二，最终代码风格要求。

* 尽量保持现有模板风格，不要大规模重构无关代码。
* 所有新增代码必须能被 Blender 4.2+ 使用。
* 不要引入额外依赖来实现依赖管理器本身。
* 不要在 `dependency_manager.py` 顶部导入第三方包。
* 不要把依赖实际安装到仓库中。
* 不要提交 `deps/site-packages` 中的第三方包。
* 修改完成后检查所有 Python 文件语法。
* 修改完成后给出变更摘要，按文件列出改了什么。

最终期望结果：

这个 Blender 插件模板应支持以下工作流：

1. 用户安装并启用插件。
2. 插件不会自动联网，也不会自动安装依赖。
3. 插件注册时会把已有的 `deps/site-packages` 加入 `sys.path`。
4. 用户打开插件 Preferences，可以看到依赖是否缺失。
5. 用户可以选择是否使用清华镜像，默认使用。
6. 用户点击安装按钮后，插件调用 Blender 自带 Python 的 `python -m pip install --target 插件目录/deps/site-packages` 安装缺失包。
7. 安装完成后，插件功能可以通过延迟导入使用这些包。
8. 用户禁用插件后，插件私有依赖路径会从 `sys.path` 移除。
9. Blender 自带 Python 的全局 site-packages 不被修改。
10. 对正式发布版本，文档提醒优先使用 wheels 或外部 Python 环境。
