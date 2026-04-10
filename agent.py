"""Banking customer service agent for tau3-bench banking_knowledge.

Edit this file to maximize pass^1. Everything you can change is here:

  - RETRIEVAL_VARIANT / RETRIEVAL_KWARGS — which retrieval pipeline the
    framework wires up before the agent runs.
  - AGENT_INSTRUCTION — the prose instructions wrapped around the policy.
  - SYSTEM_PROMPT_TEMPLATE — how policy + instructions are assembled.
  - HiveAgent.system_prompt — override to restructure the system prompt.
  - HiveAgent._generate_next_message — override to add reasoning patterns,
    retries, self-verification, etc.

The eval harness imports this module and calls create_agent().
"""

from __future__ import annotations

from typing import List, Optional

from tau2.agent.llm_agent import LLMAgent, LLMAgentState
from tau2.agent.base_agent import ValidAgentInputMessage
from tau2.data_model.message import (
    AssistantMessage,
    Message,
    MultiToolMessage,
    SystemMessage,
)
from tau2.environment.tool import Tool
from tau2.utils.llm_utils import generate


# ── Retrieval configuration ──────────────────────────────────────────────────
#
# Selects how the agent accesses the knowledge base. The framework wires up
# tools and prompt templates from this value BEFORE the agent runs.
#
# Available variants (only those usable with OPENAI_API_KEY are listed —
# qwen_* variants require OPENROUTER_API_KEY and are unsupported):
#
#   No-retrieval baselines:
#     "no_knowledge"          — no KB tools
#     "full_kb"               — entire KB inlined in the system prompt
#     "golden_retrieval"      — oracle: only required docs in prompt (diagnostic only)
#
#   Sparse:
#     "bm25"                  — BM25 keyword search via KB_search tool
#     "bm25_grep"             — BM25 + grep tool
#     "bm25_reranker"         — BM25 + LLM reranker
#     "bm25_reranker_grep"    — BM25 + reranker + grep
#
#   Dense (OpenAI embeddings):
#     "openai_embeddings"
#     "openai_embeddings_grep"
#     "openai_embeddings_reranker"
#     "openai_embeddings_reranker_grep"
#
#   Tool-based:
#     "grep_only"             — just a grep tool
#     "terminal_use"          — read-only shell sandbox (cat, grep, find, ls, …)
#     "terminal_use_write"    — shell sandbox with write access
#
# RETRIEVAL_KWARGS overrides knobs like top_k or reranker_min_score.
# Examples:
#   {"top_k": 15}
#   {"top_k": 10, "reranker_min_score": 4}
#
RETRIEVAL_VARIANT: str = "bm25_grep"
RETRIEVAL_KWARGS: dict = {}


# ── System prompt — the main lever for performance ───────────────────────────
#
# The domain_policy passed to this agent is NOT empty. It is a fully assembled
# template that already includes:
#   1. Rho-Bank policy header (don't make up policies, transfer rules, etc.)
#   2. A retrieval-specific instruction (e.g. "use the KB_search tool")
#   3. Authentication protocol (verify 2 of 4: DOB, email, phone, address)
#   4. Discoverable tool workflows (how user/agent tools work)
#
# Don't blindly duplicate that content here. Focus on RESTRUCTURING how the
# information is presented (decision trees, numbered steps, explicit binary
# checks) and on adding meta-instructions about HOW to reason and verify.

AGENT_INSTRUCTION = """
You are a customer service agent that helps the user according to the <policy> provided below.
In each turn you can either:
- Send a message to the user.
- Make a tool call.
You cannot do both at the same time.

Try to be helpful and always follow the policy. Always make sure you generate valid JSON only.
""".strip()


SYSTEM_PROMPT_TEMPLATE = """
<instructions>
{agent_instruction}
</instructions>
<policy>
{domain_policy}
</policy>
""".strip()


# ── The agent ────────────────────────────────────────────────────────────────


class HiveAgent(LLMAgent[LLMAgentState]):
    """Banking customer service agent under optimization.

    Subclasses tau2-bench's LLMAgent so all the standard plumbing (registry,
    runner, evaluator) keeps working. Override anything you need to.
    """

    def __init__(
        self,
        tools: List[Tool],
        domain_policy: str,
        llm: str,
        llm_args: Optional[dict] = None,
    ):
        super().__init__(
            tools=tools,
            domain_policy=domain_policy,
            llm=llm,
            llm_args=llm_args,
        )

    @property
    def system_prompt(self) -> str:
        return SYSTEM_PROMPT_TEMPLATE.format(
            agent_instruction=AGENT_INSTRUCTION,
            domain_policy=self.domain_policy,
        )

    def get_init_state(
        self, message_history: Optional[list[Message]] = None
    ) -> LLMAgentState:
        return LLMAgentState(
            system_messages=[SystemMessage(role="system", content=self.system_prompt)],
            messages=list(message_history or []),
        )

    def _generate_next_message(
        self,
        message: ValidAgentInputMessage,
        state: LLMAgentState,
    ) -> AssistantMessage:
        """Generate the next assistant message.

        Override this method to add reasoning patterns: chain-of-thought,
        self-verification, retry-on-tool-error, multi-step planning, etc.

        The default implementation appends the incoming message and calls
        the LLM in one shot.
        """
        if isinstance(message, MultiToolMessage):
            state.messages.extend(message.tool_messages)
        else:
            state.messages.append(message)

        messages = state.system_messages + state.messages
        return generate(
            model=self.llm,
            tools=self.tools,
            messages=messages,
            call_name="agent_response",
            **self.llm_args,
        )


# ── Factory (called by eval/run_eval.py) ─────────────────────────────────────


def create_agent(tools, domain_policy, **kwargs) -> HiveAgent:
    """Factory function — registered with tau2's agent registry."""
    return HiveAgent(
        tools=tools,
        domain_policy=domain_policy,
        llm=kwargs.get("llm"),
        llm_args=kwargs.get("llm_args"),
    )
