"""TokenTracker — per-run LLM token consumption tracker.

Tracks cumulative prompt and completion tokens for a single DS-STAR agent run.
Provides an ``over_budget()`` check that the orchestrator calls before each
round to enforce the ``MAX_TOKENS_PER_RUN`` budget declared in config.py.

Usage in the orchestrator::

    token_tracker = TokenTracker(budget=MAX_TOKENS_PER_RUN)

    # Pass the tracker when calling an agent method:
    result = await self.planner.create_plan(query, desc, token_tracker=token_tracker)

    # Before starting a new round:
    if token_tracker.over_budget():
        yield _event("warning", message="Token budget exceeded.")
        break

Design notes:
- All agents use ``.with_structured_output()`` chains, which return Pydantic
  objects rather than raw AIMessages, so ``usage_metadata`` is unavailable on
  the return value.
- Instead, each agent passes a ``TokenUsageCallback`` (defined here) via
  LangChain's ``RunnableConfig``.  The callback fires ``on_llm_end`` and reads
  ``token_usage`` from ``LLMResult.llm_output`` — the standard LangChain field
  populated by ChatNVIDIA / OpenAI-compatible endpoints.
- If a model does not return usage information, the callback is a safe no-op."""

import logging
from typing import Any, Dict, Optional

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult
from langchain_core.runnables import RunnableConfig

logger = logging.getLogger("uvicorn.info")


class TokenTracker:
    """Tracks cumulative LLM token usage for a single DS-STAR agent run.

    Attributes:
        budget: Maximum total tokens allowed for this run.
        prompt_tokens: Cumulative prompt (input) tokens consumed.
        completion_tokens: Cumulative completion (output) tokens consumed.
    """

    def __init__(self, budget: int = 50_000) -> None:
        self.budget = budget
        self.prompt_tokens: int = 0
        self.completion_tokens: int = 0

    # ── Properties ───────────────────────────────────────────────────────────

    @property
    def total_tokens(self) -> int:
        """Total tokens consumed (prompt + completion)."""
        return self.prompt_tokens + self.completion_tokens

    @property
    def remaining(self) -> int:
        """Tokens remaining before the budget is exhausted."""
        return max(0, self.budget - self.total_tokens)

    def over_budget(self) -> bool:
        """Returns True if the run has consumed at least ``budget`` tokens.

        Returns:
            bool: True when total_tokens >= budget AND budget > 0.
        """
        return self.budget > 0 and self.total_tokens >= self.budget

    # ── Recording ─────────────────────────────────────────────────────────────

    def record(self, prompt: int = 0, completion: int = 0) -> None:
        """Manually records token usage for one LLM call.

        Args:
            prompt: Prompt (input) tokens consumed by this call.
            completion: Completion (output) tokens consumed by this call.
        """
        self.prompt_tokens += max(0, prompt)
        self.completion_tokens += max(0, completion)
        logger.debug(
            "[TokenTracker] +%d prompt / +%d completion → total=%d / budget=%d",
            prompt,
            completion,
            self.total_tokens,
            self.budget,
        )

    def record_from_ai_message(self, message: Any) -> None:
        """Extracts and records token usage from a LangChain AIMessage.

        NIM endpoints return usage data in ``message.usage_metadata`` with the
        shape ``{"input_tokens": N, "output_tokens": M}``.

        This method is a safe no-op if ``usage_metadata`` is absent — e.g., when
        using models that do not return usage information, or when ``message`` is
        a Pydantic structured-output object rather than a raw AIMessage.

        Args:
            message: The AIMessage (or any object) returned by a chain call.
        """
        usage = getattr(message, "usage_metadata", None)
        if usage is None:
            return
        self.record(
            prompt=int(usage.get("input_tokens", 0)),
            completion=int(usage.get("output_tokens", 0)),
        )

    def record_from_dict(self, usage_dict: Dict[str, int]) -> None:
        """Records token usage from a plain usage dictionary.

        Useful when extracting tokens from LangChain callback metadata rather
        than directly from an AIMessage.

        Args:
            usage_dict: A dict with ``prompt_tokens`` and ``completion_tokens``
                keys — matching the LangChain ``LLMResult.llm_output`` shape.
        """
        self.record(
            prompt=int(usage_dict.get("prompt_tokens", 0)),
            completion=int(usage_dict.get("completion_tokens", 0)),
        )

    # ── Serialisation ─────────────────────────────────────────────────────────

    def summary(self) -> Dict[str, Any]:
        """Returns a serialisable summary of current token usage.

        Returns:
            Dict with prompt_tokens, completion_tokens, total_tokens,
            budget, remaining, and over_budget flag.
        """
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "budget": self.budget,
            "remaining": self.remaining,
            "over_budget": self.over_budget(),
        }

    def __repr__(self) -> str:
        return (
            f"TokenTracker(total={self.total_tokens}, "
            f"budget={self.budget}, remaining={self.remaining})"
        )


# ---------------------------------------------------------------------------
# LangChain callback — captures token usage from structured-output chains
# ---------------------------------------------------------------------------

class TokenUsageCallback(BaseCallbackHandler):
    """LangChain callback handler that records token usage into a TokenTracker.

    Works with ``.with_structured_output()`` chains where the chain return value
    is a Pydantic object, not a raw AIMessage (so ``usage_metadata`` is absent).
    Instead, usage is captured from ``LLMResult.llm_output["token_usage"]``,
    which ChatNVIDIA / OpenAI-compatible endpoints populate in ``on_llm_end``.

    Usage::

        callback = TokenUsageCallback(token_tracker)
        result = await chain.ainvoke(inputs, config={"callbacks": [callback]})

    Attributes:
        tracker: The ``TokenTracker`` instance to record into.
    """

    def __init__(self, tracker: TokenTracker) -> None:
        super().__init__()
        self.tracker = tracker

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """Reads token_usage from LLMResult and records into the tracker.

        Args:
            response: The LangChain LLMResult returned by the LLM call.
            **kwargs: Additional keyword arguments (ignored).
        """
        usage = (response.llm_output or {}).get("token_usage")
        if isinstance(usage, dict):
            self.tracker.record(
                prompt=int(usage.get("prompt_tokens", 0)),
                completion=int(usage.get("completion_tokens", 0)),
            )


def tracker_callback_config(tracker: Optional[TokenTracker]) -> RunnableConfig:
    """Builds a LangChain ``RunnableConfig`` carrying a ``TokenUsageCallback``.

    Pass the returned config to ``chain.ainvoke(inputs, config=...)`` inside
    each agent to automatically capture token usage without modifying agent
    return types.

    Args:
        tracker: Active ``TokenTracker`` for this run.  If ``None``, returns
            an empty config so callers need no conditional logic.

    Returns:
        ``RunnableConfig`` dict with a ``callbacks`` list, or empty dict.
    """
    if tracker is None:
        return {}
    return RunnableConfig(callbacks=[TokenUsageCallback(tracker)])
