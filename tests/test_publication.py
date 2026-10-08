import hashlib
import http.server
import importlib.util
import threading
import unittest
from pathlib import Path


SPEC = importlib.util.spec_from_file_location("publication", Path(__file__).resolve().parents[1] / "scripts/publication.py")
publication = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(publication)


class PublicationTests(unittest.TestCase):
    def test_platform_asset_set_is_immutable_for_a_published_version(self):
        current = {"version": "1.0.3", "integration_revision": 1, "packages": {"windows-x64": {"sha256": "same"}, "linux-x64": {"sha256": "same"}, "macos-arm64": {"sha256": "same"}}}
        publication.check_forward(current, dict(current))
        changed = {**current, "packages": {**current["packages"], "linux-x64": {"sha256": "new"}}}
        with self.assertRaisesRegex(ValueError, "immutable"):
            publication.check_forward(current, changed)

    def test_incomplete_platform_set_is_rejected_before_building_an_index(self):
        with self.assertRaisesRegex(ValueError, "all three"):
            publication.prepare_collection("unused-blender", {}, Path("unused-output"))
    def test_revision_order_does_not_use_semver_build_metadata(self):
        current = {"version": "1.0.3", "integration_revision": 2, "sha256": "same"}
        with self.assertRaisesRegex(ValueError, "older"):
            publication.check_forward(current, {**current, "integration_revision": 1})
        publication.check_forward(current, {"version": "1.0.4", "integration_revision": 1, "sha256": "new"})

    def test_identical_version_cannot_be_replaced_with_different_content(self):
        current = {"version": "1.0.3", "integration_revision": 1, "sha256": "original"}
        with self.assertRaisesRegex(ValueError, "immutable"):
            publication.check_forward(current, {**current, "sha256": "altered"})
        publication.check_forward(current, dict(current))

    def test_prerelease_cannot_be_selected_as_stable(self):
        with self.assertRaisesRegex(ValueError, "stable"):
            publication.version_key({"version": "1.0.4-rc.1", "integration_revision": 1})

    def test_authenticated_readback_does_not_forward_credentials_after_redirect(self):
        received = []
        payload = b"validated asset"

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                received.append((self.path, self.headers.get("Authorization")))
                if self.path == "/start":
                    self.send_response(302)
                    self.send_header("Location", f"http://localhost:{self.server.server_port}/asset")
                    self.end_headers()
                else:
                    self.send_response(200)
                    self.send_header("Content-Length", str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)

            def log_message(self, *args):
                pass

        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            publication.verify_download(
                f"http://127.0.0.1:{server.server_port}/start", hashlib.sha256(payload).hexdigest(), len(payload),
                allow_local_http=True, headers={"Authorization": "Bearer test-token"},
            )
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
        self.assertEqual(received, [("/start", "Bearer test-token"), ("/asset", None)])


if __name__ == "__main__":
    unittest.main()
