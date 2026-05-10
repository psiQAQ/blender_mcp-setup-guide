#!/usr/bin/env bash
set -euo pipefail

show_help() {
  cat <<'EOF'
Usage: build_extension.sh [OPTIONS]

Build Blender extension from template root.

Options:
  -h, --help   Show this help message and exit
EOF
}

case "${1:-}" in
  -h|--help)
    show_help
    exit 0
    ;;
esac

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
EXTENSION_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

cd "${EXTENSION_ROOT}"
python3 "${SCRIPT_DIR}/preflight_extension.py"
blender --command extension build
