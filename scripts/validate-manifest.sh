#!/usr/bin/env bash
# Validate a Potions Shelf catalog entry without network access.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <manifest-file>" >&2
  exit 2
fi
exec python3 "$SCRIPT_DIR/validate-manifest.py" "$1"
