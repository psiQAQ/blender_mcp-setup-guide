import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from publication import extension_version, check_forward
from upstream_source import verify_source, channel_path


class ChannelTests(unittest.TestCase):
    def test_preview_sequence_precedes_integration_revision_in_version_order(self):
        first = dict(version="1.0.2", channel="preview", preview_revision=1, integration_revision=8)
        second = dict(first, preview_revision=2, integration_revision=1)
        from publication import version_key
        self.assertGreater(version_key(second), version_key(first))
    def preview(self):
        return dict(version="1.0.2", channel="preview", source_ref="main", tag=None,
                    preview_revision=1, integration_revision=1, commit="a" * 40,
                    repository="https://projects.blender.org/lab/blender_mcp.git",
                    blender_min="5.2.0", blender_max="5.3.0", sha256="same")

    def test_preview_version_and_channel_are_explicit(self):
        record = self.preview()
        self.assertEqual(extension_version(record), "1.0.2-dev.1+integration.1")
        self.assertEqual(channel_path(record), "blender-5.2/preview")
        verify_source(record)
        check_forward(record, {**record, "preview_revision": 2})
        with self.assertRaisesRegex(ValueError, "older"):
            check_forward({**record, "preview_revision": 2}, record)
        with self.assertRaisesRegex(ValueError, "immutable"):
            check_forward(record, {**record, "sha256": "new"})

    def test_main_snapshot_cannot_be_published_as_stable(self):
        with self.assertRaisesRegex(ValueError, "official version tag"):
            verify_source({**self.preview(), "channel": "stable"})

    def test_preview_cannot_replace_legacy_stable_index(self):
        stable = dict(version="1.0.3", integration_revision=1, sha256="stable")
        self.assertEqual(extension_version(stable), "1.0.3+integration.1")
        self.assertEqual(channel_path(stable), "")
        with self.assertRaisesRegex(ValueError, "another release channel"):
            check_forward(stable, self.preview())

    def test_moved_upstream_head_blocks_publication(self):
        with patch("upstream_source.subprocess.check_output", return_value="b" * 40 + "\trefs/heads/main\n"):
            with self.assertRaisesRegex(ValueError, "moved"):
                verify_source(self.preview(), remote=True)
