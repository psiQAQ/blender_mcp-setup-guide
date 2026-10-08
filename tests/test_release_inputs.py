import hashlib
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from prepare_release import validate_artifacts
from platforms import resolve, package_name
from publication import digest


class ReleaseInputsTests(unittest.TestCase):
    def create_artifacts(self, directory):
        record = json.loads((ROOT / "packaging/upstream.json").read_text())
        identifier, target = resolve()
        record.update(integration_commit="a" * 40, integration_dirty=False, platform=identifier,
                      wheels=json.loads((ROOT / "packaging" / target["wheel_lock"]).read_text()),
                      requirements_sha256=digest(ROOT / "packaging" / target["requirements"]),
                      wheel_lock_sha256=digest(ROOT / "packaging" / target["wheel_lock"]))
        output = directory / "dist"
        output.mkdir()
        version = f"{record['version']}+integration.{record['integration_revision']}"
        package = output / package_name(version, identifier)
        with zipfile.ZipFile(package, "w") as archive:
            archive.writestr("provenance.json", json.dumps(record))
            archive.writestr("blender_manifest.toml", f'id = "blender_mcp_integration"\nversion = "{version}"\nplatforms = ["{identifier}"]\nblender_version_min = "{record["blender_min"]}"\nblender_version_max = "{record["blender_max"]}"\n')
        checksum = hashlib.sha256(package.read_bytes()).hexdigest()
        (output / (package.name + ".sha256")).write_text(f"{checksum}  {package.name}\n")
        (output / f"provenance-{identifier}.json").write_text(json.dumps(record))
        for name in ("unit", "template", "integration", "upgrade", "gui", "minimum", "repository"):
            (directory / f"{name}-tests.json").write_text(json.dumps({"status": "Passed", "package_sha256": checksum, "platform": identifier,
                "details": {"blender": target["minimum_blender" if name == "minimum" else "blender"]["version"], "python": "3.13.13"}}))
        return package

    def test_successful_report_for_another_zip_cannot_authorize_release(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            self.create_artifacts(directory)
            (directory / "gui-tests.json").write_text(json.dumps({"status": "Passed", "package_sha256": "0" * 64, "platform": resolve()[0]}))
            with self.assertRaisesRegex(ValueError, "another ZIP"):
                validate_artifacts(directory)

    def test_failed_check_and_wrong_ci_commit_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            package = self.create_artifacts(directory)
            self.assertEqual(validate_artifacts(directory, "a" * 40)[0], package)
            with self.assertRaisesRegex(ValueError, "exact clean CI commit"):
                validate_artifacts(directory, "b" * 40)
            (directory / "upgrade-tests.json").write_text(json.dumps({"status": "Failed"}))
            with self.assertRaisesRegex(ValueError, "did not pass"):
                validate_artifacts(directory)

    def test_report_from_another_blender_version_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            self.create_artifacts(directory)
            path = directory / "minimum-tests.json"
            record = json.loads(path.read_text())
            record["details"]["blender"] = "4.2.0"
            path.write_text(json.dumps(record))
            with self.assertRaisesRegex(ValueError, "wrong Blender/Python"):
                validate_artifacts(directory)


if __name__ == "__main__":
    unittest.main()
