import json
from pathlib import Path

import bpy

from .runtime import ServiceError


def integration():
    import sys
    return sys.modules[__package__]


class BLMCP_INTEGRATION_OT_start(bpy.types.Operator):
    bl_idname = "blmcp_integration.start"
    bl_label = "Start MCP"

    def execute(self, context):
        addon = integration()
        try:
            addon.start_service()
        except (ServiceError, OSError) as error:
            addon.LAST_ERROR = str(error)
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        return {"FINISHED"}


class BLMCP_INTEGRATION_OT_stop(bpy.types.Operator):
    bl_idname = "blmcp_integration.stop"
    bl_label = "Stop MCP"

    def execute(self, context):
        addon = integration()
        try:
            addon.stop_service()
        except (ServiceError, OSError, ExceptionGroup) as error:
            addon.LAST_ERROR = str(error)
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        return {"FINISHED"}


class BLMCP_INTEGRATION_OT_copy_configuration(bpy.types.Operator):
    bl_idname = "blmcp_integration.copy_configuration"
    bl_label = "Copy Connection Configuration"

    def execute(self, context):
        addon = integration()
        preferences = context.preferences.addons[__package__].preferences
        try:
            content = addon.SERVICE.configuration(preferences.client)
        except (ServiceError, OSError) as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        context.window_manager.clipboard = content
        (Path(addon.service_directory()) / "client-config.txt").write_text(content, encoding="utf-8")
        self.report({"INFO"}, "Configuration copied and saved in the extension user directory")
        return {"FINISHED"}


class BLMCP_INTEGRATION_OT_diagnose(bpy.types.Operator):
    bl_idname = "blmcp_integration.diagnose"
    bl_label = "Check Connection"

    def execute(self, context):
        addon = integration()
        try:
            state = addon.SERVICE.poll()
        except ServiceError as error:
            addon.LAST_ERROR = str(error)
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        if state != "Running" or addon._bridge is None or not addon._bridge.is_running():
            self.report({"WARNING"}, addon.LAST_ERROR or f"MCP service: {state}")
            return {"CANCELLED"}
        try:
            addon.SERVICE.check_health()
        except (ServiceError, OSError) as error:
            addon.LAST_ERROR = str(error)
            self.report({"ERROR"}, f"HTTP health check failed: {error}")
            return {"CANCELLED"}
        self.report({"INFO"}, "MCP service and Blender bridge are running")
        return {"FINISHED"}


class BLMCP_INTEGRATION_AP_preferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    http_port: bpy.props.IntProperty(name="HTTP Port", default=8000, min=1024, max=65535)
    bridge_port: bpy.props.IntProperty(name="Bridge Port", default=9876, min=1024, max=65535)
    autostart: bpy.props.BoolProperty(name="Start MCP When Enabled", default=True)
    client: bpy.props.EnumProperty(
        name="Agent", items=(("CODEX", "Codex", ""), ("CLAUDE", "Claude Code", ""), ("OPENCODE", "OpenCode", "")),
        default="CODEX",
    )

    def draw(self, context):
        addon = integration()
        layout = self.layout
        source = json.loads((Path(__file__).parent / "provenance.json").read_text(encoding="utf-8"))
        layout.label(text=f"Blender Lab MCP {source['version']} · integration {source['integration_revision']}")
        layout.label(text=f"MCP: {addon.SERVICE.state}")
        if addon.LAST_ERROR:
            layout.label(text=addon.LAST_ERROR, icon="ERROR")
        column = layout.column()
        column.enabled = addon.SERVICE.process is None
        column.prop(self, "http_port")
        column.prop(self, "bridge_port")
        layout.prop(self, "autostart")
        row = layout.row()
        row.operator("blmcp_integration.start", icon="PLAY")
        row.operator("blmcp_integration.stop", icon="CANCEL")
        layout.prop(self, "client")
        layout.operator("blmcp_integration.copy_configuration", icon="COPYDOWN")
        layout.operator("blmcp_integration.diagnose", icon="CHECKMARK")
        layout.label(text=f"Logs and configuration: {addon.service_directory()}")


CLASSES = (
    BLMCP_INTEGRATION_OT_start, BLMCP_INTEGRATION_OT_stop,
    BLMCP_INTEGRATION_OT_copy_configuration, BLMCP_INTEGRATION_OT_diagnose,
    BLMCP_INTEGRATION_AP_preferences,
)
