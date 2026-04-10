#!/usr/bin/env bash
# Evaluate agent.py on tau3-bench banking_knowledge.
set -euo pipefail

cd "$(dirname "$0")/.."

# Clear any stale simulation dir for the current mode before running. Without
# this, tau3-bench's try_resume() prompts "Do you want to resume? (y/n)" on
# stdin whenever results.json exists, which crashes with EOFError under any
# non-interactive execution (background, nohup, subprocess, CI).
EVAL_MODE="${EVAL_MODE:-fast}"
rm -rf "tau3-bench/data/simulations/hive_${EVAL_MODE}"

exec tau3-bench/.venv/bin/python3 eval/run_eval.py
