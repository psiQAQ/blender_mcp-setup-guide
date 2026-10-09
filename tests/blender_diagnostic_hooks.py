"""Instrument only the disposable diagnostic Blender and its service copy."""

import functools
import hashlib
import json
import shutil
import time
from pathlib import Path


def instrument_server(server_class):
    original = server_class.call_tool

    @functools.wraps(original)
    async def measured(self, name, *args, **kwargs):
        started = time.perf_counter()
        print('[MCP-DIAG] ' + json.dumps({'event': 'tool_start', 'tool': name,
                                         'time': time.time()}), flush=True)
        try:
            result = await original(self, name, *args, **kwargs)
        except BaseException as error:
            print('[MCP-DIAG] ' + json.dumps({'event': 'tool_error', 'tool': name,
                    'type': type(error).__name__, 'seconds': time.perf_counter() - started}), flush=True)
            raise
        print('[MCP-DIAG] ' + json.dumps({'event': 'tool_return', 'tool': name,
                    'time': time.time(), 'seconds': time.perf_counter() - started}), flush=True)
        return result

    server_class.call_tool = measured


def instrument_host(addon, control):
    import bpy

    root = Path(addon.__file__).parent
    path = root / 'server.py'
    original = path.read_bytes()
    text = original.decode('utf-8')
    newline = '\r\n' if '\r\n' in text else '\n'
    marker = '    from mcp.server.fastmcp import FastMCP' + newline
    if text.count(marker) != 1:
        raise RuntimeError('Diagnostic server hook requires one FastMCP import')
    patched = text.replace(marker, marker +
            '    from mcp_diagnostic_hooks import instrument_server' + newline +
            '    instrument_server(FastMCP)' + newline)
    shutil.copyfile(__file__, root / '_vendor/mcp_diagnostic_hooks.py')
    path.write_bytes(patched.encode('utf-8'))
    destination = control / 'diagnostic/blender.log'
    destination.parent.mkdir()
    profile = control / 'scene-profile.json'
    if profile.exists():
        settings = json.loads(profile.read_text(encoding='utf-8'))
        for key, value in settings['render'].items():
            setattr(bpy.context.scene.render, key, value)
        bpy.context.scene.cycles.samples = settings['cycles_samples']
        bpy.ops.wm.save_as_mainfile(filepath=str(control / 'fixture.blend'))

    def record(event):
        def handler(scene, *unused):
            row = {'event': event, 'time': time.time(), 'engine': scene.render.engine,
                   'resolution': [scene.render.resolution_x, scene.render.resolution_y],
                   'render_running': bpy.app.is_job_running('RENDER'),
                   'output_exists': Path(scene.render.filepath).is_file()}
            with destination.open('a', encoding='utf-8') as stream:
                stream.write(json.dumps(row) + '\n')
        return handler

    for event in ('render_init', 'render_write', 'render_complete', 'render_cancel'):
        getattr(bpy.app.handlers, event).append(record(event))
    return {'scope': 'disposable installed copy only',
            'original_server_sha256': hashlib.sha256(original).hexdigest(),
            'instrumented_server_sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
