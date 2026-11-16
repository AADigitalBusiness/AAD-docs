#!/usr/bin/env bash
# The checks to run before every commit: links, CSV, JSON, YAML and Mermaid diagrams.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 tools/check_docs.py
node tools/check_mermaid.mjs
