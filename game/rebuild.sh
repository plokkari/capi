#!/usr/bin/env bash
set -euo pipefail

# Use Python 3.11+ if you have it; otherwise python3 is fine
PYTHON_BIN="${PYTHON_BIN:-python3}"

# Ensure pygbag is available
if ! "$PYTHON_BIN" -c "import pygbag, sys; print(getattr(pygbag,'__version__','installed'))" >/dev/null 2>&1; then
  echo "pygbag is not installed for $PYTHON_BIN."
  echo "Install it with:"
  echo "  $PYTHON_BIN -m pip install --user --upgrade pygbag"
  exit 1
fi

# Build the web bundle; disable the 'Ready to start!' gate so visuals can auto-run
"$PYTHON_BIN" -m pygbag --ume_block 0 --build main.py

echo "Build complete -> game/build/web/index.html"
