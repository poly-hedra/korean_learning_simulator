#!/usr/bin/env bash
set -euo pipefail

# Move to project root regardless of where this script is called from.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

if ! command -v uv >/dev/null 2>&1; then
  echo "Error: 'uv' is not installed or not in PATH."
  echo "Install with: pip install uv"
  exit 1
fi

exec uv run main.py --reload
