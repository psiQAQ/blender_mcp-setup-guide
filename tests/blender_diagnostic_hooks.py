"""Instrument only the disposable diagnostic Blender and its service copy."""

import functools
import hashlib
import json
import os
import shutil
import time
from contextlib import contextmanager
from pathlib import Path


_SCREENSHOT_DIRECTORY = None
_SCREENSHOT_RECORDS = []


def _native_graphics_context():
    if os.name != 'nt':
        return {'status': 'Not Run', 'reason': 'Windows graphics context inspection only'}
    import ctypes
    from ctypes import wintypes

    user = ctypes.WinDLL('user32', use_last_error=True)
    graphics = ctypes.WinDLL('opengl32', use_last_error=True)
    for name in ('wglGetCurrentContext', 'wglGetCurrentDC'):
        function = getattr(graphics, name)
        function.argtypes = []
        function.restype = ctypes.c_void_p
    user.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user.GetWindowThreadProcessId.restype = wintypes.DWORD
    user.GetForegroundWindow.argtypes = []
    user.GetForegroundWindow.restype = wintypes.HWND
    user.WindowFromDC.argtypes = [wintypes.HDC]
    user.WindowFromDC.restype = wintypes.HWND
    for name in ('IsWindowVisible', 'IsIconic'):
        function = getattr(user, name)
        function.argtypes = [wintypes.HWND]
        function.restype = wintypes.BOOL
    user.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    user.GetClientRect.restype = wintypes.BOOL
    user.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    user.GetWindowRect.restype = wintypes.BOOL
    current_context = graphics.wglGetCurrentContext()
    current_dc = graphics.wglGetCurrentDC()
    drawable = user.WindowFromDC(current_dc) if current_dc else None
    foreground = user.GetForegroundWindow()
    pid = os.getpid()
    windows = []
    failures = []
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def visit(hwnd, unused):
        owner = wintypes.DWORD()
        user.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        if owner.value != pid:
            return True
        client, rectangle = wintypes.RECT(), wintypes.RECT()
        if not user.GetClientRect(hwnd, ctypes.byref(client)) or not user.GetWindowRect(hwnd, ctypes.byref(rectangle)):
            failures.append({'hwnd': int(hwnd), 'winerror': ctypes.get_last_error()})
            return True
        windows.append({
            'hwnd': int(hwnd), 'pid': pid, 'visible': bool(user.IsWindowVisible(hwnd)),
            'minimized': bool(user.IsIconic(hwnd)), 'foreground': hwnd == foreground,
            'current_wgl_drawable': hwnd == drawable,
            'client_size': [client.right - client.left, client.bottom - client.top],
            'window_rectangle': [rectangle.left, rectangle.top, rectangle.right, rectangle.bottom],
        })
        return True

    user.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
    user.EnumWindows.restype = wintypes.BOOL
    if not user.EnumWindows(callback_type(visit), 0):
        raise ctypes.WinError(ctypes.get_last_error())
    if failures:
        raise RuntimeError(f'Cannot inspect owned screenshot windows: {failures}')
    return {'status': 'Passed', 'pid': pid, 'wgl_context': int(current_context or 0),
            'wgl_dc': int(current_dc or 0), 'windows': windows,
            'note': 'Zero WGL handles do not describe the Vulkan context; only owned HWNDs are listed'}


