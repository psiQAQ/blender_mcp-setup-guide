"""Preserve the native installer's error before attempting to import an add-on."""

from contextlib import contextmanager
import sys

import bpy

from check_reports import write_json


@contextmanager
def capture_install(control):
    from bl_pkg import bl_extension_utils

    trace = {"executable": sys.executable, "python_args": list(bpy.app.python_args), "messages": []}
    original = bl_extension_utils.command_output_from_json_0

    def command(args, **kwargs):
        trace["command"] = [*bl_extension_utils.blender_ext_cmd(kwargs["python_args"]), *args]
        generator = original(args, **kwargs)
        request_exit = None
        try:
            while True:
                messages = generator.send(request_exit)
                trace["messages"].extend(item for item in messages if item[0] != "PROGRESS")
                request_exit = yield messages
        except StopIteration:
            return
        finally:
            generator.close()
            write_json(control / "native-install.json", trace)

    bl_extension_utils.command_output_from_json_0 = command
    try:
        yield trace
    finally:
        bl_extension_utils.command_output_from_json_0 = original
    errors = [str(message) for kind, message in trace["messages"] if kind == "ERROR"]
    if errors:
        raise RuntimeError("Native extension installation failed: " + "; ".join(errors))
