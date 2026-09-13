"""
Shared sentence-embedding helper for the Architecture-Modules Alignment
Agent (Ch.4.3 / Ch.5.1 / Ch.7.1 / Ch.8.2 of the project requirements all
call for "embeddings and semantic similarity", not LLM judgement alone).

The model is loaded lazily and cached at module level — `sentence-
transformers` + `torch` are a substantial import, and most FastAPI worker
processes only need this once per lifetime, not once per request.
"""

from functools import lru_cache
from typing import List

import numpy as np

import config

_MODEL = None
_LOAD_ERROR: str | None = None


def _get_model():
    """Returns the cached SentenceTransformer instance, or None if the
    library/model isn't available (degrades gracefully, same pattern as
    the Groq-key checks elsewhere in this codebase)."""
    global _MODEL, _LOAD_ERROR
    if _MODEL is not None or _LOAD_ERROR is not None:
        return _MODEL
    try:
        from sentence_transformers import SentenceTransformer

        _MODEL = SentenceTransformer(config.EMBEDDING_MODEL)
    except Exception as e:  # pragma: no cover - exercised via mocking in tests
        _LOAD_ERROR = str(e)
        _MODEL = None
    return _MODEL


def embeddings_available() -> bool:
    return _get_model() is not None


def embed(texts: List[str]) -> "np.ndarray | None":
    """Embeds a list of strings. Returns an (N, D) float32 array, or None
    if the embedding model could not be loaded."""
    model = _get_model()
    if model is None or not texts:
        return None
    return model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)


def cosine_similarity_matrix(a: "np.ndarray", b: "np.ndarray") -> "np.ndarray":
    """a: (N, D), b: (M, D), both L2-normalized (as `embed` returns them) ->
    (N, M) cosine similarity matrix. Plain dot product since the vectors
    are already unit-normalized."""
    return a @ b.T


@lru_cache(maxsize=1)
def load_error() -> str | None:
    """Exposed for diagnostics/flags — populated only after the first
    failed load attempt."""
    _get_model()
    return _LOAD_ERROR
