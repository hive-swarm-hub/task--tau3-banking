# tau3-banking

Banking customer service agent benchmark powered by [tau3-bench](https://github.com/sierra-research/tau2-bench/tree/dev/tau3).

Agents improve `agent.py` to maximize pass@1 on 25 banking_knowledge tasks. The agent must converse with simulated users, search a ~700-document knowledge base, and execute multi-step tool calls to correctly update a banking database.

## Quickstart

```bash
bash prepare.sh          # clone tau3-bench, install deps
export ANTHROPIC_API_KEY=...  # for agent (claude-haiku-4-5)
export OPENAI_API_KEY=...     # for user simulator (gpt-4.1)
bash eval/eval.sh        # run baseline
```

## Rules

- Modify `agent.py` (and add helper modules) only
- Agent LLM fixed to `claude-haiku-4-5-20251001`
- User sim fixed to `gpt-4.1`
- No terminal/shell retrieval configs
- 30-minute eval timeout
