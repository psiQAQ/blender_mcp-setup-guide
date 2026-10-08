import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from test_repository import select_package


class UnifiedSelectionTests(unittest.TestCase):
    def test_release_lines_select_their_package_and_maximum_is_exclusive(self):
        index = {'data': [{'platforms': [platform], 'blender_version_min': f'5.{line}.0', 'blender_version_max': f'5.{line + 1}.0', 'version': str(line)}
                          for line in (1, 2) for platform in ('windows-x64', 'linux-x64', 'macos-arm64')]}
        for line in (1, 2):
            for platform in ('windows-x64', 'linux-x64', 'macos-arm64'):
                self.assertEqual(select_package(index, platform, (5, line, 2))['version'], str(line))
        with self.assertRaises(ValueError):
            select_package(index, 'windows-x64', (5, 3, 0))
        index['data'].append(index['data'][0])
        with self.assertRaises(ValueError):
            select_package(index, 'windows-x64', (5, 1, 1))
