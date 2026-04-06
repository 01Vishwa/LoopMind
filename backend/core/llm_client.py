"""NVIDIA NIM LLM factory — singleton ChatNVIDIA instances per model.

All DS-STAR agents import ``get_nim_llm()`` from this module.
Swapping models only requires changing the env var, not agent code.
"""

import logging

from langchain_nvidia_ai_endpoints import ChatNVIDIA

from core.config import NVIDIA_API_KEY, NIM_MODEL_DEFAULT, NIM_MODEL_CODER

logger = logging.getLogger("uvicorn.info")

# ---------------------------------------------------------------------------
# Module-level singleton cache: model_name → ChatNVIDIA instance
# ---------------------------------------------------------------------------
_llm_cache: dict[str, ChatNVIDIA] = {}


def get_nim_llm(
    model: str | None = None,
    temperature: float = 0.1,
) -> ChatNVIDIA:
    """Returns a cached ChatNVIDIA instance for the requested model.

    Args:
        model: NIM model identifier. Defaults to ``NIM_MODEL_DEFAULT``.
        temperature: Sampling temperature (lower = more deterministic).

    Returns:
        ChatNVIDIA: Authenticated, ready-to-use LLM instance.

    Raises:
        RuntimeError: If ``NVIDIA_API_KEY`` is not configured.
    """
    if not NVIDIA_API_KEY or NVIDIA_API_KEY == "your_nvidia_api_key_here":
        raise RuntimeError(
            "NVIDIA_API_KEY is not configured in backend/.env. "
            "Obtain a key at https://build.nvidia.com and set it there."
        )

    resolved_model = model or NIM_MODEL_DEFAULT
    cache_key = f"{resolved_model}:{temperature}"

    if cache_key not in _llm_cache:
        _llm_cache[cache_key] = ChatNVIDIA(
            model=resolved_model,
            api_key=NVIDIA_API_KEY,
            temperature=temperature,
        )
        logger.info(
            "[NIM] ChatNVIDIA initialised — model=%s, temp=%.2f",
            resolved_model,
            temperature,
        )

    return _llm_cache[cache_key]


def get_default_llm() -> ChatNVIDIA:
    """Convenience accessor for the default reasoning model.

    Returns:
        ChatNVIDIA: Default NIM LLM (meta/llama-3.1-70b-instruct by default).
    """
    return get_nim_llm(model=NIM_MODEL_DEFAULT)


def get_coder_llm() -> ChatNVIDIA:
    """Convenience accessor for the code-generation model.

    Returns:
        ChatNVIDIA: Coder NIM LLM (meta/codellama-70b-instruct by default).
    """
    return get_nim_llm(model=NIM_MODEL_CODER)
