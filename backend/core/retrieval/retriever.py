"""Retriever — cosine-similarity embedding retrieval for large file sets.

When a session contains many uploaded files, feeding every file's full
content into the LLM context would exceed the token budget. The Retriever
addresses this by:

  1. Embedding the user query using a lightweight local embedding model.
  2. Embedding each file's text summary (produced by FileAnalyzerAgent).
  3. Computing cosine similarity between the query and each file summary.
  4. Returning the top-K most relevant file keys for the orchestrator to use.

Performance fixes applied:
  PERF-01: _cosine_similarity replaced with _cosine_similarity_batch() which
           uses a single numpy matrix multiply instead of pure-Python loops.
           For 100 files × 384 dims this is ~100-1000x faster.
  PERF-02: SentenceTransformer model is now a module-level singleton via
           _get_embed_model(). Model loads once at first call; all subsequent
           Retriever() instances share the cached reference with zero reload cost.

If ``sentence-transformers`` is not installed, the retriever gracefully falls
back to TF-IDF keyword overlap scoring, which is always available.
"""

import logging
import math
from typing import Any, Dict, List, Optional

logger = logging.getLogger("uvicorn.info")

try:
    import numpy as np
    _NUMPY_AVAILABLE = True
except ImportError:  # pragma: no cover
    _NUMPY_AVAILABLE = False

# Default embedding model (small, CPU-friendly, no API key required)
_DEFAULT_EMBED_MODEL = "all-MiniLM-L6-v2"
# Top-K files to return when the corpus is large
_DEFAULT_TOP_K = 10
# Only activate retrieval when file count exceeds this threshold
_RETRIEVAL_THRESHOLD = 8


# ---------------------------------------------------------------------------
# Module-level embedding model singleton (PERF-02)
# ---------------------------------------------------------------------------

_embed_model_cache: Dict[str, Any] = {}


def _get_embed_model(model_name: str) -> Optional[Any]:
    """Returns a cached SentenceTransformer instance for ``model_name``.

    Loads the model on first call and caches it at the module level.
    All subsequent ``Retriever()`` instantiations reuse the same shared
    instance — no repeated ~80 MB model loads per request.

    Args:
        model_name: Sentence-transformer model identifier.

    Returns:
        Loaded SentenceTransformer, or None if the library is not installed.
    """
    if model_name in _embed_model_cache:
        return _embed_model_cache[model_name]

    try:
        from sentence_transformers import SentenceTransformer  # pylint: disable=import-outside-toplevel
        model = SentenceTransformer(model_name)
        _embed_model_cache[model_name] = model
        logger.info(
            "[Retriever] Embedding model loaded (module singleton): %s", model_name
        )
        return model
    except ImportError:
        logger.warning(
            "[Retriever] sentence-transformers not installed — "
            "falling back to TF-IDF keyword scoring. "
            "Install with: pip install sentence-transformers"
        )
        _embed_model_cache[model_name] = None  # Cache the miss so we don't retry
        return None


# ---------------------------------------------------------------------------
# Cosine similarity — numpy batch version (PERF-01)
# ---------------------------------------------------------------------------

def _cosine_similarity_batch(
    query_vec: "np.ndarray",
    summary_vecs: "np.ndarray",
) -> "np.ndarray":
    """Vectorised cosine similarity between a query and all document vectors.

    Replaces the pure-Python per-file loop (38,400 float ops for 100 files ×
    384 dims) with a single BLAS-backed matrix multiply, giving a ~100-1000x
    speedup on typical corpora.

    Args:
        query_vec: Shape ``(D,)`` — query embedding.
        summary_vecs: Shape ``(N, D)`` — stacked document embeddings.

    Returns:
        Shape ``(N,)`` array of cosine similarity scores in ``[-1, 1]``.
    """
    dots = summary_vecs @ query_vec                                   # (N,)
    norms = np.linalg.norm(summary_vecs, axis=1) * np.linalg.norm(query_vec)
    norms = np.where(norms == 0.0, 1e-10, norms)                     # guard /0
    return dots / norms


def _cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """Pure-Python cosine similarity (fallback when numpy is absent).

    Args:
        vec_a: First embedding vector.
        vec_b: Second embedding vector.

    Returns:
        Cosine similarity score in [-1, 1].
    """
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


# ---------------------------------------------------------------------------
# TF-IDF fallback scorer
# ---------------------------------------------------------------------------

def _tfidf_score(query: str, text: str) -> float:
    """Computes a simple keyword overlap score as a fallback.

    Args:
        query: User query string.
        text: Document text to score.

    Returns:
        Float score based on keyword overlap (0.0 = no overlap).
    """
    query_words = set(query.lower().split())
    text_words = text.lower().split()
    if not text_words:
        return 0.0
    matches = sum(1 for w in text_words if w in query_words)
    return matches / len(text_words)


# ---------------------------------------------------------------------------
# Retriever
# ---------------------------------------------------------------------------

