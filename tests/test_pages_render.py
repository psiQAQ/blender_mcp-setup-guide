"""Protect release links, historical metadata, localization and subpath hosting."""

import json
import sys
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from pages_render import render_site


class Elements(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.tags = []
        self.feed(source)

    def handle_starttag(self, tag, attributes):
        self.tags.append((tag, dict(attributes)))


class PagesRenderTests(unittest.TestCase):
    def records(self):
        def record(version, **extra):
            return dict(extension_version=version, version=version.split("-")[0].split("+")[0], commit="a" * 40,
                        packages={platform: dict(sha256=str(i) * 64, size=1024 * 1024 * i,
                            archive_url=f"https://github.com/psiQAQ/blender_mcp-setup-guide/releases/download/v{version}/{platform}.zip")
                            for i, platform in enumerate(("windows-x64", "linux-x64", "macos-arm64"), 1)}, **extra)
        return {"": record("1.0.3+integration.1"),
                "blender-5.2/preview": record("1.0.2-dev.1+integration.1", channel="preview", source_ref="main", blender_min="5.2.0", blender_max="5.3.0")}

    def test_localized_pages_expose_exact_downloads_even_without_javascript(self):
        records = self.records()
        with tempfile.TemporaryDirectory() as temporary:
            site = Path(temporary)
            metadata = json.dumps(records[""], indent=4).encode() + b"\r\n"
            (site / "publication.json").write_bytes(metadata)
            render_site(site, records, "https://example.com/project")
            expected = {p["archive_url"] for record in records.values() for p in record["packages"].values()}
            for path, language in (("index.html", "zh-Hans"), ("en/index.html", "en"), ("blender-5.2/preview/index.html", "zh-Hans"), ("blender-5.2/preview/en/index.html", "en")):
                source = (site / path).read_text(encoding="utf-8")
                tags = Elements(source).tags
                self.assertIn(("html", {"lang": language}), tags)
                self.assertEqual({attributes["href"] for tag, attributes in tags if tag == "a" and "download-button" in attributes.get("class", "")}, expected)
                panels = [attributes for tag, attributes in tags if "data-channel-panel" in attributes]
                self.assertEqual(len(panels), 2)
                self.assertTrue(all("hidden" not in attributes for attributes in panels))
                self.assertIn("5.1.0 ≤ Blender &lt; 5.2.0", source)
                self.assertIn("5.2.0 ≤ Blender &lt; 5.3.0", source)
                self.assertNotIn("/releases/latest", source)
                self.assertNotIn("$hero_title", source)
            self.assertEqual((site / "publication.json").read_bytes(), metadata)

    def test_all_local_assets_and_language_links_resolve_under_a_project_subpath(self):
        with tempfile.TemporaryDirectory() as temporary:
            site = Path(temporary)
            render_site(site, self.records(), "https://example.com/project")
            for page in site.rglob("*.html"):
                elements = Elements(page.read_text(encoding="utf-8"))
                ids = [attrs["id"] for _, attrs in elements.tags if "id" in attrs]
                self.assertEqual(len(ids), len(set(ids)), page)
                for tag, attrs in elements.tags:
                    value = attrs.get("src") or attrs.get("href") or attrs.get("data-language-url", "")
                    if not value or urlsplit(value).scheme:
                        continue
                    if value.startswith("#"):
                        self.assertIn(value[1:], ids, page)
                    else:
                        target = (page.parent / unquote(urlsplit(value).path)).resolve()
                        self.assertTrue(target.is_relative_to(site), value)
                        self.assertTrue(target.is_file(), value)
                for _, attrs in elements.tags:
                    if attrs.get("rel") == "canonical":
                        self.assertTrue(attrs["href"].startswith("https://example.com/project/"))

    def test_preview_page_defaults_to_preview_without_guessing_version_order(self):
        with tempfile.TemporaryDirectory() as temporary:
            site = Path(temporary)
            render_site(site, self.records(), "https://example.com/project")
            source = (site / "blender-5.2/preview/index.html").read_text(encoding="utf-8")
            self.assertIn('data-initial-channel="release-blender-5-2-preview"', source)
            self.assertIn('value="https://example.com/project/index.json"', source)
            self.assertIn('href="https://example.com/project/blender-5.2/preview/index.json"', source)
            self.assertIn('href="https://example.com/project/blender-5.1/stable/index.json"', source)

    def test_future_stable_channel_is_separate_from_preview(self):
        records = self.records()
        stable = json.loads(json.dumps(records["blender-5.2/preview"]))
        stable.update(channel="stable", extension_version="1.1.0+integration.1", version="1.1.0", source_ref="v1.1.0")
        records["blender-5.2/stable"] = stable
        with tempfile.TemporaryDirectory() as temporary:
            site = Path(temporary)
            render_site(site, records, "https://example.com/project")
            self.assertTrue((site / "blender-5.2/stable/en/index.html").exists())
            source = (site / "index.html").read_text(encoding="utf-8")
            self.assertEqual(source.count("data-channel-panel"), 3)
            self.assertIn("1.1.0+integration.1", source)
            self.assertIn("1.0.2-dev.1+integration.1", source)

    def test_record_text_is_escaped_and_active_link_schemes_are_rejected(self):
        records = self.records()
        records[""]["extension_version"] = '<script>alert("x")</script>'
        with tempfile.TemporaryDirectory() as temporary:
            site = Path(temporary)
            render_site(site, records, "https://example.com/project")
            source = (site / "index.html").read_text(encoding="utf-8")
            self.assertNotIn('<script>alert("x")</script>', source)
            self.assertIn("&lt;script&gt;", source)
            records[""]["packages"]["windows-x64"]["archive_url"] = "javascript:alert(1)"
            with self.assertRaisesRegex(ValueError, "HTTPS"):
                render_site(site, records, "https://example.com/project")

    def test_no_published_channels_cannot_produce_fake_downloads(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError, "without published channels"):
                render_site(Path(temporary), {}, "https://example.com/project")


if __name__ == "__main__":
    unittest.main()
