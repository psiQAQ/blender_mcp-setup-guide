import bpy


def _addon_module_name():
    return __package__ or __name__.rpartition(".")[0]


class EXAMPLE_AP_preferences(bpy.types.AddonPreferences):
    bl_idname = _addon_module_name()

    show_debug: bpy.props.BoolProperty(
        name="Show Debug",
        description="Enable debug behavior in this extension",
        default=False,
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "show_debug")
