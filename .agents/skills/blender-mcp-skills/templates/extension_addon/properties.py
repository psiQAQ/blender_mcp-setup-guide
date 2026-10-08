import bpy

from .constants import SCENE_SETTINGS_NAME


class MY_EXAMPLE_EXTENSION_PG_settings(bpy.types.PropertyGroup):
    message: bpy.props.StringProperty(
        name="Message",
        description="Message shown by the demo operator",
        default="Hello from extension",
    )


def register():
    if hasattr(bpy.types.Scene, SCENE_SETTINGS_NAME):
        raise RuntimeError(f"Scene property already exists: {SCENE_SETTINGS_NAME}")
    setattr(
        bpy.types.Scene,
        SCENE_SETTINGS_NAME,
        bpy.props.PointerProperty(type=MY_EXAMPLE_EXTENSION_PG_settings),
    )


def unregister():
    if hasattr(bpy.types.Scene, SCENE_SETTINGS_NAME):
        delattr(bpy.types.Scene, SCENE_SETTINGS_NAME)
