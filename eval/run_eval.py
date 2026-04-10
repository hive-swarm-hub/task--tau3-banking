"""Evaluate agent.py on tau3-bench banking_knowledge."""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Make agent.py importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent import RETRIEVAL_KWARGS, RETRIEVAL_VARIANT, create_agent  # noqa: E402

from tau2.data_model.simulation import TextRunConfig  # noqa: E402
from tau2.metrics.agent_metrics import compute_metrics  # noqa: E402
from tau2.registry import registry  # noqa: E402
from tau2.run import run_domain  # noqa: E402

EVAL_MODE = os.environ.get("EVAL_MODE", "fast").strip().lower()
AGENT_LLM = os.environ.get("AGENT_LLM", "openai/gpt-5.4-mini")
USER_LLM = os.environ.get("USER_LLM", "openai/gpt-4.1")
MAX_CONCURRENCY = int(os.environ.get("MAX_CONCURRENCY", "8"))
MAX_STEPS = int(os.environ.get("MAX_STEPS", "200"))
SEED = int(os.environ.get("SEED", "300"))

# 20 task IDs evenly spread across the 97 banking_knowledge tasks. Used by
# fast mode for quick iteration. Fixed for reproducibility.
FAST_TASK_IDS = [
    "task_001", "task_006", "task_014", "task_019", "task_024",
    "task_029", "task_035", "task_040", "task_046", "task_051",
    "task_056", "task_061", "task_066", "task_071", "task_076",
    "task_081", "task_086", "task_091", "task_096", "task_101",
]

MODES = {
    "fast":   {"task_ids": FAST_TASK_IDS, "num_trials": 1},
    "full":   {"task_ids": None,          "num_trials": 1},
    "submit": {"task_ids": None,          "num_trials": 4},
}


def main() -> int:
    if EVAL_MODE not in MODES:
        print(f"ERROR: unknown EVAL_MODE={EVAL_MODE!r}. Use: {', '.join(MODES)}", file=sys.stderr)
        return 2
    mode = MODES[EVAL_MODE]

    if registry.get_agent_factory("hive_agent") is None:
        registry.register_agent_factory(create_agent, "hive_agent")

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
        save_to=f"hive_{EVAL_MODE}",
        retrieval_config=RETRIEVAL_VARIANT,
        retrieval_config_kwargs=RETRIEVAL_KWARGS or None,
        log_level="WARNING",
    )

    results = run_domain(config)
    metrics = compute_metrics(results)
    pass_at_1 = metrics.pass_hat_ks.get(1, 0.0)
    total = metrics.total_tasks
    correct = round(pass_at_1 * total) if total else 0
    cost = metrics.avg_agent_cost * metrics.total_simulations

    # Per-task pass/fail breakdown
    print("\n=== Per-task results ===", file=sys.stderr)
    by_task: dict[str, list[float]] = {}
    for sim in results.simulations:
        if sim.reward_info:
            by_task.setdefault(str(sim.task_id), []).append(float(sim.reward_info.reward))
    for task_id in sorted(by_task):
        rewards = by_task[task_id]
        passed = all(abs(r - 1.0) < 1e-6 for r in rewards)
        print(f"  {task_id}: {'PASS' if passed else 'FAIL'}", file=sys.stderr)

    print("\n---")
    print(f"pass_at_1:        {pass_at_1:.4f}")
    print(f"correct:          {correct}")
    print(f"total:            {total}")
    print(f"cost_usd:         {cost:.4f}")
    print(f"retrieval:        {RETRIEVAL_VARIANT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
