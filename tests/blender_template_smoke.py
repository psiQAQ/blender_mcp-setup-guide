import importlib
import json
import sys

import bpy


def main():
    packages = sys.argv[sys.argv.index("--") + 1:]
    modules = []
    for package in packages:
        outcome = bpy.ops.extensions.package_install_files(filepath=package, repo="user_default", enable_on_install=True)
        assert outcome == {"FINISHED"}, outcome
    for identifier in ("template_alpha", "template_beta"):
        key = f"bl_ext.user_default.{identifier}"
        assert key in bpy.context.preferences.addons
        module = importlib.import_module(key)
        modules.append(module)
        assert getattr(bpy.ops, identifier).run() == {"FINISHED"}
        assert hasattr(bpy.types.Scene, f"{identifier}_settings")
    for module in modules:
        for _ in range(3):
            assert bpy.ops.preferences.addon_disable(module=module.__name__) == {"FINISHED"}
            assert not module._registered_classes
            assert not hasattr(bpy.types.Scene, module.properties.SCENE_SETTINGS_NAME)
            assert bpy.ops.preferences.addon_enable(module=module.__name__) == {"FINISHED"}
        assert bpy.ops.preferences.addon_disable(module=module.__name__) == {"FINISHED"}
    module = modules[0]
    original = module.CLASSES
    invalid = type("TEMPLATE_INVALID_OT_fail", (bpy.types.Operator,), {"bl_idname": "invalid", "bl_label": "Invalid Test"})
    module.CLASSES = original + (invalid,)
    try:
        module.register()
    except RuntimeError:
        assert not module._registered_classes
        assert not hasattr(bpy.types.Scene, module.properties.SCENE_SETTINGS_NAME)
        assert all(not cls.is_registered for cls in original)
    else:
        raise AssertionError("Invalid registration did not fail")
    finally:
        module.CLASSES = original
    print("TEMPLATE_RESULT=" + json.dumps({"status": "Passed", "two_extensions": True, "reload_cycles": 3, "registration_rollback": True}))


if __name__ == "__main__":
    main()
