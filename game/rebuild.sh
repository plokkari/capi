#!/usr/bin/env bash
set -euo pipefail
PYTHON_BIN="${PYTHON_BIN:-python3}"
"$PYTHON_BIN" -m pygbag --ume_block 0 --build main.py
echo "Build complete -> game/build/web/index.html"
