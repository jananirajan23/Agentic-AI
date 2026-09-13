"""
Unit tests for agents/architecture_structure_agent.py — the OCR/vision
merge logic is tested as pure functions; the OCR engine and the Groq
vision call are mocked out.
"""

import agents.architecture_structure_agent as arch


def test_filter_ocr_labels_drops_noise():
    labels = ["Parser", "->", "1", "2", "DB", "-", "Report Output"]
    filtered = arch._filter_ocr_labels(labels)
    assert filtered == ["Parser", "DB", "Report Output"]


def test_merge_components_dedupes_case_insensitively():
    vision = ["Parser", "Scoring Engine"]
    ocr = ["parser", "Report Output", "ScoringEngine"]
    merged = arch._merge_components(vision, ocr)
    assert merged == ["Parser", "Scoring Engine", "Report Output"]
    # "ScoringEngine" (no space) is treated as a substring-ish duplicate of
    # "Scoring Engine" only if one contains the other; here it isn't a
    # substring, so it should still be added.


def test_merge_components_keeps_vision_order_first():
    vision = ["Parser", "Scoring Engine"]
    ocr = ["Notifier"]  # a genuinely new label, not noise, not a duplicate
    assert arch._merge_components(vision, ocr) == ["Parser", "Scoring Engine", "Notifier"]


def test_score_architecture_no_readings():
    result = arch.score_architecture([])
    assert result["score"] == 0
    assert "No diagram images" in result["flags"][0]


def test_score_architecture_penalizes_missing_components():
    readings = [
        {
            "components": ["Parser"],
            "data_flow": [],
            "missing_vs_problem": ["Notification Module"],
            "notes": "",
            "image_path": "diagram.png",
        }
    ]
    result = arch.score_architecture(readings)
    assert result["score"] == 90  # 100 - MISSING_COMPONENT_PENALTY(10) * 1
    assert any("Notification Module" in f for f in result["flags"])


def test_score_architecture_zero_components_penalty():
    readings = [{"components": [], "data_flow": [], "missing_vs_problem": [], "notes": "blank page", "image_path": "x.png"}]
    result = arch.score_architecture(readings)
    assert result["score"] == 60  # 100 - ZERO_COMPONENT_PENALTY(40)


def test_run_no_images_returns_zero():
    result = arch.run({"diagram_image_paths": [], "problem_statement": ""})
    assert result["architecture_score"] == 0
    assert result["diagram_components"] == []


def test_run_without_groq_key_still_uses_ocr(monkeypatch, mocker):
    monkeypatch.setattr(arch.config, "GROQ_API_KEY", "")
    mocker.patch("agents.architecture_structure_agent.ocr_available", return_value=True)
    mocker.patch(
        "agents.architecture_structure_agent.extract_text_labels",
        return_value=["Parser", "Scoring Engine"],
    )

    result = arch.run({"diagram_image_paths": ["diagram.png"], "problem_statement": ""})

    assert result["architecture_score"] == 0
    assert "GROQ_API_KEY" in result["architecture_flags"][0]
    assert "Parser" in result["diagram_components"]
    assert "Scoring Engine" in result["diagram_components"]


def test_run_merges_vision_and_ocr(monkeypatch, mocker):
    monkeypatch.setattr(arch.config, "GROQ_API_KEY", "fake-key-for-this-test")
    mocker.patch("agents.architecture_structure_agent.ocr_available", return_value=True)
    mocker.patch(
        "agents.architecture_structure_agent.extract_text_labels",
        return_value=["Parser", "Extra Label"],
    )
    mocker.patch(
        "agents.architecture_structure_agent.read_diagram",
        return_value={
            "components": ["Parser", "Scoring Engine"],
            "data_flow": [],
            "missing_vs_problem": [],
            "notes": "",
            "image_path": "diagram.png",
        },
    )

    result = arch.run({"diagram_image_paths": ["diagram.png"], "problem_statement": "x"})

    assert result["diagram_components"] == ["Parser", "Scoring Engine", "Extra Label"]
    assert result["ocr_labels"] == ["Parser", "Extra Label"]
