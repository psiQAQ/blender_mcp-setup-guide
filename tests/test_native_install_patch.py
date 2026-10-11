"""Check deployment byte and validation guards using owned fixture files only."""

import hashlib
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import apply_native_install_fix as apply_fix


class NativeInstallPatchTests(unittest.TestCase):
    def setUp(self):
        working = ROOT / "build/.working"
        working.mkdir(parents=True, exist_ok=True)
        temporary = tempfile.TemporaryDirectory(prefix="native-install-patch-", dir=working)
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.latest = self.root / "latest"
        self.version = "5.2.2"
        self.bundle = self.latest / "native-install-fix" / f"blender-{self.version}"
        self.bundle.mkdir(parents=True)
        self.target = self.root / "owned-installer.py"
        self.original = b"\xef\xbb\xbf# Original fixture bytes\r\nvalue = 1\r\n"
        self.patched = b"\xef\xbb\xbf# Patched fixture with a longer body\r\nvalue = 2\r\nretry = True\r\n"
        self.original_hash = hashlib.sha256(self.original).hexdigest()
        self.patched_hash = hashlib.sha256(self.patched).hexdigest()
        self.target.write_bytes(self.original)
        (self.bundle / "blender_ext.original.py").write_bytes(self.original)
        (self.bundle / "blender_ext.py").write_bytes(self.patched)
        self.write_json(self.bundle / "manifest.json", {
            "blender_version": self.version,
            "system_installer": str(self.target),
            "original_sha256": self.original_hash,
            "patched_sha256": self.patched_hash,
        })
        self.report_path = self.latest / f"native-install-fix-{self.version}-tests.json"
        self.write_json(self.report_path, self.valid_report())
        for name, value in (("LATEST", self.latest), ("BASELINES", {self.version: self.original_hash})):
            patcher = patch.object(apply_fix, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    @staticmethod
    def write_json(path, value):
        path.write_text(json.dumps(value), encoding="utf-8", newline="\n")

    def valid_report(self):
        return {
            "status": "Passed",
            "blender_version": self.version,
            "installer_sha256": self.patched_hash,
        }

    def invoke(self, action):
        output = io.StringIO()
        with patch.object(sys, "argv", ["apply_native_install_fix", "--version", self.version, "--action", action]), \
                redirect_stdout(output):
            apply_fix.main()
        return json.loads(output.getvalue())

    def test_apply_and_restore_preserve_exact_bytes(self):
        result = self.invoke("apply")
        self.assertEqual(self.target.read_bytes(), self.patched)
        self.assertEqual(result["result_sha256"], self.patched_hash)
        self.assertEqual(result["status"], "Passed")
        self.assertEqual((self.bundle / "blender_ext.original.py").read_bytes(), self.original)
        self.assertEqual(self.invoke("apply")["result_sha256"], self.patched_hash)

        result = self.invoke("restore")
        self.assertEqual(self.target.read_bytes(), self.original)
        self.assertEqual(result["result_sha256"], self.original_hash)
        self.assertEqual(result["status"], "Passed")
        receipt = json.loads((self.bundle / "deployment.json").read_text(encoding="utf-8"))
        self.assertEqual(receipt["action"], "restore")
        self.assertEqual(receipt["result_sha256"], self.original_hash)

    def test_check_does_not_write_installer_or_deployment_receipt(self):
        result = self.invoke("check")
        self.assertEqual(result["current_sha256"], self.original_hash)
        self.assertEqual(self.target.read_bytes(), self.original)
        self.assertFalse((self.bundle / "deployment.json").exists())

    def test_unknown_installer_hash_is_refused_without_modifying_it(self):
        unknown = b"# User changed this fixture\r\nvalue = 99\r\n"
        self.target.write_bytes(unknown)
        for action in ("check", "apply", "restore"):
            with self.subTest(action=action):
                with self.assertRaisesRegex(ValueError, "System installer changed"):
                    self.invoke(action)
                self.assertEqual(self.target.read_bytes(), unknown)
                self.assertFalse((self.bundle / "deployment.json").exists())

    def test_apply_requires_passed_report_for_the_exact_patch(self):
        reports = [
            {**self.valid_report(), "status": "Failed"},
            {**self.valid_report(), "status": "Not Run"},
            {**self.valid_report(), "installer_sha256": self.original_hash},
            {"status": "Passed"},
        ]
        for report in reports:
            with self.subTest(report=report):
                self.write_json(self.report_path, report)
                with self.assertRaisesRegex(ValueError, "Passed validation report"):
                    self.invoke("apply")
                self.assertEqual(self.target.read_bytes(), self.original)
                self.assertFalse((self.bundle / "deployment.json").exists())

    def test_corrupted_backup_or_patch_is_refused_before_writing(self):
        for filename, expected, message in (
            ("blender_ext.original.py", self.original, "Original installer backup"),
            ("blender_ext.py", self.patched, "Patched installer changed"),
        ):
            for action in ("apply", "restore"):
                with self.subTest(filename=filename, action=action):
                    self.target.write_bytes(self.original if action == "apply" else self.patched)
                    before = self.target.read_bytes()
                    path = self.bundle / filename
                    path.write_bytes(expected + b"# Corrupted retained artifact\r\n")
                    try:
                        with self.assertRaisesRegex(ValueError, message):
                            self.invoke(action)
                        self.assertEqual(self.target.read_bytes(), before)
                        self.assertFalse((self.bundle / "deployment.json").exists())
                    finally:
                        path.write_bytes(expected)


if __name__ == "__main__":
    unittest.main()
