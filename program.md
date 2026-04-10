# tau3-banking

Optimize a banking customer service agent on the tau3-bench `banking_knowledge`
domain. The metric is **pass^1**: the fraction of tasks where the agent's
final database state matches the gold standard on a single trial.

You evolve `agent.py`, and only `agent.py`. Everything else is infrastructure.

---

## Setup

1. **Read the in-scope files**:
   - `agent.py` — the agent under optimization. You modify this.
   - `eval/eval.sh` and `eval/run_eval.py` — the eval harness. Do not modify.
   - `prepare.sh` — installs tau2-bench, Python deps, and sandbox-runtime.
     Do not modify.
2. **Run prepare**: `bash prepare.sh` (idempotent — safe to re-run).
3. **Verify env**: `echo $OPENAI_API_KEY` — must be set.
4. **Initialize results.tsv**: create `results.tsv` with the header row only.
5. **Run a baseline**: `bash eval/eval.sh` (fast mode, 20 tasks). Record the
   score in `results.tsv`.

---

## The benchmark

`banking_knowledge` is a knowledge-retrieval customer service domain with 97
multi-turn tasks. In each task the agent must:

- Authenticate the customer (verify 2 of 4: DOB, email, phone, address).
- Search a knowledge base of 698 documents covering products, fees,
  eligibility rules, dispute procedures, and other policies.
- Discover and call 51 "discoverable" tools that are referenced only inside
  the KB documents — the agent finds them by reading the KB.
- Use 14 always-available banking tools to read and modify a transactional
  database.
- End the conversation with the database in the exact correct state.

A task passes when the final database state matches the gold standard
(reward = 1.0). pass^1 is the fraction of tasks that pass on a single trial.

The simulated user follows task-specific flow rules and will steer toward
edge cases. pass^1 across frontier models on this domain ranges from
roughly 8% to 32% — this is a hard benchmark.

---

## Eval modes

`bash eval/eval.sh` runs in `fast` mode by default. Set `EVAL_MODE` for
the other modes:

| Mode   | Tasks | Trials | Use this when |
|--------|-------|--------|---------------|
| `fast`   | 20 fixed | 1 | Every iteration. ~5 minutes. |
| `full`   | 97 | 1 | Confirming a fast-mode improvement on the full set. |
| `submit` | 97 | 4 | Producing the canonical 4-trial trajectories. |

```bash
bash eval/eval.sh                       # fast (default)
EVAL_MODE=full   bash eval/eval.sh
EVAL_MODE=submit bash eval/eval.sh
```

The fast subset is 20 fixed task IDs evenly spread across the 97 — same
set every run, so results are directly comparable across iterations.

---

## What you can edit

Everything inside `agent.py`. The three main levers:

### 1. Retrieval variant (`RETRIEVAL_VARIANT` / `RETRIEVAL_KWARGS`)

The framework wires up different tools and prompt templates depending on
the variant. Switching the variant is a major change — the agent gets a
different set of tools, and the policy template changes too.

Variants usable with `OPENAI_API_KEY`:

| Variant | Tools | Notes |
|---------|-------|-------|
| `bm25` | KB_search | Sparse keyword |
| `bm25_grep` | KB_search + grep | Adds regex fallback |
| `bm25_reranker` | KB_search | Reranks BM25 results with an LLM |
| `bm25_reranker_grep` | KB_search + grep | Both |
| `openai_embeddings` | KB_search | Dense, uses `text-embedding-3-large` |
| `openai_embeddings_grep` | KB_search + grep | + grep |
| `openai_embeddings_reranker` | KB_search | + LLM reranker |
| `openai_embeddings_reranker_grep` | KB_search + grep | All four |
| `grep_only` | grep | Just regex |
| `terminal_use` | shell | Read-only Unix shell sandbox |
| `terminal_use_write` | shell | Shell with write access |
| `no_knowledge` | (none) | No KB at all |
| `full_kb` | (none) | Whole KB inlined in prompt — token-heavy |

`golden_retrieval` exists but is a diagnostic only — it injects task-specific
docs into the prompt and is not a valid retrieval method for a real run.

`qwen_*` variants require `OPENROUTER_API_KEY` and are unsupported here.

`RETRIEVAL_KWARGS` overrides knobs like `top_k` (for KB_search) or
`reranker_min_score` (for `*_reranker` variants).

