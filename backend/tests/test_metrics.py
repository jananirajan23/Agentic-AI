"""Unit tests for agents/metrics.py (Ch.9.4/Ch.11.1 retrieval metrics)."""

import pytest

from agents.metrics import citation_resolution_rate, precision_at_k, recall_at_k


def test_precision_at_k_all_relevant():
    retrieved = ["a", "b", "c"]
    relevant = ["a", "b", "c", "d"]
    assert precision_at_k(retrieved, relevant, 3) == 1.0


def test_precision_at_k_partial():
    retrieved = ["a", "x", "b", "y"]
    relevant = ["a", "b"]
    assert precision_at_k(retrieved, relevant, 4) == 0.5


def test_precision_at_k_truncates_to_k():
    retrieved = ["a", "b", "x", "y", "z"]
    relevant = ["a", "b"]
    # Only the top 2 are considered even though 5 were retrieved.
    assert precision_at_k(retrieved, relevant, 2) == 1.0


def test_precision_at_k_rejects_non_positive_k():
    with pytest.raises(ValueError):
        precision_at_k(["a"], ["a"], 0)


def test_recall_at_k_finds_all():
    retrieved = ["x", "a", "b", "y"]
    relevant = ["a", "b"]
    assert recall_at_k(retrieved, relevant, 4) == 1.0


def test_recall_at_k_partial():
    retrieved = ["a", "x", "y"]
    relevant = ["a", "b"]
    assert recall_at_k(retrieved, relevant, 3) == 0.5


def test_recall_at_k_no_relevant_items():
    assert recall_at_k(["a", "b"], [], 2) == 0.0


def test_citation_resolution_rate():
    assert citation_resolution_rate(10, 8) == 0.8
    assert citation_resolution_rate(0, 0) == 0.0
    assert citation_resolution_rate(4, 0) == 0.0
    assert citation_resolution_rate(4, 4) == 1.0
