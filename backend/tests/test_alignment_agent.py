"""
Unit tests for agents/alignment_agent.py — the module-phrase splitter is
tested as a pure function; the embedding model and the Groq call are
mocked so the embeddings math (cosine similarity -> matched/unmatched) is
verified deterministically without downloading/running the real model.
"""

import numpy as np

import agents.alignment_agent as align


def test_split_module_phrases_line_based():
    text = "Parser Module - extracts sections.\nScoring Module - computes scores.\n\n"
    phrases = align.split_module_phrases(text)
    assert phrases == ["Parser Module - extracts sections.", "Scoring Module - computes scores."]


def test_split_module_phrases_falls_back_to_sentences_for_paragraphs():
    # Needs to exceed the 160-char per-line threshold to trigger the
    # sentence-splitting fallback instead of being kept as one phrase.
    long_line = "A" * 70 + ". " + "B" * 70 + ". " + "C" * 70 + "."
    phrases = align.split_module_phrases(long_line)
    assert len(phrases) == 3


def test_split_module_phrases_deduplicates_and_caps(monkeypatch):
    text = "\n".join([f"Module {i % 3}" for i in range(100)])
    phrases = align.split_module_phrases(text, max_phrases=5)
    assert len(phrases) <= 5


def _fake_embed(vectors_by_text):
    def embed(texts):
        return np.array([vectors_by_text[t] for t in texts], dtype=np.float32)

    return embed


def test_embedding_alignment_matches_and_flags_unmatched(mocker):
    # Three orthogonal axes so similarity is unambiguous: "Parser" points
    # exactly at "Parses the input" (sim 1.0); "Notifier" points at
    # neither module phrase (sim 0.0 to both) and should end up flagged.
    vectors = {
        "Parser": [1.0, 0.0, 0.0],
        "Notifier": [0.0, 1.0, 0.0],
        "Parses the input": [1.0, 0.0, 0.0],
        "Sends emails on completion": [0.0, 0.0, 1.0],
    }

    def fake_embed(texts):
        arr = np.array([vectors[t] for t in texts], dtype=np.float32)
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        norms[norms == 0] = 1
        return arr / norms

    mocker.patch("agents.alignment_agent.embeddings_available", return_value=True)
    mocker.patch("agents.alignment_agent.load_error", return_value=None)
    mocker.patch("agents.alignment_agent.embed", side_effect=fake_embed)

    result = align.embedding_alignment(["Parser", "Notifier"], ["Parses the input", "Sends emails on completion"])

    assert result["available"] is True
    assert result["score"] is not None
    assert any("Notifier" in f for f in result["flags"])


def test_embedding_alignment_unavailable(mocker):
    mocker.patch("agents.alignment_agent.embeddings_available", return_value=False)
    mocker.patch("agents.alignment_agent.load_error", return_value="sentence-transformers not installed")

    result = align.embedding_alignment(["Parser"], ["Parses the input"])
    assert result["available"] is False
    assert result["score"] is None
    assert "unavailable" in result["flags"][0]


def test_embedding_alignment_empty_inputs(mocker):
    mocker.patch("agents.alignment_agent.embeddings_available", return_value=True)
    result = align.embedding_alignment([], ["Parses the input"])
    assert result["score"] is None


def test_run_blends_embedding_and_llm_scores(monkeypatch, mocker):
    mocker.patch(
        "agents.alignment_agent.embedding_alignment",
        return_value={"available": True, "score": 80.0, "flags": ["embedding flag"]},
    )
    mocker.patch(
        "agents.alignment_agent.check_alignment",
        return_value={
            "score": 60,
            "in_diagram_not_in_text": ["Widget"],
            "in_text_not_in_diagram": [],
            "flags": ["llm flag"],
        },
    )

    result = align.run({"diagram_components": ["Widget"], "modules_text": "Some module text."})

    assert result["alignment_score"] == 70.0  # (80 + 60) / 2
    assert result["embedding_alignment_score"] == 80.0
    assert "embedding flag" in result["alignment_flags"]
    assert "llm flag" in result["alignment_flags"]
    assert any("Widget" in f for f in result["alignment_flags"])


def test_run_uses_embedding_score_alone_without_groq(monkeypatch, mocker):
    monkeypatch.setattr(align.config, "GROQ_API_KEY", "")
    mocker.patch(
        "agents.alignment_agent.embedding_alignment",
        return_value={"available": True, "score": 55.0, "flags": []},
    )

    result = align.run({"diagram_components": ["Widget"], "modules_text": "Some module text."})

    assert result["alignment_score"] == 55.0


def test_run_with_nothing_to_compare():
    result = align.run({"diagram_components": [], "modules_text": ""})
    assert result["alignment_score"] == 0
    assert "Neither diagram components nor module text" in result["alignment_flags"][0]
