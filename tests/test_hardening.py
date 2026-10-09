import json
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import check_reports
import platforms
import test_repository
import build_integration
from test_upgrade import previous_fixture, previous_release
from upstream_sync import inspect
from integration_build_runtime.private_files import normalize_windows_dacl, persistent_token, private_directory, windows_dacl, windows_user_sid, write_private


class HardeningTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)

    def test_credentials_are_private_and_old_token_is_preserved(self):
        directory = private_directory(self.directory / "service")
        token_path = directory / "http-token.txt"
        token_path.write_text("a" * 43)
        token = persistent_token(token_path)
        self.assertEqual(token, "a" * 43)
        config = directory / "client-config.txt"
        write_private(config, "old")
        write_private(config, "current")
        self.assertEqual(config.read_text(), "current")
        self.assertEqual(list(directory.glob("*.pending")), [])
        if os.name == "nt":
            sid = windows_user_sid()
            self.assertEqual(normalize_windows_dacl(windows_dacl(directory)), normalize_windows_dacl(f"D:P(A;OICI;FA;;;SY)(A;OICI;FA;;;BA)(A;OICI;FA;;;{sid})"))
            for path in (token_path, config):
                self.assertEqual(normalize_windows_dacl(windows_dacl(path)), normalize_windows_dacl(f"D:P(A;;FA;;;SY)(A;;FA;;;BA)(A;;FA;;;{sid})"))
        else:
            self.assertEqual(directory.stat().st_mode & 0o777, 0o700)
            for path in (token_path, config):
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    @unittest.skipUnless(os.name == "nt", "Windows security descriptors")
    def test_windows_acl_aliases_preserve_protection_and_permissions(self):
        expected = normalize_windows_dacl("D:P(A;;FA;;;SY)")
        self.assertEqual(normalize_windows_dacl("D:PAI(A;;FA;;;S-1-5-18)"), expected)
        for changed in ("D:(A;;FA;;;SY)", "D:P(A;;FR;;;SY)", "D:P(A;;FA;;;SY)(A;;FA;;;WD)", "D:P(A;ID;FA;;;SY)"):
            self.assertNotEqual(normalize_windows_dacl(changed), expected)

    def test_failed_public_install_replaces_old_passed_report(self):
        build = self.directory / "build/latest"
        build.mkdir(parents=True)
        report = build / "published-tests.json"
        report.write_text('{"status": "Passed"}')
        with patch.object(check_reports, "LATEST", build), patch("build_cache.LATEST", build), patch("build_cache.BUILD", self.directory / "build"), patch.object(test_repository, "main", side_effect=RuntimeError("Install failed")):
            with self.assertRaisesRegex(RuntimeError, "Install failed"):
                test_repository.run(["--blender", "unused", "--artifacts", "unused", "--public-index", "https://example.invalid/index.json"])
        result = json.loads(report.read_text())
        self.assertEqual(result["status"], "Failed")
        self.assertIn("Install failed", result["error"])
        self.assertFalse((build / "repository-tests.json").exists())

    def test_retry_retains_the_previous_failure_and_its_log(self):
        build = self.directory / "build/latest"
        log = build / "evidence/native/blender.log"
        log.parent.mkdir(parents=True)
        log.write_text("Original installation error")
        report = build / "native-tests.json"
        report.write_text(json.dumps({"status": "Failed", "package_sha256": "a" * 64,
                                      "checks": {"installation": "Failed"}}))
        with patch.object(check_reports, "LATEST", build):
            check_reports.preserve_failure("native", report)
            check_reports.preserve_failure("native", report)
        saved = list((build / "evidence/failed-checks/native").glob("*/report.json"))
        self.assertEqual(len(saved), 1)
        self.assertEqual(json.loads(saved[0].read_text())["checks"]["installation"], "Failed")
        self.assertEqual((saved[0].parent / "diagnostics/blender.log").read_text(), "Original installation error")

    def test_child_failure_preserves_package_and_completed_checks(self):
        build = self.directory / "build/latest"
        work = self.directory / "build/.working/native"
        build.mkdir(parents=True)
        work.mkdir(parents=True)
        report = build / "native-tests.json"
        def fail():
            check_reports.write_json(report, {"status": "Failed", "package_sha256": "a" * 64,
                                              "checks": {"first": "Passed"}})
            raise RuntimeError("Native installation failed")
        with patch.object(check_reports, "LATEST", build), patch("build_cache.BUILD", self.directory / "build"), patch.dict(os.environ, BLENDER_MCP_CHECK_WORK=str(work)):
            with self.assertRaisesRegex(RuntimeError, "Native installation failed"):
                check_reports.run_check("native", fail)
        self.assertEqual(json.loads(report.read_text())["package_sha256"], "a" * 64)
        self.assertEqual(json.loads(report.read_text())["checks"], {"first": "Passed"})

    def package(self, version):
        record = dict(version=version, channel="preview", preview_revision=1, integration_revision=1,
                      extension_version=f"{version}-dev.1+integration.1", blender_min="5.2.0", blender_max="5.3.0", platform="windows-x64")
        path = self.directory / f"{version}.zip"
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("provenance.json", json.dumps(record))
            archive.writestr("blender_manifest.toml", f'version = "{record["extension_version"]}"\n')
        return path

    def test_first_preview_fixture_supports_zero_patch_versions(self):
        for version in ("1.1.0", "2.0.0"):
            path = self.package(version)
            previous = self.directory / f"{version}-previous.zip"
            previous_fixture(path, previous)
            with zipfile.ZipFile(previous) as archive:
                source = json.loads(archive.read("provenance.json"))
            self.assertEqual(source["extension_version"], "0.0.0-dev.1+integration.0")
            self.assertIn("Synthetic", source["upgrade_fixture"])

    def test_previous_package_must_match_locked_hash(self):
        candidate = self.package("1.1.0")
        baselines = self.directory / "baselines.json"
        baselines.write_text(json.dumps({"blender-5.2/preview": {
            "extension_version": "1.0.0-dev.1+integration.1", "packages": {"windows-x64": {
                "archive_url": "https://example.invalid/previous.zip", "sha256": "0" * 64, "size": candidate.stat().st_size,
            }},
        }}))
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            previous_release(candidate, self.directory / "old.zip", baselines, local=candidate)

    def test_preview_monitor_detects_moved_stable_baseline_with_newer_tag(self):
        pinned = dict(tag=None, source_ref="main", commit="a" * 40,
                      stable_baseline_tag="v1.0.3", stable_baseline_commit="b" * 40)
        release = dict(tag_name="v1.0.4", html_url="https://example.invalid", published_at="2026-10-08")
        with self.assertRaisesRegex(ValueError, "baseline tag moved"):
            inspect(pinned, release, "c" * 40, "a" * 40, "d" * 40)
        result = inspect(pinned, release, "c" * 40, "a" * 40, "b" * 40)
        self.assertTrue(result["new_stable_tag"])
        self.assertFalse(result["main_changed"])

    def test_service_requires_explicit_host_binary(self):
        with patch.object(platforms.runtime, "check_runtime"), patch.object(platforms.runtime, "require_free_port"):
            with self.assertRaisesRegex(platforms.runtime.ServiceError, "host Blender"):
                platforms.runtime.Service().start(self.directory, 8123, 9876)

    def test_candidate_replacement_preserves_other_release_line_evidence(self):
        for name, checksum in (("replaced", "old"), ("stable", "stable"), ("current", "new")):
            (self.directory / f"{name}-tests.json").write_text(json.dumps({"status": "Passed", "package_sha256": checksum}))
        with patch.object(build_integration, "LATEST", self.directory):
            build_integration.invalidate_candidate_reports({"old"}, "new")
        self.assertEqual(json.loads((self.directory / "replaced-tests.json").read_text())["status"], "Not Run")
        for name in ("stable", "current"):
            self.assertEqual(json.loads((self.directory / f"{name}-tests.json").read_text())["status"], "Passed")


if __name__ == "__main__":
    unittest.main()
