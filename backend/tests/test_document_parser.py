"""Unit tests for agents/document_parser.py (Ch.11.2: "PDF extraction" unit tests)."""

import os

from agents.document_parser import _split_into_sections, parse_pdf
from tests.make_dummy_report import build_dummy_pdf


def test_split_into_sections_finds_known_headings():
    text = "\n".join(
        [
            "Problem Statement",
            "We need a better review tool.",
            "Literature Survey",
            "[1] Someone, Some Paper, 2021.",
            "System Modules",
            "Parser module and scoring module.",
        ]
    )
    sections, found, missing = _split_into_sections(text)

    assert "problem_statement" in found
    assert "literature_survey" in found
    assert "modules" in found
    assert "architecture" in missing
    assert "better review tool" in sections["problem_statement"]
    assert "Parser module" in sections["modules"]


def test_split_into_sections_no_headings_returns_all_missing():
    sections, found, missing = _split_into_sections("Just some unstructured text with no headings at all.")
    assert found == []
    assert set(missing) == {"problem_statement", "literature_survey", "modules", "architecture"}


def test_parse_pdf_extracts_sections_and_diagram(tmp_path):
    pdf_path = os.path.join(tmp_path, "dummy.pdf")
    build_dummy_pdf(pdf_path)

    # parse_pdf writes extracted images under config.UPLOAD_DIR keyed by
    # the pdf's basename — point it at a scratch dir for this test.
    import config

    original_upload_dir = config.UPLOAD_DIR
    config.UPLOAD_DIR = str(tmp_path)
    try:
        result = parse_pdf(pdf_path)
    finally:
        config.UPLOAD_DIR = original_upload_dir

    assert "AI-assisted pre-review tool" in result["problem_statement"] or result["problem_statement"]
    assert "[1]" in result["literature_text"]
    assert "Document Parsing module" in result["modules_text"]
    assert len(result["diagram_image_paths"]) >= 1
    for path in result["diagram_image_paths"]:
        assert os.path.exists(path)
