"""Record native CPython 3.13 wheels selected from hashed requirements."""

import argparse
import hashlib
import json
from pathlib import Path
from platforms import resolve


from build_cache import LATEST, file_digest

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform", choices=("windows-x64", "linux-x64", "macos-arm64"))
    parser.add_argument("--wheelhouse", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    identifier, target = resolve(args.platform)
    args.wheelhouse = args.wheelhouse or LATEST / "inputs/wheels" / identifier / file_digest(ROOT / 'packaging' / target['wheel_lock'])
    args.output = args.output or ROOT / "packaging" / target["wheel_lock"]
    requirements = (ROOT / "packaging" / target["requirements"]).read_text(encoding="utf-8")
    wheels = []
    for path in sorted(args.wheelhouse.glob("*.whl")):
        with path.open("rb") as stream:
            checksum = hashlib.file_digest(stream, "sha256").hexdigest()
        if f"sha256:{checksum}" not in requirements:
            raise RuntimeError(f"Wheel checksum is absent from requirements lock: {path.name}")
        wheels.append({"filename": path.name, "sha256": checksum, "size": path.stat().st_size})
    if not wheels:
        raise RuntimeError("No downloaded wheels found")
    args.output.write_text(json.dumps(wheels, indent=2) + "\n", encoding="utf-8")
    print(f"Locked {len(wheels)} wheels")


if __name__ == "__main__":
    main()
