"""Observation truncation policy.

Sandbox output can be arbitrarily large. This module caps stdout and stderr
to a safe size before they are injected into LLM prompts.
"""

from __future__ import annotations

from vera_core.models.run import Observation

# Default caps
DEFAULT_STDOUT_CAP = 8_192  # 8 KB — enough for most outputs
DEFAULT_STDERR_CAP = 2_048  # 2 KB — keep errors concise


def truncate_observation(
    obs: Observation,
    stdout_cap: int = DEFAULT_STDOUT_CAP,
    stderr_cap: int = DEFAULT_STDERR_CAP,
) -> Observation:
    """Return a copy of the observation with output capped for prompt injection.

    Truncation is applied to stdout and stderr independently.
    The ``truncated`` flag is set to True if either was shortened.
    """
    original_stdout = obs.stdout
    original_stderr = obs.stderr

    truncated_stdout = _cap(obs.stdout, stdout_cap)
    truncated_stderr = _cap(obs.stderr, stderr_cap)
    was_truncated = len(original_stdout) > stdout_cap or len(original_stderr) > stderr_cap

    return obs.model_copy(
        update={
            "stdout": truncated_stdout,
            "stderr": truncated_stderr,
            "truncated": was_truncated or obs.truncated,
        }
    )


def _cap(text: str, max_chars: int) -> str:
    """Hard-cap a string, appending an indicator if truncated."""
    if len(text) <= max_chars:
        return text
    head = max_chars // 2
    tail = max_chars - head
    return text[:head] + f"\n\n... [TRUNCATED {len(text) - max_chars} chars] ...\n\n" + text[-tail:]


__all__ = ["truncate_observation", "DEFAULT_STDOUT_CAP", "DEFAULT_STDERR_CAP"]
