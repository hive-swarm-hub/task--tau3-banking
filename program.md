# tau3-banking

Improve a banking customer service agent evaluated on the tau3-bench banking_knowledge benchmark. Score = pass@1 (fraction of tasks where all required database updates match the gold standard).

## Setup

1. **Read the in-scope files**:
   - `agent.py` — the banking agent implementation. You modify this.
   - `eval/eval.sh` — runs evaluation against 25 tasks. Do not modify.
   - `prepare.sh` — clones tau3-bench and installs dependencies. Do not modify.
2. **Run prepare**: `bash prepare.sh` to clone tau3-bench and install dependencies.
3. **Verify setup**: Check that `tau3-bench/` exists and contains the tau3-bench framework.
4. **Initialize results.tsv**: Create `results.tsv` with just the header row.
5. **Run baseline**: `bash eval/eval.sh` to establish the starting score.

Use `SAMPLE_FRAC=0.2 bash eval/eval.sh` to run on ~5 tasks for fast iteration. Use `SAMPLE_FRAC=1.0` (default) for full evaluation. Use `MAX_CONCURRENCY=4` if you hit rate limits (default is 16, which can trigger 429 errors with mini-class models).

## The benchmark

The tau3-bench banking_knowledge domain tests an agent's ability to act as a banking customer service representative. The agent converses with a simulated user (powered by gpt-4.1), searches a knowledge base of ~700 documents covering banking products and policies, reasons over complex interdependent policies, and executes multi-step tool calls to resolve customer requests. There are 97 total tasks; the eval runs 25 representative ones. Tasks include opening accounts, disputing transactions, handling referrals, and more. Success requires getting the final database state exactly right.

## Experimentation

**What you CAN do:**
- Modify `agent.py` — change the agent class, system prompt, retrieval strategy, reasoning approach, tool use patterns, error handling, etc.
- Add helper Python modules that `agent.py` imports (e.g., `prompts.py`, `retrieval.py`, `utils.py`).
- Change the `RETRIEVAL_VARIANT` and `RETRIEVAL_KWARGS` in `agent.py`. Available retrieval configs:
  - `bm25` — offline BM25 keyword search via `KB_search` tool
  - `openai_embeddings` — embedding-based search via `KB_search`
  - `qwen_embeddings` — embedding search via OpenRouter (needs `OPENROUTER_API_KEY`)
  - `grep_only` — grep-based search via `grep` tool
  - `full_kb` — entire knowledge base in context (no search tool)
  - `no_knowledge` — no knowledge base access
  - `golden_retrieval` — oracle retrieval (for reference only)
- Implement advanced patterns: ReAct, chain-of-thought, multi-step verification, adaptive retrieval.

**What you CANNOT do:**
- Modify `eval/`, `prepare.sh`, or test data.
- Change the agent LLM from `openai/gpt-5.4-mini`.
- Change the user simulator LLM from `openai/gpt-4.1`.
- Change the agent temperature from `0.0` or seed from `300`.
- Use terminal/shell-based retrieval configs (`terminal_use`, `terminal_use_write`).
- Hardcode answers to specific task IDs.

**The goal: maximize pass_at_1.** This is the fraction of the 25 eval tasks where the agent's final database state exactly matches the gold standard. Higher is better. Range: 0.0 to 1.0.

**Simplicity criterion**: All else being equal, prefer fewer lines of code and shorter system prompts. Verbose prompts hurt small models — be specific and concise.

## Understanding the agent environment

The `domain_policy` string passed to your agent is NOT empty — it is a fully assembled prompt built from template files. For the `bm25` variant, it includes:

1. **Policy header** (`tau3-bench/data/tau2/domains/banking_knowledge/prompts/components/policy_header.md`): Rho-Bank customer service guidelines — don't make up policies, use `get_current_time()`, transfer to human only as last resort, don't leak internal info.
2. **Retrieval instruction**: "Search the knowledge base using the provided `KB_search` tool."
3. **Additional instructions** (`tau3-bench/data/tau2/domains/banking_knowledge/prompts/components/additional_instructions.md`): Full discoverable tool workflows (user tools and agent tools), authentication protocol (verify 2 of 4: DOB, email, phone, address), verification logging.

Your agent already receives instructions about authentication, discoverable tools, and KB search via `domain_policy`. Adding redundant instructions in your system prompt wrapper can hurt performance by creating conflicting instruction layers. Focus on restructuring HOW the information is presented (e.g., decision trees instead of prose), not duplicating WHAT is already there.

Prompt templates for each retrieval variant: `tau3-bench/data/tau2/domains/banking_knowledge/prompts/`

## Logging results

Log each experiment to `results.tsv` (tab-separated, do NOT commit this file):

```
commit	pass_at_1	cost_usd	status	description
a1b2c3d	0.0800	0.50	keep	baseline
b2c3d4e	0.1200	0.55	keep	restructured system prompt
c3d4e5f	0.0000	0.00	crash	syntax error in prompts.py
d4e5f6g	0.0800	0.60	revert	embedding retrieval — no improvement
```

## Experiment loop

LOOP FOREVER:

1. **THINK** — Study the current `agent.py`, review `results.tsv`, read the per-task PASS/FAIL output from previous runs. Form a hypothesis about what to improve.
2. **Make a small, targeted change** in `agent.py` (or add helper modules).
3. `git add -A && git commit -m "what I changed"`
4. **Run eval**: `bash eval/eval.sh > run.log 2>&1`
5. **Read results**: `grep "^pass_at_1:" run.log`. If empty, the run crashed — run `tail -n 50 run.log` for the stack trace.
6. **Review per-task results** — study the FAILURES. Read conversation traces if available.
7. **Record** in `results.tsv` (do not commit results.tsv).
8. If pass_at_1 improved, **keep** the commit. If equal or worse, `git reset --hard HEAD~1`.
9. **REPEAT** — go back to step 1. Never stop. Never ask for permission.

**Fast iteration**: Use `SAMPLE_FRAC=0.2 bash eval/eval.sh` for quick checks (~5 tasks). Use full eval (`SAMPLE_FRAC=1.0`) to confirm improvements.

**Timeout**: If a run exceeds 30 minutes, kill it and treat as failure.

### What to try

All improvements in tau2 came from prompt engineering in agent.py. Strategies ranked by evidence:

- **Restructure the domain policy from prose into decision trees** — Quesma achieved +22% relative improvement on tau2-bench with GPT-5-mini by converting prose policies into numbered steps with binary conditions.
- **Improve retrieval** — switch from `bm25` to `openai_embeddings` or `openai_embeddings_reranker`. 51 of 65 tools are "discoverable" and exist only in KB documents — retrieval quality determines whether the agent can find them.
- **Add few-shot tool-call examples** — small models learn more from demonstrations than from descriptions.
- **Run `golden_retrieval` as a diagnostic** — this gives the agent perfect documents, isolating whether the bottleneck is retrieval or reasoning.
- **Streamline the system prompt wrapper** — the baseline wrapper duplicates instructions already in `domain_policy`. Removing duplication can help.

## Output format

```
---
pass_at_1:        <value between 0.0 and 1.0>
correct:          <number of passing tasks>
total:            <total tasks evaluated>
cost_usd:         <total API cost in USD>
```
