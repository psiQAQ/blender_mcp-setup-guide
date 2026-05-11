# Common Pitfalls and Fixes

## 1) Submodule cache keeps old code

**Symptom:** update does not take effect after disable/enable.

**Fix:** clear `sys.modules["<package>.<submodule>"]` before re-importing submodules.

## 2) `hasattr` is unreliable for registration state

**Symptom:** `hasattr(bpy.types, "MyPropertyGroup")` returns `False` even after registration.

**Fix:**
- use `try/except ValueError` for class registration
- validate PropertyGroup through attached scene property

## 3) Wrong module key for self-disable

**Symptom:** add-on cannot disable itself with display name.

**Fix:** use module name from `self.__class__.__module__.split(".")[0]`.

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
