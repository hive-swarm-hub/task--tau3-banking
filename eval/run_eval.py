"""Evaluate agent.py on tau3-bench banking_knowledge."""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Make agent.py importable when run from anywhere
TASK_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TASK_DIR))

from agent import RETRIEVAL_KWARGS, RETRIEVAL_VARIANT, create_agent  # noqa: E402

from tau2.data_model.simulation import TextRunConfig  # noqa: E402
from tau2.metrics.agent_metrics import compute_metrics  # noqa: E402
from tau2.registry import registry  # noqa: E402
from tau2.run import run_domain  # noqa: E402


# ── Config ───────────────────────────────────────────────────────────────────

EVAL_MODE = os.environ.get("EVAL_MODE", "fast").strip().lower()
AGENT_LLM = os.environ.get("AGENT_LLM", "openai/gpt-5.4-mini")
USER_LLM = os.environ.get("USER_LLM", "openai/gpt-4.1")
MAX_CONCURRENCY = int(os.environ.get("MAX_CONCURRENCY", "8"))
MAX_STEPS = int(os.environ.get("MAX_STEPS", "200"))
SEED = int(os.environ.get("SEED", "300"))

# 20 task IDs, evenly spread across the 97 banking_knowledge tasks (every 5th).
# Used for fast iteration. Fixed for reproducibility — same set every run.
FAST_TASK_IDS = [
    "task_001", "task_006", "task_014", "task_019", "task_024",
    "task_029", "task_035", "task_040", "task_046", "task_051",
    "task_056", "task_061", "task_066", "task_071", "task_076",
    "task_081", "task_086", "task_091", "task_096", "task_101",
]

MODE_CONFIG = {
    "fast":   {"task_ids": FAST_TASK_IDS, "num_trials": 1, "save_to": "hive_fast"},
    "full":   {"task_ids": None,          "num_trials": 1, "save_to": "hive_full"},
    "submit": {"task_ids": None,          "num_trials": 4, "save_to": "hive_submit"},
}


def main() -> int:
    if EVAL_MODE not in MODE_CONFIG:
        print(f"ERROR: unknown EVAL_MODE={EVAL_MODE!r}. "
              f"Use one of: {', '.join(MODE_CONFIG)}", file=sys.stderr)
        return 2

    mode = MODE_CONFIG[EVAL_MODE]

    # Register the agent factory
    if registry.get_agent_factory("hive_agent") is None:
        registry.register_agent_factory(create_agent, "hive_agent")

    print(f"=== tau3-banking eval ({EVAL_MODE}) ===", file=sys.stderr)
    print(f"  agent_llm:          {AGENT_LLM}", file=sys.stderr)
    print(f"  user_llm:           {USER_LLM}", file=sys.stderr)
    print(f"  retrieval_variant:  {RETRIEVAL_VARIANT}", file=sys.stderr)
    print(f"  retrieval_kwargs:   {RETRIEVAL_KWARGS or '{}'}", file=sys.stderr)
    print(f"  num_trials:         {mode['num_trials']}", file=sys.stderr)
    print(f"  max_concurrency:    {MAX_CONCURRENCY}", file=sys.stderr)
    if mode["task_ids"] is not None:
        print(f"  num_tasks:          {len(mode['task_ids'])}", file=sys.stderr)
    else:
        print(f"  num_tasks:          all (97)", file=sys.stderr)
    print("", file=sys.stderr)

    config = TextRunConfig(
        domain="banking_knowledge",
        agent="hive_agent",
        llm_agent=AGENT_LLM,
        llm_args_agent={"temperature": 0.0, "seed": SEED},
        user="user_simulator",
        llm_user=USER_LLM,
        llm_args_user={"temperature": 0.0, "seed": SEED},
        num_trials=mode["num_trials"],
        max_concurrency=MAX_CONCURRENCY,
        max_steps=MAX_STEPS,
        seed=SEED,
        task_ids=mode["task_ids"],
        save_to=mode["save_to"],
        retrieval_config=RETRIEVAL_VARIANT,
        retrieval_config_kwargs=RETRIEVAL_KWARGS or None,
        log_level="WARNING",
    )

    results = run_domain(config)
    metrics = compute_metrics(results)

    pass_at_1 = metrics.pass_hat_ks.get(1, 0.0)
    total_tasks = metrics.total_tasks
    correct = round(pass_at_1 * total_tasks) if total_tasks else 0
    cost_usd = metrics.avg_agent_cost * metrics.total_simulations

    # Per-task pass/fail breakdown
    print("\n=== Per-task results ===", file=sys.stderr)
    by_task: dict[str, list[float]] = {}
    for sim in results.simulations:
        if not sim.reward_info:
            continue
        by_task.setdefault(str(sim.task_id), []).append(float(sim.reward_info.reward))
    for task_id in sorted(by_task):
        rewards = by_task[task_id]
        all_pass = all(abs(r - 1.0) < 1e-6 for r in rewards)
        status = "PASS" if all_pass else "FAIL"
        if len(rewards) > 1:
            print(f"  {task_id}: {status} (rewards={rewards})", file=sys.stderr)
        else:
            print(f"  {task_id}: {status}", file=sys.stderr)

    # Summary block
    print("")
    print("---")
    print(f"pass_at_1:        {pass_at_1:.4f}")
    print(f"correct:          {correct}")
    print(f"total:            {total_tasks}")
    print(f"cost_usd:         {cost_usd:.4f}")
    print(f"retrieval:        {RETRIEVAL_VARIANT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
