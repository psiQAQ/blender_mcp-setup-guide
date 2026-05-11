import bpy

from ..utils.common import get_extension_settings


class EXAMPLE_PT_panel(bpy.types.Panel):
    bl_idname = "EXAMPLE_PT_panel"
    bl_label = "Extension Demo"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Extension Demo"

    def draw(self, context):
        layout = self.layout
        settings = get_extension_settings(context)

        if settings:
            layout.prop(settings, "message")

        layout.operator("example_extension.run", icon="PLAY")