### 2. The system prompt (`AGENT_INSTRUCTION`, `SYSTEM_PROMPT_TEMPLATE`,
`HiveAgent.system_prompt`)

The single biggest lever. The `domain_policy` passed to the agent is
already a fully assembled template — it includes the Rho-Bank policy,
retrieval-specific guidance, the authentication protocol, and
discoverable-tool workflows. Don't naively duplicate that content.

What works:

- Restructure prose into decision trees with explicit binary checks.
- Add meta-instructions about how to reason: "before each tool call, state
  the policy clause it satisfies"; "after each KB search, list the
  documents you actually used".
- Add few-shot tool-call examples for tricky discoverable tools.

### 3. The reasoning loop (`HiveAgent._generate_next_message`)

You can rewrite this method entirely. Patterns to try:

- Self-verification: after the LLM proposes a tool call, run a cheap
  second pass that checks the call against the policy.
- Retry-on-tool-error with the error message included as context.
- Multi-step planning: an explicit plan → execute → check loop instead
  of one-shot generation.
- Authentication state tracking: a flag in `state` so the agent stops
  trying to verify after success.

You can subclass `LLMAgentState` and add fields if you need cross-turn state.

---

## What you cannot edit

- `eval/eval.sh`, `eval/run_eval.py`, `prepare.sh`
- Any file inside `tau3-bench/`
- `AGENT_LLM`, `USER_LLM`, temperature (0.0), or seed (300) — these are
  fixed by the eval harness.

You also cannot create helper modules — keep all code inside `agent.py`.
This avoids merge conflicts when multiple agents iterate in parallel and
keeps every commit a single-file diff.

---

## Output format

`eval/eval.sh` prints this block at the end:

```
---
pass_at_1:        0.1234
correct:          12
total:            97
cost_usd:         5.67
retrieval:        bm25_grep
```

`pass_at_1` is the optimization target. Higher is better.

---

## Logging results

Append every iteration to `results.tsv` (do not commit it):

```
commit	pass_at_1	cost_usd	mode	retrieval	status	description
a1b2c3d	0.1500	0.42	fast	bm25_grep	keep	baseline
b2c3d4e	0.1500	0.41	fast	bm25_grep	revert	added few-shot — no change
c3d4e5f	0.2000	0.55	fast	openai_embeddings_grep	keep	switched retrieval
d4e5f6g	0.2200	2.31	full	openai_embeddings_grep	keep	gated on full split
```

Status: `keep`, `revert`, or `crash`.

---

## The experiment loop

LOOP FOREVER:

1. **THINK** — read `results.tsv` and the per-task PASS/FAIL breakdown
   from the last run. Form one specific hypothesis.
2. **EDIT** — make one focused change in `agent.py`.
3. **RUN** — `bash eval/eval.sh > run.log 2>&1`
4. **CHECK** — `grep "^pass_at_1:" run.log`. If empty the run crashed —
   `tail -n 50 run.log` for the stack trace.
5. **GATE** — if it improved on fast, run `EVAL_MODE=full bash eval/eval.sh`
   to confirm on all 97 tasks before committing.
6. **REVIEW** — for failing tasks, read the trace files in
   `tau3-bench/data/simulations/hive_fast/` (or `hive_full/`).
7. **COMMIT** — if it improved, `git add agent.py && git commit -m "..."`.
   If not, `git reset --hard HEAD~1`.
8. **RECORD** — append to `results.tsv` (do not commit `results.tsv`).
9. **REPEAT** — go to step 1.

---

## Strategy notes

- Always run a baseline before changing anything, then change one thing
  at a time.
- Read the FAILURES, not the passes. Per-task PASS/FAIL is printed by the
  eval; trace files live under `tau3-bench/data/simulations/`.
- `golden_retrieval` is a diagnostic. Run it once: the gap between your
  golden score and your real score is how much retrieval is hurting you.
  If both are low, the problem is reasoning, not search.
- Combine retrieval changes with prompt changes — a new variant often
  needs a new prompt structure to be effective.
- A change that gains 1/20 on fast (5 percentage points) is likely noise.
  Promote to `full` before celebrating.
- Cost matters less than score. Optimize for pass^1.

NEVER STOP. Once the loop begins, do not pause to ask. The loop runs until
interrupted.
