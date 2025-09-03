#!/usr/bin/env bash
set -euo pipefail

# You can override which Python to use by doing:  PYTHON_BIN=python3.11 ./rebuild.sh
PYTHON_BIN="${PYTHON_BIN:-python3}"

# (Optional) if your outer page isn't at repo root, set:
# OUTER_INDEX=game/index.html ./rebuild.sh
OUTER_INDEX="${OUTER_INDEX:-index.html}"

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
else
  awk -v tag="$TAG" '
    /<\/body>/ && !done { print "  <!-- injected: forwarder.js -->\n  " tag; done=1 }
    { print }
  ' "$F" > "$F.tmp" && mv "$F.tmp" "$F"
  echo "Injected forwarder.js"
fi

# --- Step 3: add/update a cache-buster on the iframe src in your outer page ---
# Turns:  build/web/index.html  ->  build/web/index.html?v=<timestamp>
STAMP="$(date +%s)"
if [ -f "$OUTER_INDEX" ]; then
  "$PYTHON_BIN" - "$OUTER_INDEX" "$STAMP" <<'PY'
import re, sys
path, ver = sys.argv[1], sys.argv[2]
try:
    s = open(path, 'r', encoding='utf-8').read()
except FileNotFoundError:
    sys.exit(0)

# Replace existing ?v=… or add if missing
pattern = re.compile(r'(build/web/index\.html)(?:\?v=[^"\'\s]*)?')
new = pattern.sub(lambda m: f'{m.group(1)}?v={ver}', s)

if new != s:
    open(path, 'w', encoding='utf-8').write(new)
    print(f"Cache-buster set in {path} -> v={ver}")
else:
    print(f"No build/web/index.html reference found in {path}; skipped cache-buster")
PY
else
  echo "Outer page $OUTER_INDEX not found; skipped cache-buster"
fi

echo "Rebuild complete."
