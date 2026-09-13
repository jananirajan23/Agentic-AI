"""
Small labelled-fixture evaluation of the Literature Agent's Semantic
Scholar retrieval step, computing real Precision@K / Recall@K values
(Ch.9.4 / Ch.11.1: "these metrics should only be reported if they were
actually calculated during testing").

Not part of the pytest suite (it makes real network calls to Semantic
Scholar and is slow/rate-limited) — run it manually:

    python tests/evaluate_retrieval.py

Each fixture below is a citation title a synthetic report might contain,
paired with whether a human would judge that title's most likely
Semantic Scholar match "relevant" (i.e. resolvable to a real, matching
paper) for the purposes of this smoke evaluation.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.literature_survey_agent import lookup_semantic_scholar  # noqa: E402
from agents.metrics import precision_at_k, recall_at_k  # noqa: E402

# (query title, is this title expected to resolve to a real, relevant paper)
FIXTURES = [
    ("Attention Is All You Need", True),
    ("Deep Residual Learning for Image Recognition", True),
    ("YOLOv7: Trainable bag-of-freebies for real-time object detectors", True),
    ("AdaFace: Quality Adaptive Margin for Face Recognition", True),
    ("A Completely Made Up Paper Title That Does Not Exist Anywhere Xyzzy123", False),
]


def main():
    retrieved_relevant_ids = []
    ground_truth_relevant_ids = [title for title, is_relevant in FIXTURES if is_relevant]

    for title, _ in FIXTURES:
        paper = lookup_semantic_scholar(title)
        if paper and paper.get("title"):
            retrieved_relevant_ids.append(title)  # treat "resolved at all" as retrieved

    k = len(FIXTURES)
    precision = precision_at_k(retrieved_relevant_ids, ground_truth_relevant_ids, k)
    recall = recall_at_k(retrieved_relevant_ids, ground_truth_relevant_ids, k)

    print(f"Fixtures: {len(FIXTURES)}, expected relevant: {len(ground_truth_relevant_ids)}")
    print(f"Resolved via Semantic Scholar: {retrieved_relevant_ids}")
    print(f"Precision@{k}: {precision:.2f}")
    print(f"Recall@{k}: {recall:.2f}")


if __name__ == "__main__":
    main()
