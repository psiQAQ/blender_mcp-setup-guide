import bpy

from . import preferences, properties
from .operators.object_ops import MY_EXAMPLE_EXTENSION_OT_run
from .panels.viewport_panel import MY_EXAMPLE_EXTENSION_PT_panel


CLASSES = (
    properties.MY_EXAMPLE_EXTENSION_PG_settings,
    preferences.MY_EXAMPLE_EXTENSION_AP_preferences,
    MY_EXAMPLE_EXTENSION_OT_run,
    MY_EXAMPLE_EXTENSION_PT_panel,
)
_registered_classes = []
_properties_registered = False


def register():
    global _properties_registered
    if _registered_classes:
        raise RuntimeError("Extension is already registered")
    try:
        for cls in CLASSES:
            bpy.utils.register_class(cls)
            _registered_classes.append(cls)
        properties.register()
        _properties_registered = True
    except Exception as error:
        try:
            unregister()
        except Exception as cleanup_error:
            error.add_note(f"Registration rollback failed: {cleanup_error}")
        raise


def unregister():
    global _properties_registered
    errors = []
    if _properties_registered:
        try:
            properties.unregister()
            _properties_registered = False
        except (RuntimeError, AttributeError) as error:
            errors.append(error)
    for cls in reversed(_registered_classes.copy()):
        try:
            bpy.utils.unregister_class(cls)
            _registered_classes.remove(cls)
        except (RuntimeError, ValueError) as error:
            errors.append(error)
    if errors:
        raise ExceptionGroup("Extension cleanup failed", errors)
