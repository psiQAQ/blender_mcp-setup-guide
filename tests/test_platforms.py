import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from platforms import records


class PlatformLocksTests(unittest.TestCase):
    def test_platform_wheels_share_versions_and_match_the_python_abi(self):
        versions = []
        for identifier, record in records().items():
            wheels = json.loads((ROOT / "packaging" / record["wheel_lock"]).read_text())
            self.assertEqual(len(wheels), 40 if identifier == "windows-x64" else 39)
            selected = {}
            for wheel in wheels:
                name, version = wheel["filename"].split("-")[:2]
                if name != "pywin32":
                    selected[name] = version
                self.assertEqual(len(wheel["sha256"]), 64)
                filename = wheel["filename"]
                if not filename.endswith("-none-any.whl"):
                    self.assertTrue("-cp313-cp313-" in filename or "-cp311-abi3-" in filename)
                    suffix = {"windows-x64": "win_amd64.whl", "linux-x64": "x86_64.whl", "macos-arm64": "arm64.whl"}[identifier]
                    self.assertTrue(filename.endswith(suffix), filename)
            versions.append(selected)
            for key in ("blender", "minimum_blender"):
                self.assertEqual(len(record[key]["sha256"]), 64)
        self.assertTrue(all(version == versions[0] for version in versions))


if __name__ == "__main__":
    unittest.main()
