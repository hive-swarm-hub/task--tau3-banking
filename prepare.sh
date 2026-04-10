#!/usr/bin/env bash
# Set up tau3-bench banking_knowledge: clones tau2-bench v1.0.0, installs
# Python deps via uv, installs sandbox-runtime + ripgrep for terminal_use.
# Idempotent — safe to re-run.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TAU3_DIR="$SCRIPT_DIR/tau3-bench"
TAU3_REPO="https://github.com/sierra-research/tau2-bench.git"
TAU3_REF="v1.0.0"
SRT_VERSION="0.0.23"

echo "=== tau3-banking: prepare ==="

# ── 1. Check OPENAI_API_KEY ─────────────────────────────────────────────────
if [ -z "${OPENAI_API_KEY:-}" ]; then
    echo "WARNING: OPENAI_API_KEY is not set. Set it before running eval."
fi

# ── 2. Clone tau2-bench at v1.0.0 ───────────────────────────────────────────
if [ -d "$TAU3_DIR/.git" ]; then
    echo "tau3-bench already cloned at $TAU3_DIR — fetching latest tags"
    cd "$TAU3_DIR"
    git fetch --tags origin "$TAU3_REF" 2>/dev/null || true
    git checkout "$TAU3_REF" 2>/dev/null || true
    cd "$SCRIPT_DIR"
else
    echo "Cloning tau2-bench @ $TAU3_REF ..."
    git clone --depth 1 --branch "$TAU3_REF" "$TAU3_REPO" "$TAU3_DIR"
fi

# ── 3. Install Python deps with uv (knowledge extra needed for banking) ─────
cd "$TAU3_DIR"

if ! command -v uv >/dev/null 2>&1; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

echo "Installing tau2-bench with the 'knowledge' extra..."
uv sync --extra knowledge

VENV_PYTHON="$TAU3_DIR/.venv/bin/python3"

# ── 4. Install task-level requirements (litellm, etc.) ──────────────────────
if [ -f "$SCRIPT_DIR/requirements.txt" ] \
        && grep -qvE '^\s*(#|$)' "$SCRIPT_DIR/requirements.txt"; then
    echo "Installing task requirements..."
    uv pip install --python "$VENV_PYTHON" -r "$SCRIPT_DIR/requirements.txt"
fi

# ── 5. Install system tools needed by terminal_use ──────────────────────────
# terminal_use needs Anthropic's sandbox-runtime (srt, via npm) + ripgrep.
# Skip silently if the tooling isn't available — only terminal_use* variants
# need this. All bm25/embeddings/grep_only variants work without it.

install_node_if_missing() {
    if command -v node >/dev/null 2>&1 && command -v npm >/dev/null 2>&1; then
        return 0
    fi
    echo "Node.js / npm not found — needed for sandbox-runtime (terminal_use)."
    if [[ "$OSTYPE" == "darwin"* ]] && command -v brew >/dev/null 2>&1; then
        brew install node
    elif command -v apt-get >/dev/null 2>&1; then
        sudo apt-get update -y && sudo apt-get install -y nodejs npm
    else
        echo "  (skipping — install Node.js manually if you want terminal_use)"
        return 1
    fi
}

if install_node_if_missing && command -v npm >/dev/null 2>&1; then
    if ! command -v srt >/dev/null 2>&1; then
        echo "Installing @anthropic-ai/sandbox-runtime@$SRT_VERSION ..."
        npm install -g "@anthropic-ai/sandbox-runtime@$SRT_VERSION" 2>&1 \
            || sudo npm install -g "@anthropic-ai/sandbox-runtime@$SRT_VERSION" 2>&1 \
            || echo "  (failed — terminal_use variant will not work)"
    else
        echo "sandbox-runtime (srt) already installed"
    fi
fi

if ! command -v rg >/dev/null 2>&1; then
    echo "Installing ripgrep (needed for terminal_use) ..."
    if [[ "$OSTYPE" == "darwin"* ]] && command -v brew >/dev/null 2>&1; then
        brew install ripgrep
    elif command -v apt-get >/dev/null 2>&1; then
        sudo apt-get install -y ripgrep || true
    else
        echo "  (skipping — install ripgrep manually if you want terminal_use)"
    fi
fi

if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    if ! command -v bwrap >/dev/null 2>&1 && command -v apt-get >/dev/null 2>&1; then
        echo "Installing bubblewrap + socat (needed for srt on Linux) ..."
        sudo apt-get install -y bubblewrap socat || true
    fi
fi

# ── 6. Verify the domain loads ──────────────────────────────────────────────
echo ""
echo "Verifying setup..."
"$VENV_PYTHON" -c "
from tau2.runner import get_tasks
tasks = get_tasks(task_set_name='banking_knowledge')
print(f'  banking_knowledge: {len(tasks)} tasks loaded')
"

echo ""
echo "=== Preparation complete ==="
echo ""
echo "Required env var:  OPENAI_API_KEY"
echo "Optional env vars:"
echo "  AGENT_LLM   (default: openai/gpt-5.4-mini)"
echo "  USER_LLM    (default: openai/gpt-4.1)"
echo "  EVAL_MODE   (default: fast — also: full, submit)"
