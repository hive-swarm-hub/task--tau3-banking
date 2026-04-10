#!/usr/bin/env bash
# tau3-banking evaluation script (thin wrapper around eval/run_eval.py).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TASK_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
TAU3_DIR="$TASK_DIR/tau3-bench"
PYTHON="$TAU3_DIR/.venv/bin/python3"

# ── Validate prerequisites ──────────────────────────────────────────────────
if [ ! -d "$TAU3_DIR" ]; then
    echo "ERROR: tau3-bench not found at $TAU3_DIR" >&2
    echo "Run 'bash prepare.sh' first." >&2
    exit 1
fi

if [ ! -f "$PYTHON" ]; then
    echo "ERROR: venv not found at $TAU3_DIR/.venv" >&2
    echo "Run 'bash prepare.sh' first." >&2
    exit 1
fi

if [ -z "${OPENAI_API_KEY:-}" ]; then
    echo "ERROR: OPENAI_API_KEY is not set" >&2
    exit 1
fi

# ── Run from tau3-bench dir so its package data resolves correctly ──────────
cd "$TAU3_DIR"
exec "$PYTHON" "$SCRIPT_DIR/run_eval.py"
