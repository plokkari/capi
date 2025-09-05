#!/usr/bin/env bash
set -euo pipefail
PYTHON_BIN="${PYTHON_BIN:-python3}"

"$PYTHON_BIN" -m pygbag --ume_block 0 --build main.py

F="build/web/index.html"
TAG='<script src="../../forwarder.js"></script>'

# Inject once if missing
if [ -f "$F" ] && ! grep -q 'forwarder.js' "$F"; then
  awk -v tag="$TAG" '
    /<\/body>/ && !done { print "  <!-- injected: forwarder.js -->\n  " tag; done=1 }
    { print }
  ' "$F" > "$F.tmp" && mv "$F.tmp" "$F"
  echo "Injected forwarder.js"
else
  echo "forwarder already injected or page missing"
fi

echo "Build complete -> $F"
