# Common Pitfalls and Fixes

## 1) Submodule cache keeps old code

**Symptom:** update does not take effect after disable/enable.

**Fix:** clear `sys.modules["<package>.<submodule>"]` before re-importing submodules.

## 2) `hasattr` is unreliable for registration state

**Symptom:** `hasattr(bpy.types, "MyPropertyGroup")` returns `False` even after registration.

**Fix:**
- use explicit registration state and roll back completed registrations on failure
- validate PropertyGroup through attached scene property

## 3) Wrong module key for self-disable

**Symptom:** add-on cannot disable itself with display name.

**Fix:** use the full root package namespace (`bl_ext.<repo>.<id>`), preserved by root `__package__`.

## 4) `global` declaration order error

**Symptom:** `SyntaxError: name used prior to global declaration`.

**Fix:** put `global` statement before any variable usage in function scope.

## 5) Path errors in shell commands

**Symptom:** quoted path missing causes file-not-found for folders with spaces.

**Fix:** always quote full path variables in shell commands.

## 6) Unregister verification via `bpy.ops`

**Symptom:** operator-like checks look stale due proxy behavior.

**Fix:** verify removal via `bpy.types` and preferences add-ons map.

## 7) Broken or duplicate links in development path

**Symptom:** add-on changes do not apply or wrong directory is loaded.

**Fix:**
- remove broken symlink/junction entries
- remove duplicate links pointing to the same source
- keep only one active link target per module name

## 8) Handler duplication after repeated reload cycles

**Symptom:** handler executes multiple times after disable/enable loops.

**Fix:**
- unregister old handlers before register
- deduplicate handlers by function identity/name before append

## 9) Dependency conflicts in a sidecar

**Symptom:** Blender's bundled packages override the service's locked dependencies.

**Fix:** launch the independent service with `-I -S -B`, then explicitly initialize its bundled runtime and `.pth` files.

## 10) Missing optional dependencies break enable

**Symptom:** a package for an optional capability prevents the whole Extension from enabling.

**Fix:** do not import optional third-party packages at module top level; import them inside `execute()` or the function that needs them.

## 11) Module discovery scans dependency directories

**Symptom:** reload imports packages from `deps/site-packages` as if they were add-on modules.

**Fix:** default to explicit class/module lists. If discovery is needed, exclude dependency and development directories.

## 12) Network install happens during register

**Symptom:** enabling the add-on unexpectedly downloads packages.

**Fix:** bundle dependencies at build time as wheels, or as an isolated service runtime.

## 13) Binary packages fail inside Blender Python

**Symptom:** packages such as `numpy`, `opencv-python`, `scipy`, or `torch` fail with ABI, DLL, or Python version errors.

**Fix:** verify Blender Python compatibility first and prefer wheels or an external Python environment for heavy binary dependencies.

## 14) Heavy dependencies are forced into Blender

**Symptom:** add-on startup becomes fragile or slow because it embeds large ML/CV/CUDA stacks.

**Fix:** run heavy dependencies in an external Python service and communicate through `subprocess`, sockets, HTTP, or MCP.
