#!/usr/bin/env bash
set -euo pipefail

python -m ruff check .
python -m pytest
python -m build

echo "Local validation passed."
