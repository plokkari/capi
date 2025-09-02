#!/usr/bin/env bash
set -euo pipefail

# You can override which Python to use by doing:  PYTHON_BIN=python3.11 ./rebuild.sh
PYTHON_BIN="${PYTHON_BIN:-python3}"

# Make sure pygbag is installed for this Python
if ! "$PYTHON_BIN" -c "import pygbag, sys; print(getattr(pygbag, '__version__', 'installed'))" >/dev/null 2>&1; then
  echo "pygbag is not installed for $PYTHON_BIN."
  echo "Install it with:"
  echo "  $PYTHON_BIN -m pip install --user --upgrade pygbag"
  exit 1
fi

# Build the web bundle and DO NOT wait for 'user media engagement'
# (removes the 'Ready to start!' gate so visuals can auto-run on mobile)
"$PYTHON_BIN" -m pygbag --ume_block 0 --build main.py

F="build/web/index.html"
TAG='<script src="../../forwarder.js"></script>'

# Inject forwarder.js once (keeps your scoreboard/Supabase signaling intact)
if grep -q 'forwarder.js' "$F"; then
  echo "forwarder already injected"
  exit 0
fi

awk -v tag="$TAG" '
  /<\/body>/ && !done { print "  <!-- injected: forwarder.js -->\n  " tag; done=1 }
  { print }
' "$F" > "$F.tmp" && mv "$F.tmp" "$F"

echo "Injected forwarder.js"
