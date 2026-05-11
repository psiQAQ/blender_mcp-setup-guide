import bpy


class EXAMPLE_AP_preferences(bpy.types.AddonPreferences):
    bl_idname = __package__.split(".")[0]

    show_debug: bpy.props.BoolProperty(
        name="Show Debug",
        description="Enable debug behavior in this extension",
        default=False,
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "show_debug")
