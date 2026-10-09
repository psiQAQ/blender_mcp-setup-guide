import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from test_index_sync import host


class IndexSyncCaptureTests(unittest.TestCase):
    def test_native_error_stops_before_reading_the_missing_installed_manifest(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'build/.working') as temporary:
            control = Path(temporary)
            repository = SimpleNamespace(directory=str(control / 'uninstalled'))
            class Repositories(list):
                def new(self, **unused):
                    self.append(repository)
                    return repository
            error = 'Failed to rename directory: [WinError 5] Access denied'
            def messages(*unused, **kwargs):
                yield [('ERROR', error)]
            utilities = SimpleNamespace(command_output_from_json_0=messages,
                                        blender_ext_cmd=lambda python_args: ['native-installer'])
            def install(**unused):
                list(utilities.command_output_from_json_0([], python_args=[]))
                return {'FINISHED'}
            bpy = SimpleNamespace(app=SimpleNamespace(python_args=[]),
                context=SimpleNamespace(preferences=SimpleNamespace(system=SimpleNamespace(),
                    extensions=SimpleNamespace(repos=Repositories()))),
                ops=SimpleNamespace(extensions=SimpleNamespace(repo_sync=lambda **unused: {'FINISHED'},
                                                               package_install=install)))
            package = SimpleNamespace(bl_extension_utils=utilities,
                                      repo_stats_calc_outdated_for_repo_directory=lambda *unused: 0)
            with patch.dict(sys.modules, {'bpy': bpy, 'bl_pkg': package}), \
                    patch.dict(os.environ, BLENDER_USER_CONFIG=str(control / 'profile/config')):
                sys.modules.pop('native_install_capture', None)
                with self.assertRaisesRegex(RuntimeError, 'Native extension installation failed:.*WinError 5'):
                    host('https://example.com/index.json', control / 'result.json', 'http://127.0.0.1/index.json')
            trace = json.loads((control / 'native-install.json').read_bytes())
            self.assertEqual(trace['messages'], [['ERROR', error]])
            self.assertFalse((control / 'result.json').exists())
