#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# tau3-banking evaluation script
#
# Runs the agent defined in agent.py against 25 banking_knowledge tasks
# from tau3-bench and reports pass@1.
#
# Usage:  bash eval/eval.sh
# Output: prints score summary ending with the standard hive format.
# ──────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TASK_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
TAU3_DIR="$TASK_DIR/tau3-bench"
PYTHON="$TAU3_DIR/.venv/bin/python3"

# ── Settings ─────────────────────────────────────────────────────────────────
AGENT_LLM="anthropic/claude-haiku-4-5-20251001"
USER_LLM="openai/gpt-4.1"
MAX_CONCURRENCY=3
MAX_STEPS=200
TIMEOUT=1800  # 30 minutes

# 25 representative tasks spread across the full set
TASK_IDS="task_001,task_004,task_007,task_012,task_016,task_020,task_024,task_028,task_033,task_037,task_041,task_045,task_049,task_053,task_057,task_061,task_065,task_069,task_073,task_077,task_081,task_085,task_089,task_094,task_099"

# ── Validate prerequisites ──────────────────────────────────────────────────
if [ ! -d "$TAU3_DIR" ]; then
    echo "ERROR: tau3-bench not found at $TAU3_DIR"
    echo "Run 'bash prepare.sh' first."
    exit 1
fi

if [ ! -f "$PYTHON" ]; then
    echo "ERROR: venv not found at $TAU3_DIR/.venv"
    echo "Run 'bash prepare.sh' first."
    exit 1
fi

if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
    echo "ERROR: ANTHROPIC_API_KEY is not set (needed for agent LLM)"
    exit 1
fi

if [ -z "${OPENAI_API_KEY:-}" ]; then
    echo "ERROR: OPENAI_API_KEY is not set (needed for user simulator)"
    exit 1
fi

# ── Read retrieval config from agent.py ──────────────────────────────────────
RETRIEVAL_VARIANT=$("$PYTHON" -c "
import sys
sys.path.insert(0, '$TASK_DIR')
from agent import RETRIEVAL_VARIANT
print(RETRIEVAL_VARIANT)
" 2>/dev/null || echo "bm25")

RETRIEVAL_KWARGS_JSON=$("$PYTHON" -c "
import sys, json
sys.path.insert(0, '$TASK_DIR')
from agent import RETRIEVAL_KWARGS
print(json.dumps(RETRIEVAL_KWARGS) if RETRIEVAL_KWARGS else '')
" 2>/dev/null || echo "")

echo "=== tau3-banking eval ==="
echo "Agent LLM:         $AGENT_LLM"
echo "User LLM:          $USER_LLM"
echo "Retrieval variant:  $RETRIEVAL_VARIANT"
echo "Tasks:             25 / 97"
echo "Timeout:           ${TIMEOUT}s"
echo ""

# ── Run evaluation ───────────────────────────────────────────────────────────
cd "$TAU3_DIR"

# Construct retrieval kwargs for Python
if [ -n "$RETRIEVAL_KWARGS_JSON" ]; then
    RETRIEVAL_KWARGS_PY="$RETRIEVAL_KWARGS_JSON"
else
    RETRIEVAL_KWARGS_PY="None"
fi

# Register and run the custom agent
RESULTS_JSON=$(mktemp)
# Use gtimeout on macOS, timeout on Linux
TIMEOUT_CMD=""
if command -v timeout &>/dev/null; then
    TIMEOUT_CMD="timeout $TIMEOUT"
elif command -v gtimeout &>/dev/null; then
    TIMEOUT_CMD="gtimeout $TIMEOUT"
fi

$TIMEOUT_CMD "$PYTHON" -c "
import sys, json, os
sys.path.insert(0, '$TASK_DIR')

from agent import create_agent, RETRIEVAL_VARIANT, RETRIEVAL_KWARGS
from tau2.registry import registry
from tau2.runner import get_tasks, run_domain
from tau2.data_model.simulation import TextRunConfig

# Register the custom agent
registry.register_agent_factory(create_agent, 'hive_agent')

# Build run config
task_ids = '$TASK_IDS'.split(',')

config = TextRunConfig(
    domain='banking_knowledge',
    agent='hive_agent',
    llm_agent='$AGENT_LLM',
    llm_user='$USER_LLM',
    num_trials=1,
    num_tasks=len(task_ids),
    task_ids=task_ids,
    max_steps=$MAX_STEPS,
    max_concurrency=$MAX_CONCURRENCY,
    retrieval_config='$RETRIEVAL_VARIANT',
    retrieval_config_kwargs=$RETRIEVAL_KWARGS_PY,
)

results = run_domain(config)

# results is a Results object with .simulations list of SimulationRun
sims = results.simulations

# Compute pass@1
passed = sum(1 for r in sims if r.reward_info and r.reward_info.reward == 1.0)
total = len(sims)
score = passed / total if total > 0 else 0.0

# Write detailed results
details = []
for r in sims:
    reward = r.reward_info.reward if r.reward_info else 0.0
    msgs = r.messages if r.messages else []
    details.append({
        'task_id': r.task_id,
        'reward': reward,
        'num_messages': len(msgs),
    })

with open('$RESULTS_JSON', 'w') as f:
    json.dump({'passed': passed, 'total': total, 'score': score, 'details': details}, f, indent=2)

print(json.dumps({'passed': passed, 'total': total, 'score': score}))
" 2>&1 | tee /dev/stderr | tail -1 > /dev/null

# ── Parse and display results ────────────────────────────────────────────────
if [ ! -f "$RESULTS_JSON" ] || [ ! -s "$RESULTS_JSON" ]; then
    echo ""
    echo "ERROR: Evaluation failed to produce results."
    echo "---"
    echo "pass_at_1:        0.0"
    echo "correct:          0"
    echo "total:            25"
    exit 0
fi

PASSED=$("$PYTHON" -c "import json; d=json.load(open('$RESULTS_JSON')); print(d['passed'])")
TOTAL=$("$PYTHON" -c "import json; d=json.load(open('$RESULTS_JSON')); print(d['total'])")
SCORE=$("$PYTHON" -c "import json; d=json.load(open('$RESULTS_JSON')); print(f\"{d['score']:.4f}\")")

# Show per-task breakdown
echo ""
echo "=== Per-task results ==="
"$PYTHON" -c "
import json
d = json.load(open('$RESULTS_JSON'))
for t in d['details']:
    status = 'PASS' if t['reward'] == 1.0 else 'FAIL'
    print(f\"  {t['task_id']}: {status} (msgs={t['num_messages']})\")
"

echo ""
echo "=== Summary ==="
echo "---"
echo "pass_at_1:        $SCORE"
echo "correct:          $PASSED"
echo "total:            $TOTAL"

# Clean up
rm -f "$RESULTS_JSON"
