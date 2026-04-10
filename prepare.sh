#!/usr/bin/env bash
# Set up tau2-bench (includes the τ³ banking_knowledge domain). Run once.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TAU3_DIR="$SCRIPT_DIR/tau3-bench"

if [ ! -d "$TAU3_DIR" ]; then
    echo "Cloning tau2-bench..."
    git clone --depth 1 --branch dev/tau3 https://github.com/sierra-research/tau2-bench.git "$TAU3_DIR"
fi

python3 "$SCRIPT_DIR/_setup.py" "$TAU3_DIR"

cd "$TAU3_DIR"
uv sync --extra knowledge

# Optional: terminal_use retrieval needs sandbox-runtime + ripgrep.
command -v srt >/dev/null 2>&1 || npm install -g @anthropic-ai/sandbox-runtime@0.0.23 2>/dev/null || true
command -v rg  >/dev/null 2>&1 || brew install ripgrep 2>/dev/null || true

echo "Done."
