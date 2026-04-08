#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# tau3-banking preparation script
#
# Clones the tau3-bench framework and installs dependencies.
# Run once before eval: bash prepare.sh
# ──────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TAU3_DIR="$SCRIPT_DIR/tau3-bench"

echo "=== tau3-banking: prepare ==="

# ── Clone tau3-bench ─────────────────────────────────────────────────────────
if [ -d "$TAU3_DIR" ]; then
    echo "tau3-bench already cloned at $TAU3_DIR"
    cd "$TAU3_DIR"
    git fetch origin dev/tau3 2>/dev/null || true
    git checkout dev/tau3 2>/dev/null || true
    git pull origin dev/tau3 2>/dev/null || true
else
    echo "Cloning tau3-bench (branch: dev/tau3)..."
    git clone --branch dev/tau3 https://github.com/sierra-research/tau2-bench.git "$TAU3_DIR"
fi

# ── Install dependencies ────────────────────────────────────────────────────
cd "$TAU3_DIR"

echo "Installing tau3-bench with knowledge extras..."

# Check if uv is available, fall back to pip
if command -v uv &>/dev/null; then
    # Install knowledge deps via uv sync, then voice deps via uv pip
    # (uv sync --extra voice fails without portaudio for pyaudio build)
    uv sync --extra knowledge 2>&1
    # Install voice deps except pyaudio (needs portaudio system library)
    uv pip install elevenlabs deepgram-sdk websockets jiwer scipy pydub tqdm \
        aiohttp google-genai boto3 google-cloud-aiplatform google-auth \
        --python "$TAU3_DIR/.venv/bin/python3" 2>&1
else
    pip install -e ".[knowledge]" 2>&1
    pip install elevenlabs deepgram-sdk websockets jiwer scipy pydub tqdm \
        aiohttp google-genai boto3 google-cloud-aiplatform google-auth 2>&1
fi

# Create stub pyaudio module (avoids needing portaudio system library)
SITE_PACKAGES=$("$TAU3_DIR/.venv/bin/python3" -c "import site; print(site.getsitepackages()[0])")
if [ ! -f "$SITE_PACKAGES/pyaudio.py" ]; then
    echo "Creating pyaudio stub..."
    cat > "$SITE_PACKAGES/pyaudio.py" << 'STUB'
"""Stub pyaudio module — only needed so tau2.voice imports don't crash.
Not used for text-only banking_knowledge evaluation."""
paInt16 = 8
paFloat32 = 1
class PyAudio:
    def __init__(self): pass
    def open(self, **kw): raise RuntimeError("pyaudio stub: audio not available")
    def terminate(self): pass
class Stream:
    pass
STUB
fi

# ── Install task-level requirements ──────────────────────────────────────────
VENV_PYTHON="$TAU3_DIR/.venv/bin/python3"
if [ -f "$SCRIPT_DIR/requirements.txt" ] && grep -qvE '^\s*(#|$)' "$SCRIPT_DIR/requirements.txt" 2>/dev/null; then
    echo "Installing task requirements..."
    if command -v uv &>/dev/null; then
        uv pip install -r "$SCRIPT_DIR/requirements.txt" --python "$VENV_PYTHON" 2>&1
    else
        "$VENV_PYTHON" -m pip install -r "$SCRIPT_DIR/requirements.txt" 2>&1
    fi
fi

# ── Verify setup ─────────────────────────────────────────────────────────────
echo ""
echo "Verifying setup..."

# Check that the domain loads (use the venv python to avoid pyenv conflicts)
"$VENV_PYTHON" -c "
from tau2.runner import get_tasks
tasks = get_tasks('banking_knowledge')
print(f'  banking_knowledge domain: {len(tasks)} tasks loaded')
" 2>&1

echo ""
echo "=== Preparation complete ==="
echo "Make sure these env vars are set before running eval:"
echo "  OPENAI_API_KEY     (for agent LLM: gpt-5.4-mini and user simulator: gpt-4.1)"
