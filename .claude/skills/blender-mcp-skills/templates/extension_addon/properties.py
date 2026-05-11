import bpy


class EXAMPLE_PG_settings(bpy.types.PropertyGroup):
    message: bpy.props.StringProperty(
        name="Message",
        description="Message shown by the demo operator",
        default="Hello from extension",
    )


def register():
    if not hasattr(bpy.types.Scene, "example_extension_settings"):
        bpy.types.Scene.example_extension_settings = bpy.props.PointerProperty(type=EXAMPLE_PG_settings)


def unregister():
    if hasattr(bpy.types.Scene, "example_extension_settings"):
        del bpy.types.Scene.example_extension_settings
