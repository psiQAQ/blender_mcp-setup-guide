import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from pages_site import compose, validate_index, verify_retained


class PagesSiteTests(unittest.TestCase):
    def channel(self, path):
        preview = path.endswith("preview")
        line = "5.2" if path else "5.1"
        version = "1.0.2-dev.1+integration.1" if preview else "1.0.3+integration.1"
        platforms = ("windows-x64", "linux-x64", "macos-arm64")
        packages = {p: dict(sha256="a" * 64, size=12, archive_url=f"https://example.com/{p}.zip") for p in platforms}
        record = dict(extension_version=version, packages=packages)
        if path:
            record.update(channel="preview" if preview else "stable", blender_min=line + ".0", blender_max="5.3.0")
        index = dict(data=[dict(platforms=[p], version=version, archive_hash="sha256:" + "a" * 64,
                                archive_size=12, archive_url=packages[p]["archive_url"],
                                blender_version_min=line + ".0", blender_version_max="5.3.0" if path else "5.2.0") for p in platforms])
        return {"publication.json": json.dumps(record).encode(), "index.json": json.dumps(index).encode(), "index.html": b"Published channel\r\n"}

    def test_preview_deployment_preserves_legacy_stable_bytes_and_checks_assets(self):
        stable, preview = self.channel(""), self.channel("blender-5.2/preview")
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            candidate = directory / "candidate"
            candidate.mkdir()
            for name, content in preview.items():
                (candidate / name).write_bytes(content)
            def fetch(base, path, optional=False):
                return stable.get(path)
            with patch("pages_site.read_bytes", side_effect=fetch), patch("pages_site.verify_download") as readback:
                compose("https://example.com", candidate, directory / "site")
                for name, content in stable.items():
                    self.assertEqual((directory / "site" / name).read_bytes(), content)
                verify_retained("https://example.com", directory / "site")
                self.assertEqual(readback.call_count, 6)
            with patch("pages_site.read_bytes", return_value=b"changed"):
                with self.assertRaisesRegex(ValueError, "Retained channel changed"):
                    verify_retained("https://example.com", directory / "site")

    def test_index_cannot_claim_another_channel(self):
        stable = self.channel("")
        with self.assertRaisesRegex(ValueError, "wrong channel"):
            validate_index(stable["index.json"], stable["publication.json"], "blender-5.2/preview")
