import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from publish_release import find_release, publish_assets


class PublishReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        directory = Path(self.temporary.name)
        self.assets = (directory / "package.zip", directory / "package.zip.sha256")
        for path in self.assets:
            path.write_bytes(path.name.encode())
        self.notes = directory / "notes.md"
        self.notes.write_text("Validated publication")
        self.commit = "a" * 40
        self.marker = "<!-- validated CI source -->"

    def draft(self, assets):
        return {
            "id": 123, "tag_name": "v1.0.3+integration.1", "draft": True, "prerelease": False,
            "body": self.marker, "target_commitish": self.commit,
            "assets": [{"id": index + 1, "name": path.name} for index, path in enumerate(assets)],
        }

    def publish(self):
        return publish_assets("owner/repo", "v1.0.3+integration.1", self.commit,
                              self.assets, self.notes, self.marker, "test-token")

    def test_partial_owned_draft_only_uploads_missing_assets_then_publishes(self):
        events = []
        with patch("publish_release.find_release", return_value=self.draft(self.assets[:1])), \
                patch("publish_release.github_json", return_value=self.draft(self.assets)) as api, \
                patch("publish_release.subprocess.run", side_effect=lambda command, **kwargs: events.append(("gh", command))), \
                patch("publish_release.verify_download", side_effect=lambda url, *args, **kwargs: events.append(("read", url, kwargs))):
            archive_url = self.publish()
        commands = [event[1] for event in events if event[0] == "gh"]
        self.assertEqual(commands[0][:3], ["gh", "release", "upload"])
        self.assertEqual(commands[0][-1], str(self.assets[1]))
        self.assertNotIn(str(self.assets[0]), commands[0])
        self.assertIn("--draft=false", commands[1])
        self.assertEqual(api.call_args.args[1], "releases/123")
        edit = next(index for index, event in enumerate(events) if event[0] == "gh" and "edit" in event[1])
        for event in events[:edit]:
            if event[0] == "read":
                self.assertTrue(event[1].startswith("https://api.github.com/"))
                self.assertEqual(event[2]["headers"]["Authorization"], "Bearer test-token")
        self.assertEqual(len(events[edit + 1:]), len(self.assets))
        self.assertTrue(all(event[1].startswith("https://github.com/") and not event[2] for event in events[edit + 1:]))
        self.assertTrue(archive_url.endswith("/package.zip"))

    def test_new_release_is_explicitly_created_as_a_draft(self):
        with patch("publish_release.find_release", side_effect=[None, self.draft(())]), \
                patch("publish_release.github_json", return_value=self.draft(self.assets)), \
                patch("publish_release.subprocess.run") as command, patch("publish_release.verify_download"):
            self.publish()
        create = command.call_args_list[0].args[0]
        self.assertEqual(create[:3], ["gh", "release", "create"])
        self.assertIn("--draft", create)
        self.assertEqual(create[create.index("--target") + 1], self.commit)
        self.assertNotIn(str(self.assets[0]), create)

    def test_staging_reads_every_asset_without_publishing(self):
        with patch("publish_release.find_release", return_value=self.draft(self.assets)), patch("publish_release.subprocess.run") as command, patch("publish_release.verify_download") as readback:
            publish_assets("owner/repo", "v1.0.3+integration.1", self.commit, self.assets, self.notes, self.marker, "test-token", finalize=False)
        command.assert_not_called()
        self.assertEqual(readback.call_count, len(self.assets) * 2)

    def test_unrelated_draft_is_rejected_before_any_remote_mutation(self):
        for change in ({"body": "Other publisher"}, {"target_commitish": "b" * 40}):
            draft = self.draft(self.assets)
            draft.update(change)
            with self.subTest(change=change), patch("publish_release.find_release", return_value=draft), \
                    patch("publish_release.subprocess.run") as command, patch("publish_release.verify_download") as readback:
                with self.assertRaisesRegex(ValueError, "does not belong"):
                    self.publish()
                command.assert_not_called()
                readback.assert_not_called()

    def test_corrupt_existing_asset_blocks_upload_and_publication(self):
        with patch("publish_release.find_release", return_value=self.draft(self.assets[:1])), \
                patch("publish_release.subprocess.run") as command, \
                patch("publish_release.verify_download", side_effect=ValueError("SHA-256 differs")):
            with self.assertRaisesRegex(ValueError, "SHA-256 differs"):
                self.publish()
            command.assert_not_called()

    def test_draft_lookup_pages_the_list_when_published_tag_endpoint_returns_404(self):
        draft = self.draft(self.assets)
        first_page = [{"tag_name": f"other-{index}"} for index in range(100)]
        with patch("publish_release.github_json", side_effect=[None, first_page, [draft]]) as api:
            self.assertEqual(find_release("owner/repo", draft["tag_name"], "test-token"), draft)
        self.assertTrue(api.call_args_list[0].kwargs["allow_missing"])
        self.assertEqual([call.args[1] for call in api.call_args_list[1:]],
                         ["releases?per_page=100&page=1", "releases?per_page=100&page=2"])


if __name__ == "__main__":
    unittest.main()
