"""Generate an Extension with unique Blender identifiers."""

import argparse
import re
import shutil
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = REPO_ROOT / ".agents/skills/blender-mcp-skills/templates/extension_addon"


def scaffold(extension_id: str, output: Path) -> None:
    if not re.fullmatch(r"[a-z][a-z0-9_]*", extension_id):
        raise ValueError("Extension ID must be a lowercase Python identifier")
    if output.exists():
        raise FileExistsError(f"Output already exists: {output}")
    shutil.copytree(TEMPLATE, output, ignore=shutil.ignore_patterns("__pycache__", "*.zip"))
    for path in sorted(output.rglob("*")):
        if path.suffix not in {".py", ".toml", ".md"}:
            continue
        content = path.read_text(encoding="utf-8")
        content = content.replace("my_example_extension", extension_id)
        content = content.replace("MY_EXAMPLE_EXTENSION", extension_id.upper())
        path.write_text(content, encoding="utf-8", newline="\n")
    shutil.copyfile(REPO_ROOT / "LICENSE", output / "LICENSE")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("extension_id")
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    scaffold(args.extension_id, args.output.resolve())


if __name__ == "__main__":
    main()
