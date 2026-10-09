"""Compare real image content and HTTP/SDK response timing in isolated Blender."""

import argparse
import asyncio
import base64
import ctypes
import hashlib
import json
import os
import shutil
import subprocess
import time
import traceback
from datetime import timedelta
from pathlib import Path

from build_cache import LATEST, current_work
from check_reports import run_check, write_json
from mcp_checks import SDK_READ_TIMEOUT
from platforms import process_options
from publication import digest
from test_gui import wait_result
from test_integration import ROOT, free_port, initialize_client_runtime
from test_mcp_tools import image_details, unwrap


class OwnedWindow:
    def __init__(self, pid, include_hidden=False):
        from ctypes import wintypes
        self.api = ctypes.WinDLL('user32', use_last_error=True)
        self.api.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
        self.api.IsWindowVisible.argtypes = [wintypes.HWND]
        self.api.IsIconic.argtypes = [wintypes.HWND]
        self.api.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
        self.api.GetForegroundWindow.restype = wintypes.HWND
        self.api.GetWindowTextLengthW.argtypes = [wintypes.HWND]
        self.pid = pid
        windows = []
        callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

        def visit(hwnd, unused):
            owner = wintypes.DWORD()
            self.api.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
            if owner.value == pid and self.api.GetWindowTextLengthW(hwnd) and (
                    include_hidden or self.api.IsWindowVisible(hwnd)):
                windows.append(hwnd)
            return True

        self.api.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
        self.api.EnumWindows(callback_type(visit), 0)
        if not windows:
            raise RuntimeError(f'No visible owned Blender window for PID {pid}')
        self.hwnd = windows[0]

    def state(self):
        from ctypes import wintypes
        owner = wintypes.DWORD()
        self.api.GetWindowThreadProcessId(self.hwnd, ctypes.byref(owner))
        if owner.value != self.pid:
            raise RuntimeError('Owned diagnostic window changed process')
        return {'visible': bool(self.api.IsWindowVisible(self.hwnd)),
                'minimized': bool(self.api.IsIconic(self.hwnd)),
                'foreground': self.api.GetForegroundWindow() == self.hwnd}

    def show(self, command):
        self.state()
        self.api.ShowWindow(self.hwnd, command)


