import bpy


class MY_EXAMPLE_EXTENSION_AP_preferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    show_debug: bpy.props.BoolProperty(
        name="Show Debug",
        description="Show diagnostic information",
        default=False,
    )

    def draw(self, context):
        self.layout.prop(self, "show_debug")
