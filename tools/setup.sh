#!/usr/bin/env bash
# Installs what the checks and the agent skills need. Run once from anywhere.
set -euo pipefail
cd "$(dirname "$0")/.."
command -v python3 >/dev/null || { echo "python3 is required"; exit 1; }
command -v git >/dev/null || { echo "git is required"; exit 1; }
command -v node >/dev/null || { echo "node 20 or later is required"; exit 1; }
python3 -m pip install --quiet --break-system-packages -r requirements-dev.txt 2>/dev/null \
  || python3 -m pip install --quiet -r requirements-dev.txt
(cd tools && npm ci --silent)
echo "ready: run tools/check.sh"
