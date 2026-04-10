# tau3-banking

Banking customer service agent benchmark powered by [tau2-bench](https://github.com/sierra-research/tau2-bench).

The agent is evaluated on the `banking_knowledge` domain (97 multi-turn
customer service tasks). Modify `agent.py` to maximize **pass^1**.

## Quickstart

```bash
export OPENAI_API_KEY=sk-...
bash prepare.sh                          # one-time setup
bash eval/eval.sh                        # fast eval (20 tasks)
EVAL_MODE=full   bash eval/eval.sh       # full eval (97 tasks, 1 trial)
EVAL_MODE=submit bash eval/eval.sh       # submission eval (97 tasks, 4 trials)
```

## What you modify

- `agent.py` — the banking agent (system prompt, retrieval variant,
  reasoning loop). See `program.md` for the full task spec.

## Output

`eval/eval.sh` prints:

```
---
pass_at_1:        0.1234
correct:          12
total:            97
cost_usd:         5.67
retrieval:        bm25_grep
```
