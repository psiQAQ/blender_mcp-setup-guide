import atexit

import bpy

from . import preferences
from .runtime import Service, ServiceError


SERVICE = Service()
LAST_ERROR = ""
_registered_classes = []
_bridge = None


def service_directory():
    return bpy.utils.extension_path_user(__package__, path="service", create=True)


def stop_service():
    global _bridge
    errors = []
    try:
        if bpy.app.timers.is_registered(_poll_service):
            bpy.app.timers.unregister(_poll_service)
    except Exception as error:
        errors.append(error)
    try:
        SERVICE.stop()
    except Exception as error:
        errors.append(error)
    if _bridge is not None:
        _bridge._integration_token = ""
        try:
            _bridge.stop()
            _bridge = None
        except Exception as error:
            errors.append(error)
    if errors:
        raise ExceptionGroup("Service cleanup failed: " + "; ".join(map(str, errors)), errors)


def _poll_service():
    global LAST_ERROR
    try:
        SERVICE.poll()
        if _bridge is not None:
            _bridge.poll()
    except (ServiceError, OSError) as error:
        LAST_ERROR = str(error)
        try:
            stop_service()
        except Exception as cleanup_error:
            LAST_ERROR += f"; {cleanup_error}"
        return None
    return 0.05


def start_service():
    global _bridge, LAST_ERROR
    from ._vendor.bridge import mcp_to_blender_server as bridge
    from .runtime import require_free_port

    if SERVICE.process is not None or _bridge is not None or bpy.app.timers.is_registered(_poll_service):
        raise ServiceError("Service is already started")
    conflicts = [key for key in bpy.context.preferences.addons.keys() if key != __package__ and key.endswith(".mcp")]
    if conflicts:
        raise ServiceError("Disable the original MCP extension before starting this integration")
    prefs = bpy.context.preferences.addons[__package__].preferences
    require_free_port(prefs.bridge_port)
    try:
        SERVICE.start(service_directory(), prefs.http_port, prefs.bridge_port, bpy.app.python_args)
        bridge._integration_token = SERVICE.bridge_token
        bridge.start("127.0.0.1", prefs.bridge_port)
        _bridge = bridge
        if not bpy.app.background:
            bpy.app.timers.register(_poll_service, first_interval=0.05, persistent=True)
    except Exception as error:
        _bridge = bridge
        try:
            stop_service()
        except Exception as cleanup_error:
            error.add_note(f"Service start rollback failed: {cleanup_error}")
        raise
    LAST_ERROR = ""


def _autostart():
    global LAST_ERROR
    prefs = bpy.context.preferences.addons[__package__].preferences
    if prefs.autostart:
        try:
            start_service()
        except (ServiceError, OSError) as error:
            LAST_ERROR = str(error)
    return None


def register():
    if bpy.app.version[:2] != (5, 1):
        raise ServiceError("This integration is validated for Blender 5.1.x")
    if _registered_classes:
        raise RuntimeError("Extension is already registered")
    try:
        for cls in preferences.CLASSES:
            bpy.utils.register_class(cls)
            _registered_classes.append(cls)
        atexit.register(stop_service)
        if not bpy.app.background:
            bpy.app.timers.register(_autostart, first_interval=1.0)
    except Exception as error:
        try:
            unregister()
        except Exception as cleanup_error:
            error.add_note(f"Registration rollback failed: {cleanup_error}")
        raise


def unregister():
    errors = []
    try:
        if bpy.app.timers.is_registered(_autostart):
            bpy.app.timers.unregister(_autostart)
    except Exception as error:
        errors.append(error)
    try:
        stop_service()
    except Exception as error:
        errors.append(error)
    atexit.unregister(stop_service)
    for cls in reversed(_registered_classes.copy()):
        try:
            bpy.utils.unregister_class(cls)
            _registered_classes.remove(cls)
        except Exception as error:
            errors.append(error)
    if errors:
        raise ExceptionGroup("Extension cleanup failed: " + "; ".join(map(str, errors)), errors)
