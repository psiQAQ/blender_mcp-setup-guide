import importlib.util
import json
import tomllib
import tempfile
import unittest
import sys
import types
from pathlib import Path
from unittest.mock import patch


PACKAGE = types.ModuleType("integration_unit")
PACKAGE.__path__ = [str(Path(__file__).resolve().parents[1] / "src/blender_mcp_integration")]
sys.modules[PACKAGE.__name__] = PACKAGE
SPEC = importlib.util.spec_from_file_location("integration_unit.runtime", Path(PACKAGE.__path__[0]) / "runtime.py")
runtime = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runtime)


class RuntimeTests(unittest.TestCase):
    def test_exported_configurations_have_correct_transport_and_authorization(self):
        codex = tomllib.loads(runtime.client_configuration("CODEX", 8123, "test-token"))["mcp_servers"]["blender"]
        claude = json.loads(runtime.client_configuration("CLAUDE", 8123, "test-token"))["mcpServers"]["blender"]
        opencode = json.loads(runtime.client_configuration("OPENCODE", 8123, "test-token"))["mcp"]["blender"]
        for configuration, header_key in ((codex, "http_headers"), (claude, "headers"), (opencode, "headers")):
            self.assertEqual(configuration["url"], "http://127.0.0.1:8123/")
            self.assertEqual(configuration[header_key]["Authorization"], "Bearer test-token")
        self.assertEqual(claude["type"], "http")
        self.assertEqual(opencode["type"], "remote")

    def test_python_abi_mismatch_fails_before_process_creation(self):
        with patch.object(runtime.platform, "system", return_value="Windows"), patch.object(runtime.platform, "machine", return_value="AMD64"), patch.object(runtime.sys, "version_info", (3, 12)):
            with self.assertRaisesRegex(runtime.ServiceError, "CPython 3.13"):
                runtime.check_runtime()

    def test_unsupported_platform_fails_before_process_creation(self):
        with patch.object(runtime.platform, "system", return_value="Darwin"), patch.object(runtime.platform, "machine", return_value="x86_64"):
            with self.assertRaisesRegex(runtime.ServiceError, "Unsupported platform"):
                runtime.check_runtime()

    def test_supported_native_platforms_require_cpython_313(self):
        for system, machine, expected in (("Windows", "AMD64", "windows-x64"), ("Linux", "x86_64", "linux-x64"), ("Darwin", "arm64", "macos-arm64")):
            with self.subTest(system=system), patch.object(runtime.platform, "system", return_value=system), patch.object(runtime.platform, "machine", return_value=machine), patch.object(runtime.sys, "version_info", (3, 13)):
                self.assertEqual(runtime.platform_id(), expected)
                runtime.check_runtime()

    def test_stopped_service_cannot_export_credentials_as_a_working_connection(self):
        with self.assertRaisesRegex(runtime.ServiceError, "Start the service"):
            runtime.Service().configuration("CODEX")

    def test_incomplete_cleanup_cannot_be_overwritten_by_a_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            service = runtime.Service()
            service.config_path = Path(directory) / "session-leftover.json"
            with patch.object(runtime, "check_runtime"):
                with self.assertRaisesRegex(runtime.ServiceError, "cleaning up"):
                    service.start(directory, 8000, 9876)
            self.assertEqual(service.config_path.name, "session-leftover.json")


if __name__ == "__main__":
    unittest.main()
