"""
Retrieval-quality evaluation metrics (Ch.9.4 / Ch.11.1 of the
requirements: "Precision@K", "Recall@K" for the Literature Survey
Agent's Semantic Scholar retrieval step).

Deliberately pure, dependency-free functions: the requirements document
is explicit that "these metrics should only be reported if they were
actually calculated during testing" (Ch.11.1) — they're not wired into
the live per-report pipeline (a single student's citation list isn't a
labelled retrieval benchmark), but they ARE exercised, with a small
labelled fixture set, from backend/tests/test_metrics.py and
backend/tests/evaluate_retrieval.py so a real, measured value can be
quoted in Ch.11.3's results table instead of a placeholder.
"""

from typing import Sequence


def precision_at_k(retrieved: Sequence[str], relevant: Sequence[str], k: int) -> float:
    """Fraction of the top-k retrieved items that are actually relevant.

    `retrieved` is ranked (index 0 = top result); `relevant` is the set of
    ground-truth-relevant item ids/titles for this query.
    """
    if k <= 0:
        raise ValueError("k must be positive")
    top_k = retrieved[:k]
    if not top_k:
        return 0.0
    relevant_set = set(relevant)
    hits = sum(1 for item in top_k if item in relevant_set)
    return hits / len(top_k)


def recall_at_k(retrieved: Sequence[str], relevant: Sequence[str], k: int) -> float:
    """Fraction of all relevant items that show up in the top-k retrieved."""
    if k <= 0:
        raise ValueError("k must be positive")
    if not relevant:
        return 0.0
    top_k_set = set(retrieved[:k])
    relevant_set = set(relevant)
    hits = sum(1 for item in relevant_set if item in top_k_set)
    return hits / len(relevant_set)


def citation_resolution_rate(total_citations: int, resolved_citations: int) -> float:
    """The one retrieval-quality number the live pipeline *can* honestly
    report per-run without a labelled ground truth: what fraction of the
    citations a student wrote down were actually found on Semantic
    Scholar. Not Precision/Recall@K (no relevance judgement is made) but
    a real, measured retrieval-success rate."""
    if total_citations <= 0:
        return 0.0
    return round(resolved_citations / total_citations, 3)
