import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = REPO_ROOT / ".claude/skills/blender-mcp-skills/templates/extension_addon/scripts/validate_extension.py"


def write_minimal_manifest(extension_root: Path, *, network_permission: bool = False) -> None:
    permissions = (
        '\n[permissions]\nnetwork = "Install missing Python packages into the extension private dependency directory"\n'
        if network_permission
        else ""
    )
    (extension_root / "blender_manifest.toml").write_text(
        textwrap.dedent(
            f"""
            schema_version = "1.0.0"
            id = "test_extension"
            version = "1.0.0"
            name = "Test Extension"
            tagline = "Test extension"
            maintainer = "Tester"
            type = "add-on"
            blender_version_min = "4.2.0"
            license = ["SPDX:GPL-3.0-or-later"]
            {permissions}
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )


def run_validator(extension_root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(VALIDATOR),
            "--source-path",
            str(extension_root),
            "--skip-blender-validate",
        ],
        check=False,
        capture_output=True,
        text=True,
    )


class ValidateExtensionDependencyChecksTest(unittest.TestCase):
    def test_warns_for_pip_install_without_target_and_missing_network_permission(self):
        with tempfile.TemporaryDirectory() as tmp:
            extension_root = Path(tmp)
            write_minimal_manifest(extension_root)
            (extension_root / "installer.py").write_text(
                textwrap.dedent(
                    """
                    import subprocess
                    import sys

                    def install():
                        subprocess.run([sys.executable, "-m", "pip", "install", "requests"])
                    """
                ),
                encoding="utf-8",
            )

            proc = run_validator(extension_root)

        output = proc.stdout + proc.stderr
        self.assertEqual(proc.returncode, 0, output)
        self.assertIn("pip install", output)
        self.assertIn("--target", output)
        self.assertIn("network", output)

    def test_warns_for_private_deps_and_top_level_third_party_imports(self):
        with tempfile.TemporaryDirectory() as tmp:
            extension_root = Path(tmp)
            write_minimal_manifest(extension_root, network_permission=True)
            (extension_root / "deps" / "site-packages").mkdir(parents=True)
            (extension_root / "operators").mkdir()
            (extension_root / "operators" / "example.py").write_text(
                "import requests\nfrom yaml import safe_load\n",
                encoding="utf-8",
            )

            proc = run_validator(extension_root)

        output = proc.stdout + proc.stderr
        self.assertEqual(proc.returncode, 0, output)
        self.assertIn("deps/site-packages", output)
        self.assertIn("top-level", output)
        self.assertIn("requests", output)
        self.assertIn("yaml", output)


if __name__ == "__main__":
    unittest.main()
