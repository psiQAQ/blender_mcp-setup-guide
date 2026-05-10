import bpy


class EXAMPLE_PT_panel(bpy.types.Panel):
    bl_idname = "EXAMPLE_PT_panel"
    bl_label = "Extension Demo"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Extension Demo"

    def draw(self, context):
        layout = self.layout
        settings = getattr(context.scene, "example_extension_settings", None)

        if settings:
            layout.prop(settings, "message")

        layout.operator("example_extension.run", icon="PLAY")
