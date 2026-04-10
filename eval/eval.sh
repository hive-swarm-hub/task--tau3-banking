#!/usr/bin/env bash
# Evaluate agent.py on tau3-bench banking_knowledge.
set -euo pipefail

cd "$(dirname "$0")/.."
exec tau3-bench/.venv/bin/python3 eval/run_eval.py
