import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from publication_receipt import PLATFORMS, prepare_receipt, upload_receipt
from publish_release import publish_assets


class PublicationReceiptTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.version = "1.0.2-dev.2+integration.1"
        self.commit = "a" * 40
        self.record = {"extension_version": self.version, "channel": "preview", "integration_commit": self.commit, "packages": {
            platform: {"sha256": str(index) * 64} for index, platform in enumerate(sorted(PLATFORMS), 1)
        }}
        self.publication = self.root / "publication.json"
        self.publication.write_text(json.dumps(self.record))
        self.reports = self.root / "reports"
        for platform in PLATFORMS:
            folder = self.reports / f"publication-{platform}"
            folder.mkdir(parents=True)
            (folder / "published-tests.json").write_text(json.dumps({
                "status": "Passed", "platform": platform, "package_sha256": self.record["packages"][platform]["sha256"],
                "publication_run_id": "123", "integration_commit": self.commit,
            }))

    def prepare(self):
        return prepare_receipt(self.publication, self.reports, self.root / "receipts", "owner/repo", self.commit, "123")

    def test_receipt_preserves_all_reports_and_retries_without_replacing(self):
        receipt = self.prepare()
        original = receipt.read_bytes()
        self.assertEqual(self.prepare().read_bytes(), original)
        with zipfile.ZipFile(receipt) as archive:
            self.assertEqual(len(archive.namelist()), 5)
            record = json.loads(archive.read("receipt.json"))
            self.assertEqual(set(record["packages"]), PLATFORMS)
            self.assertEqual(record["publication_run_id"], "123")
            for platform in PLATFORMS:
                self.assertEqual(archive.read(f"{platform}-published-tests.json"), (self.reports / f"publication-{platform}/published-tests.json").read_bytes())

    def test_failed_wrong_package_and_stale_run_reports_are_rejected(self):
        path = self.reports / "publication-windows-x64/published-tests.json"
        report = json.loads(path.read_text())
        for key, value in (("status", "Failed"), ("package_sha256", "0" * 64), ("publication_run_id", "122"), ("integration_commit", "b" * 40)):
            with self.subTest(key=key):
                path.write_text(json.dumps({**report, key: value}))
                with self.assertRaises(ValueError):
                    self.prepare()
        path.write_text(json.dumps(report))

    def test_changed_receipt_cannot_overwrite_existing_receipt(self):
        receipt = self.prepare()
        path = self.reports / "publication-linux-x64/published-tests.json"
        report = json.loads(path.read_text())
        report["extra"] = "changed"
        path.write_text(json.dumps(report))
        before = receipt.read_bytes()
        with self.assertRaisesRegex(ValueError, "immutable"):
            self.prepare()
        self.assertEqual(receipt.read_bytes(), before)

    def test_existing_remote_receipt_is_read_back_without_upload(self):
        receipt = self.prepare()
        with patch("publication_receipt.verify_tag"), patch("publication_receipt.find_release", return_value={"draft": False, "assets": [{"name": receipt.name}]}), \
                patch("publication_receipt.subprocess.run") as command, patch("publication_receipt.verify_download") as verify:
            upload_receipt("owner/repo", f"v{self.version}", self.commit, receipt, "unit-test-token")
        command.assert_not_called()
        verify.assert_called_once()

    def test_installer_retry_accepts_only_matching_hashed_public_receipts(self):
        installer = self.root / "package.zip"
        installer.write_bytes(b"installer")
        receipt = self.prepare()
        release = {"draft": False, "prerelease": True, "assets": [
            {"name": installer.name}, {"name": receipt.name, "digest": "sha256:" + "c" * 64, "size": receipt.stat().st_size},
        ]}
        with patch("publish_release.find_release", return_value=release), patch("publish_release.verify_download") as readback, patch("publish_release.subprocess.run") as command:
            publish_assets("owner/repo", f"v{self.version}", self.commit, [installer], self.root / "notes.md", "marker", "token", channel="preview")
        command.assert_not_called()
        self.assertEqual(readback.call_count, 3)
        release["assets"][1]["name"] = receipt.name.replace(self.version, "1.0.0")
        with patch("publish_release.find_release", return_value=release):
            with self.assertRaisesRegex(ValueError, "unexpected assets"):
                publish_assets("owner/repo", f"v{self.version}", self.commit, [installer], self.root / "notes.md", "marker", "token", channel="preview")


if __name__ == "__main__":
    unittest.main()
