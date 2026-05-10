# System Adaptation for Commands and Paths

Use this document before running Blender commands or touching add-on files.

## 1) Mandatory pre-checks

Check both runtime sides first:

1. **Agent runtime system** (where Claude tools run)
2. **Blender runtime system** (where Blender process runs)

### 1.1 Check agent runtime system

```bash
python - <<'PY'
import platform
print(platform.system())
print(platform.release())
PY
```

### 1.2 Check Blender runtime system

Use MCP `execute_blender_code` and run:

```python
import platform
import bpy
result = {
    "blender_system": platform.system(),
    "blender_version": bpy.app.version_string,
    "binary_path": bpy.app.binary_path,
    "scripts_user": bpy.utils.user_resource("SCRIPTS", path="addons"),
}
```

## 2) Resolve operating mode

### Mode A: Same-system runtime

If agent and Blender are on the same OS runtime, edit files directly in Blender add-on location.

### Mode B: Cross-system runtime

If agent and Blender are on different systems, choose a shared path strategy first.

#### B1) Agent on WSL/Linux, Blender on Windows

- Preferred: write through mounted Windows path from WSL, usually `/mnt/c/...`.
- Example add-on location pattern:
  - `/mnt/c/Users/<user>/AppData/Roaming/Blender Foundation/Blender/<version>/scripts/addons/`
- WSL/Windows 路径示例：
  - WSL 源目录：`/home/ustcw/project-folder/blender_mcp/my_addon`
  - Windows 目标目录（WSL 访问）：`/mnt/c/Users/<user>/AppData/Roaming/Blender Foundation/Blender/4.5/scripts/addons/my_addon`
  - Windows 原生写法：`C:\Users\<user>\AppData\Roaming\Blender Foundation\Blender\4.5\scripts\addons\my_addon`
- Path conversion helpers:

```bash
wslpath -w "/mnt/c/Users/..."
wslpath "C:\\Users\\..."
```

#### B2) No shared filesystem available

Fallback to MCP code execution that writes files on Blender host side.

## 3) Path discovery (do not hardcode)

Always query Blender first when possible:

```python
import bpy
scripts_addons = bpy.utils.user_resource("SCRIPTS", path="addons")
script_paths = bpy.utils.script_paths(subdir="addons")
```

For extension repository paths, inspect Blender preferences runtime state instead of assumptions.

## 4) Command execution safety

- Quote paths with spaces.
- Use add-on **module name** for enable/disable.
- Reload cycle:

```python
bpy.ops.preferences.addon_disable(module="your_module")
bpy.ops.preferences.addon_enable(module="your_module")
```

- Verify via `bpy.types` and preference add-on map, not only `bpy.ops` proxy checks.

## 5) Extension repo / target dir pre-check

在执行同步或 reload 前，先确认以下任一条件成立：

- 目标目录是 Blender 当前使用的扩展目录（来自 `bpy.utils.user_resource(...)` / `bpy.utils.script_paths(...)` 结果）。
- 或者目标目录是已确认可映射到 Blender 主机侧的共享路径（例如 WSL 的 `/mnt/c/...`）。

建议最少检查：

1. `target` 目录存在且可写。
2. `target` 与预期模块目录一致（避免写到错误版本或错误用户目录）。
3. 若使用 helper 脚本，先 `--dry-run` 预览复制列表。

## 6) Helper scope boundary

- `sync_and_reload.py` helper 只做文件增量同步（较新/新增文件）。
- helper 不执行 Blender API，不触发 add-on enable/disable。
- helper 不做任何 Python 包安装或自动依赖处理。

## 7) Quick checklist

Before file writes or reload operations:

1. Confirm agent system.
2. Confirm Blender system.
3. Confirm target add-on directory from Blender API.
4. Confirm extension repo/target mapping and write permission.
5. Select same-system or cross-system strategy.
6. Execute with quoted paths and module-name reload.
