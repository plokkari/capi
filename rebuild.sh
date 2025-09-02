#!/usr/bin/env bash
set -euo pipefail

pygbag --build main.py

F="build/web/index.html"
TAG='<script src="../../forwarder.js"></script>'

# Skip if already present
grep -q 'forwarder.js' "$F" && { echo "forwarder already injected"; exit 0; }

# Insert before </body> (works on macOS & Linux)
awk -v tag="$TAG" '
  /<\/body>/ && !done { print "  <!-- injected: forwarder.js -->\n  " tag; done=1 }
  { print }
' "$F" > "$F.tmp" && mv "$F.tmp" "$F"

echo "Injected forwarder.js"