@contextmanager
def observe_screenshot(source_path):
    """Record metadata before capture and inspect both PNGs after tool encoding."""
    import bpy
    from blender_screenshot_probe import context_details, graphics_details, image_details

    if _SCREENSHOT_DIRECTORY is None:
        raise RuntimeError('Screenshot observation requires an isolated instrument_host setup')
    row = {'sequence': len(_SCREENSHOT_RECORDS) + 1, 'status': 'Not Run', 'started_at': time.time()}
    _SCREENSHOT_RECORDS.append(row)
    capture = {}
    try:
        row['context_before'] = context_details()
        for item, window in zip(row['context_before']['windows'], bpy.context.window_manager.windows):
            item.update(workspace=window.workspace.name, position=[window.x, window.y])
        row['graphics_before'] = graphics_details()
        if 'error' in row['graphics_before']:
            raise RuntimeError(row['graphics_before']['error'])
        row['native_before'] = _native_graphics_context()
        yield capture
        # The caller has completed the original screenshot, downscale and base64 encoding.
        # Preserve both byte streams before image loading can affect a later tool call.
        artifacts = []
        if Path(source_path).is_file():
            artifacts.append(('source', Path(source_path).read_bytes()))
        if 'image_data' in capture:
            artifacts.append(('output', capture['image_data']))
        for kind, raw in artifacts:
            path = _SCREENSHOT_DIRECTORY / f"screenshot-{row['sequence']}-{kind}.png"
            path.write_bytes(raw)
            row[kind] = {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
        for kind, unused in artifacts:
            row[kind].update(image_details(Path(row[kind]['path'])))
        if 'error' in capture:
            row.update(status='Failed', error=capture['error'])
        elif len(artifacts) != 2:
            row.update(status='Failed', error='Screenshot returned without both source and output PNG bytes')
        else:
            row['observation_status'] = 'Passed'
            row['source_output_bytes_equal'] = artifacts[0][1] == artifacts[1][1]
            row['black_image'] = row['source']['black_image'] or row['output']['black_image']
            row['content_valid'] = row['source']['content_valid'] and row['output']['content_valid']
            row['status'] = 'Passed' if row['content_valid'] else 'Failed'
    except BaseException as error:
        row.update(status='Failed', error=f'{type(error).__name__}: {error}')
        raise
    finally:
        row['finished_at'] = time.time()
        report = {'status': 'Failed' if any(item['status'] != 'Passed' for item in _SCREENSHOT_RECORDS) else 'Passed',
                  'scope': 'One isolated host; metadata before capture, pixel inspection after encoding',
                  'captures': _SCREENSHOT_RECORDS}
        temporary = _SCREENSHOT_DIRECTORY / 'screenshots.pending.json'
        temporary.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8', newline='\n')
        temporary.replace(_SCREENSHOT_DIRECTORY / 'screenshots.json')


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

    global _SCREENSHOT_DIRECTORY, _SCREENSHOT_RECORDS
    control = Path(control).resolve()
    root = Path(addon.__file__).resolve().parent
    working = Path(__file__).resolve().parents[1] / 'build/.working'
    if not control.is_relative_to(working.resolve()) or not root.is_relative_to(control):
        raise RuntimeError('Diagnostic hooks require an extension installed inside this owned working directory')
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

    screenshot_path = root / '_vendor/blmcp/tools/get_screenshot_of_window_as_image_toolcode.py'
    screenshot_original = screenshot_path.read_bytes()
    screenshot_text = screenshot_original.decode('utf-8')
    screenshot_newline = '\r\n' if '\r\n' in screenshot_text else '\n'
    start = ('        try:' + screenshot_newline +
             '            bpy.ops.screen.screenshot(filepath=filepath_screenshot)' + screenshot_newline)
    finish = '        data = base64.b64encode(image_data).decode("ascii")' + screenshot_newline
    if screenshot_text.count(start) != 1 or screenshot_text.count(finish) != 1:
        raise RuntimeError('Screenshot observation requires one native screenshot and base64 encoding block')
    begin, end = screenshot_text.index(start), screenshot_text.index(finish) + len(finish)
    if end <= begin:
        raise RuntimeError('Screenshot encoding must follow the native screenshot call')
    original_block = screenshot_text[begin:end]
    error_marker = '        except RuntimeError as ex:' + screenshot_newline
    if original_block.count(error_marker) != 1:
        raise RuntimeError('Screenshot observation requires one native RuntimeError handler')
    block = original_block.replace(error_marker, error_marker +
            '            screenshot_capture["error"] = str(ex)' + screenshot_newline)
    wrapped = ('        from blender_diagnostic_hooks import observe_screenshot' + screenshot_newline +
               '        with observe_screenshot(filepath_screenshot) as screenshot_capture:' + screenshot_newline +
               ''.join('    ' + line if line.strip() else line for line in block.splitlines(keepends=True)) +
               '            screenshot_capture["image_data"] = image_data' + screenshot_newline)
    screenshot_patched = screenshot_text[:begin] + wrapped + screenshot_text[end:]
    compile(patched, str(path), 'exec')
    compile(screenshot_patched, str(screenshot_path), 'exec')
    shutil.copyfile(__file__, root / '_vendor/mcp_diagnostic_hooks.py')
    path.write_bytes(patched.encode('utf-8'))
    screenshot_path.write_bytes(screenshot_patched.encode('utf-8'))
    destination = control / 'diagnostic/blender.log'
    destination.parent.mkdir()
    _SCREENSHOT_DIRECTORY = destination.parent
    _SCREENSHOT_RECORDS = []
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
            'instrumented_server_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'original_screenshot_toolcode_sha256': hashlib.sha256(screenshot_original).hexdigest(),
            'instrumented_screenshot_toolcode_sha256': hashlib.sha256(screenshot_path.read_bytes()).hexdigest(),
            'screenshot_observation': str(_SCREENSHOT_DIRECTORY / 'screenshots.json')}