async def audit(connection, run, report, path, rounds, window, http_read_timeout,
                skip_window_matrix, multi_window):
    import httpx
    from mcp import ClientSession
    from mcp.client.streamable_http import streamable_http_client

    exchanges = report['http_exchanges'] = []
    report['calls'] = []
    report['screenshots'] = []

    class TracedStream(httpx.AsyncByteStream):
        def __init__(self, stream, row):
            self.stream, self.row = stream, row

        async def __aiter__(self):
            pending = b''
            try:
                async for chunk in self.stream:
                    self.row.setdefault('first_chunk_at', time.time())
                    self.row['bytes'] += len(chunk)
                    pending = (pending + chunk).replace(b'\r\n', b'\n')
                    while b'\n\n' in pending:
                        frame, pending = pending.split(b'\n\n', 1)
                        data = b'\n'.join(line[5:].lstrip() for line in frame.splitlines()
                                          if line.startswith(b'data:'))
                        if data:
                            message = json.loads(data)
                            self.row.setdefault('message_ids', []).append(message.get('id'))
                    if len(pending) > 16 * 1024 * 1024:
                        raise RuntimeError('Diagnostic SSE frame exceeded 16 MiB')
                    yield chunk
                self.row['eof_observed'] = True
            except BaseException as error:
                self.row['stream_error'] = type(error).__name__
                raise
            finally:
                self.row['stream_end_at'] = time.time()

        async def aclose(self):
            await self.stream.aclose()

    async def response_hook(response):
        request = response.request
        body = json.loads(request.content) if request.method == 'POST' else {}
        row = {'method': request.method, 'rpc_id': body.get('id'),
               'rpc_method': body.get('method'),
               'tool': body.get('params', {}).get('name'),
               'headers_at': time.time(), 'http_status': response.status_code,
               'content_type': response.headers.get('content-type'),
               'bytes': 0, 'eof_observed': False,
               'stream_note': 'SDK may close SSE immediately after its response; EOF is not required'}
        exchanges.append(row)
        response.stream = TracedStream(response.stream, row)

    async with httpx.AsyncClient(headers={'Authorization': f"Bearer {connection['token']}"},
            timeout=httpx.Timeout(5.0, read=http_read_timeout), trust_env=False,
            event_hooks={'response': [response_hook]}) as http:
        async with streamable_http_client(f"http://127.0.0.1:{connection['http_port']}/",
                                           http_client=http) as (read, write, _):
            async with ClientSession(read, write, read_timeout_seconds=SDK_READ_TIMEOUT) as session:
                await session.initialize()
                state = unwrap(await session.call_tool('execute_blender_code', {'code':
                    "import bpy,platform\nresult={'version':bpy.app.version_string,"
                    "'binary':bpy.app.binary_path,'platform':platform.system(),"
                    "'engine':bpy.context.scene.render.engine}"}))
                report['runtime_query'] = state
                report['artifact_replays'] = []
                for name in ('window.png', 'window-recheck.png'):
                    artifact = LATEST / 'evidence/live-mcp-tools' / name
                    if artifact.exists():
                        row = {'path': str(artifact), 'sha256': digest(artifact)}
                        try:
                            row.update(await image_details(session, artifact))
                            row['black_image_reproduced'] = False
                        except AssertionError as error:
                            row.update(black_image_reproduced=True, evidence=str(error))
                        report['artifact_replays'].append(row)

                async def call(name, arguments, phase):
                    row = {'tool': name, 'phase': phase, 'started_at': time.time(), 'status': 'Not Run'}
                    report['calls'].append(row)
                    started = time.perf_counter()
                    try:
                        response = await session.call_tool(name, arguments)
                        assert not response.isError, [x.text for x in response.content if x.type == 'text']
                        row['status'] = 'Passed'
                        return response
                    except Exception as error:
                        row.update(status='Failed', error=f'{type(error).__name__}: {error}',
                                   traceback=traceback.format_exc())
                        return None
                    finally:
                        row['seconds'] = round(time.perf_counter() - started, 6)
                        row['finished_at'] = time.time()
                        write_json(path, report)
                        print(f"{phase}: {name}: {row['status']} ({row['seconds']}s)", flush=True)

                async def save_capture(response, phase):
                    row = {'phase': phase, 'window_state': window.state(), 'status': 'Not Run'}
                    report['screenshots'].append(row)
                    if response is None:
                        row['status'] = 'Failed'
                        return
                    image = next(x for x in response.content if x.type == 'image')
                    raw = base64.b64decode(image.data, validate=True)
                    png = run / f'{phase}.png'
                    png.write_bytes(raw)
                    row.update(path=str(png), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
                    try:
                        row.update(await image_details(session, png))
                        row['status'] = 'Passed'
                    except Exception as error:
                        row.update(status='Failed', error=str(error))

                async def capture(phase):
                    response = await call('get_screenshot_of_window_as_image', {}, phase)
                    await save_capture(response, phase)

                # The historical ten-tool ordering, including an image and an API
                # member miss before search, stays in one live SDK session.
                for number in range(rounds):
                    for name, arguments in [
                        ('get_objects_summary', {}),
                        ('get_object_detail_summary', {'name': 'Cube'}),
                        ('get_blendfile_summary_datablocks', {}),
                        ('get_screenshot_of_window_as_json', {}),
                        ('get_screenshot_of_window_as_image', {}),
                        ('get_python_api_docs', {'identifier': 'bpy.types.Object.location'}),
                        ('search_api_docs', {'query': 'primitive_cube_add', 'max_results': 3}),
                        ('execute_blender_code', {'code': f"result={{'sequence':{number}}}"}),
                        ('execute_blender_code_for_cli', {'blend_file': connection['blend_file'],
                            'code': "import bpy\nresult={'binary':bpy.app.binary_path,'background':bpy.app.background}"}),
                        ('render_thumbnail_to_path', {'output_path': f'timing-thumbnail-{number}.png'}),
                    ]:
                        response = await call(name, arguments, f'historical-order-{number + 1}')
                        if response is not None and name == 'get_screenshot_of_window_as_image':
                            await save_capture(response, f'historical-order-{number + 1}')
                        if response is not None and name.startswith('search_'):
                            assert unwrap(response)['hits']
                        if response is not None and name == 'render_thumbnail_to_path':
                            value = unwrap(response)
                            report.setdefault('thumbnail_responses', []).append(value)
                    response = await call('execute_blender_code', {'code':
                        "import bpy,os\n"
                        f"p=os.path.join(bpy.app.tempdir,'blender_mcp','timing-thumbnail-{number}.png')\n"
                        "result={'path':p,'exists':os.path.isfile(p),'render_running':bpy.app.is_job_running('RENDER')}"},
                        f'output-observation-{number + 1}')
                    if response is not None:
                        observed = unwrap(response)
                        if observed['exists']:
                            output = run / f'timing-thumbnail-{number}.png'
                            shutil.copyfile(observed['path'], output)
                            observed.update(path=str(output), bytes=output.stat().st_size, sha256=digest(output))
                        report.setdefault('thumbnail_outputs', []).append(observed)

                if multi_window:
                    for operation, phase in [('bpy.ops.wm.window_new()', 'two-main-windows'),
                                             ('bpy.ops.screen.userpref_show()', 'with-preferences-window'),
                                             ("bpy.ops.render.view_show('INVOKE_DEFAULT')", 'with-render-window')]:
                        await call('execute_blender_code', {'code':
                            f"import bpy\n{operation}\nresult={{'windows':len(bpy.context.window_manager.windows)}}"}, phase)
                        await asyncio.sleep(0.5)
                        await capture(phase)
                    await call('execute_blender_code', {'code':
                        "import bpy\n"
                        "for w in bpy.context.window_manager.windows:\n"
                        "    with bpy.context.temp_override(window=w):\n"
                        "        bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP',iterations=2)\n"
                        "result={'windows':len(bpy.context.window_manager.windows)}"}, 'redraw-all-windows')
                    await capture('multi-window-redrawn')

                if skip_window_matrix:
                    return
                for phase, command in [('normal', 4), ('minimized', 6), ('restored', 9),
                                       ('maximized', 3), ('hidden', 0), ('shown', 4)]:
                    window.show(command)
                    await asyncio.sleep(0.5)
                    await capture(phase)
                    # A direct Blender screenshot bypasses the MCP image tool's
                    # PNG encoder/downscaler, but uses the same host framebuffer.
                    direct = run / f'{phase}-direct.png'
                    response = await call('execute_blender_code', {'code':
                        f"import bpy\nbpy.ops.screen.screenshot(filepath={str(direct)!r})\nresult={{'saved':True}}"},
                        phase + '-direct')
                    if response is not None and direct.is_file():
                        row = {'phase': phase + '-direct', 'path': str(direct),
                               'window_state': window.state()}
                        try:
                            row.update(await image_details(session, direct))
                            row['status'] = 'Passed'
                        except Exception as error:
                            row.update(status='Failed', error=str(error))
                        report['screenshots'].append(row)
                window.show(9)
                await asyncio.sleep(0.5)
                await capture('final-restored')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--blender', type=Path, required=True)
    parser.add_argument('--package', type=Path, required=True)
    parser.add_argument('--label', required=True)
    parser.add_argument('--rounds', type=int, default=2)
    parser.add_argument('--historical-scene', action='store_true')
    parser.add_argument('--gpu-backend', choices=('opengl', 'vulkan'), default='opengl')
    parser.add_argument('--http-read-timeout', type=float, default=60)
    parser.add_argument('--skip-window-matrix', action='store_true')
    parser.add_argument('--multi-window', action='store_true')
    parser.add_argument('--render-samples', type=int)
    parser.add_argument('--skip-initial-redraw', action='store_true')
    args = parser.parse_args()
    if os.name != 'nt':
        parser.error('Owned-window state comparisons currently require Windows')
    if args.rounds < 1 or args.http_read_timeout <= 0:
        parser.error('rounds and HTTP read timeout must be positive')
    if args.render_samples is not None and (not args.historical_scene or args.render_samples < 1):
        parser.error('render-samples requires historical-scene and a positive sample count')
    run = current_work('mcp-response-diagnosis')
    report_path = LATEST / f'mcp-response-{args.label}-tests.json'
    report = {'status': 'Not Run', 'package_sha256': digest(args.package),
              'human_gui_acceptance': 'Not Run', 'diagnosis_complete': False,
              'call_scope': 'response delivery and isError only; full tool semantics use test_mcp_tools.py',
              'gpu_backend': args.gpu_backend,
              'http_read_timeout_seconds': args.http_read_timeout,
              'sdk_timeout_seconds': SDK_READ_TIMEOUT.total_seconds(),
              'diagnostic_driver_sha256': digest(Path(__file__)),
              'initial_redraw_forced': not args.skip_initial_redraw,
              'scene_profile': 'historical' if args.historical_scene else 'standard fixture'}
    if args.historical_scene:
        previous = json.loads((LATEST / 'live-mcp-tools-tests.json').read_text(encoding='utf-8'))['before']
        settings = {'render': {key: value for key, value in previous['render'].items() if key != 'filepath'},
                    'cycles_samples': previous['cycles_samples']}
        if args.render_samples is not None:
            settings['render']['engine'] = 'CYCLES'
            settings['cycles_samples'] = args.render_samples
        report['scene_settings'] = settings
        write_json(run / 'scene-profile.json', settings)
    write_json(report_path, report)
    environment = {**os.environ, 'BLENDER_USER_RESOURCES': str(run / 'profile'),
                   'PYTHONDONTWRITEBYTECODE': '1'}
    with (run / 'blender.log').open('w', encoding='utf-8') as log:
        process = subprocess.Popen([str(args.blender), '--gpu-backend', args.gpu_backend,
            '--factory-startup', '--python-exit-code', '1',
            '--python', str(ROOT / 'tests/blender_tools_host.py'), '--', str(args.package.resolve()),
            str(run), str(free_port()), str(free_port()), 'diagnostic',
            *(['skip-initial-redraw'] if args.skip_initial_redraw else [])], env=environment,
            stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, **process_options(gui=True))
        try:
            wait_result(run / 'service.json', run, process)
            connection = json.loads((run / 'service.json').read_text())
            report['host'] = json.loads((run / 'host.json').read_text())
            initialize_client_runtime(args.package, run / 'client')
            window = OwnedWindow(process.pid)
            asyncio.run(audit(connection, run, report, report_path, args.rounds, window,
                              args.http_read_timeout, args.skip_window_matrix, args.multi_window))
            report['diagnosis_complete'] = True
            report['status'] = 'Failed' if any(row['status'] == 'Failed' for row in
                    [*report['calls'], *report['screenshots']]) else 'Passed'
        except Exception as error:
            report.update(status='Failed', error=f'{type(error).__name__}: {error}', traceback=traceback.format_exc())
        finally:
            (run / 'stop').touch()
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.terminate()
                process.wait(timeout=10)
            report['host_exit_code'] = process.returncode
            report['render_events'] = [json.loads(line) for line in
                (run / 'diagnostic/blender.log').read_text().splitlines()] if (run / 'diagnostic/blender.log').exists() else []
            # Only diagnostic metadata is retained; bearer tokens and request
            # headers are never exported to the report.
            report['server_events'] = []
            for service_log in (run / 'profile').rglob('service.log'):
                for line in service_log.read_text(encoding='utf-8', errors='replace').splitlines():
                    if line.startswith('[MCP-DIAG] '):
                        report['server_events'].append(json.loads(line[len('[MCP-DIAG] '):]))
            if (run / 'native-install.json').exists():
                report['native_install'] = json.loads((run / 'native-install.json').read_text())
            write_json(report_path, report)
    print(json.dumps({'status': report['status'], 'report': str(report_path),
                      'calls': len(report.get('calls', []))}), flush=True)
    if report['status'] != 'Passed':
        raise SystemExit(1)


if __name__ == '__main__':
    import sys
    label = sys.argv[sys.argv.index('--label') + 1]
    run_check(f'mcp-response-{label}', main)
