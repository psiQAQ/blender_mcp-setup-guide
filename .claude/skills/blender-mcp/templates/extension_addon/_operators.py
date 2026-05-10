import bpy


class EXAMPLE_OT_run(bpy.types.Operator):
    bl_idname = "example_extension.run"
    bl_label = "Run Example"
    bl_description = "Run a minimal extension operator"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        settings = getattr(context.scene, "example_extension_settings", None)
        message = settings.message if settings else "Extension is running"
        self.report({"INFO"}, message)
        return {"FINISHED"}