class Retriever:
    """Selects the top-K most relevant files for a query using embeddings.

    Uses sentence-transformers for embedding when available; falls back to
    TF-IDF keyword overlap when the library is not installed.

    The embedding model is shared at the module level (singleton) so that
    instantiating multiple Retriever objects per request has negligible cost.

    Attributes:
        _model_name: Sentence-transformer model name.
        _top_k: Maximum number of file summaries to return.
        _embed_model: Shared SentenceTransformer model (if available).
        _embed_available: True when the embedding path is usable.
    """

    def __init__(
        self,
        model_name: str = _DEFAULT_EMBED_MODEL,
        top_k: int = _DEFAULT_TOP_K,
    ) -> None:
        """Initialises the retriever.

        Args:
            model_name: Sentence-transformer model identifier.
            top_k: Maximum files to return per query.
        """
        self._model_name = model_name
        self._top_k = top_k
        # Reuse module-level singleton — zero cost if already loaded
        self._embed_model = _get_embed_model(model_name)
        self._embed_available = self._embed_model is not None

    def _embed(self, texts: List[str]) -> Any:
        """Produces embedding arrays for a list of texts.

        Returns raw numpy arrays (not .tolist()) so the batch cosine
        function can consume them without unnecessary conversion overhead.

        Args:
            texts: Strings to embed.

        Returns:
            Numpy array of shape (len(texts), D).
        """
        return self._embed_model.encode(texts, convert_to_numpy=True)

    def retrieve(
        self,
        query: str,
        file_summaries: Dict[str, str],
    ) -> Dict[str, str]:
        """Returns the top-K most relevant file summaries for the query.

        If the total file count is below ``_RETRIEVAL_THRESHOLD``, all files
        are returned unchanged (retrieval is a no-op for small corpora).

        Args:
            query: The user's natural language query.
            file_summaries: Mapping of ``{filename: summary_text}``.

        Returns:
            Filtered mapping of the top-K most relevant
            ``{filename: summary_text}`` entries.
        """
        if len(file_summaries) <= _RETRIEVAL_THRESHOLD:
            logger.info(
                "[Retriever] File count=%d ≤ threshold=%d — skipping retrieval.",
                len(file_summaries),
                _RETRIEVAL_THRESHOLD,
            )
            return file_summaries

        filenames = list(file_summaries.keys())
        summaries = list(file_summaries.values())

        if self._embed_available and self._embed_model is not None:
            # Batch embed query + all summaries in a single model.encode() call
            all_texts = [query] + summaries
            all_vecs = self._embed(all_texts)           # (N+1, D) numpy array
            query_vec = all_vecs[0]                     # (D,)
            summary_vecs = all_vecs[1:]                 # (N, D)

            if _NUMPY_AVAILABLE:
                scores = _cosine_similarity_batch(query_vec, summary_vecs).tolist()
            else:
                # Numpy arrays but no top-level numpy import (edge case)
                scores = [
                    _cosine_similarity(query_vec.tolist(), sv.tolist())
                    for sv in summary_vecs
                ]
            method = "embedding"
        else:
            # TF-IDF fallback
            scores = [_tfidf_score(query, s) for s in summaries]
            method = "tfidf"

        # Rank and return top-K
        ranked = sorted(
            zip(filenames, scores),
            key=lambda x: x[1],
            reverse=True,
        )
        top_k = min(self._top_k, len(ranked))
        selected = {fname: file_summaries[fname] for fname, _ in ranked[:top_k]}

        logger.info(
            "[Retriever] method=%s | total=%d → selected=%d files | "
            "top score=%.3f",
            method,
            len(file_summaries),
            top_k,
            ranked[0][1] if ranked else 0.0,
        )

        return selected

    def retrieve_combined_extractions(
        self,
        query: str,
        combined_extractions: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Wraps ``retrieve()`` to work directly with orchestrator context.

        The orchestrator's ``combined_extractions`` dict maps filenames to
        extraction result dicts (not plain strings). This helper extracts
        text summaries, runs retrieval, and returns the filtered extractions.

        Args:
            query: The user's natural language query.
            combined_extractions: Raw ``combined_extractions`` dict from
                the processing context.

        Returns:
            Filtered ``combined_extractions`` dict with only the top-K
            most relevant files.
        """
        # Build a summary string per file for scoring
        summaries: Dict[str, str] = {}
        for fname, extraction in combined_extractions.items():
            if isinstance(extraction, dict):
                parts = []
                for key in ("summary", "text", "description", "columns"):
                    val = extraction.get(key)
                    if val:
                        parts.append(str(val)[:500])
                summaries[fname] = " ".join(parts) or fname
            else:
                summaries[fname] = str(extraction)[:500]

        selected_names = set(self.retrieve(query, summaries).keys())
        return {
            fname: ext
            for fname, ext in combined_extractions.items()
            if fname in selected_names
        }
