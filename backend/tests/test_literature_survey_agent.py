"""
Unit tests for agents/literature_survey_agent.py.

Citation-extraction regexes are tested as pure functions; the Semantic
Scholar HTTP call and the Groq scoring call are mocked out — this suite
should never hit the network or spend API credits (Ch.11.2: "Unit
Testing... citation parsing" tested independently of retrieval/scoring).
"""

import agents.literature_survey_agent as lit


def test_extract_bracket_citations():
    text = (
        '[1] A. Kumar, "Automated Essay Scoring Using Transformer Models," IEEE Access, 2022.\n'
        '[2] R. Chen and T. Osei, "A Survey of LLM-Based Document Review Systems," ACM CSUR, 2023.'
    )
    candidates = lit.extract_citation_candidates(text)
    assert len(candidates) == 2
    assert candidates[0]["year"] == 2022
    assert "Automated Essay Scoring" in candidates[0]["title"]
    assert candidates[1]["year"] == 2023


def test_extract_author_year_citations():
    text = "Prior work by Smith and Doe (2020) explored a similar system for grading."
    candidates = lit.extract_citation_candidates(text)
    assert len(candidates) == 1
    assert candidates[0]["year"] == 2020


def test_extract_citation_candidates_deduplicates():
    text = "[1] Same Paper, 2021.\n[1] Same Paper, 2021."
    candidates = lit.extract_citation_candidates(text)
    assert len(candidates) == 1


def test_lookup_semantic_scholar_success(mocker):
    mock_response = mocker.Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": [{"title": "Attention Is All You Need", "year": 2017, "abstract": "...", "venue": "NeurIPS"}]
    }
    mock_response.raise_for_status.return_value = None
    mocker.patch("agents.literature_survey_agent.requests.get", return_value=mock_response)
    mocker.patch("agents.literature_survey_agent.time.sleep")  # skip the politeness delay

    result = lit.lookup_semantic_scholar("Attention Is All You Need")
    assert result["title"] == "Attention Is All You Need"


def test_lookup_semantic_scholar_no_results(mocker):
    mock_response = mocker.Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": []}
    mock_response.raise_for_status.return_value = None
    mocker.patch("agents.literature_survey_agent.requests.get", return_value=mock_response)
    mocker.patch("agents.literature_survey_agent.time.sleep")

    assert lit.lookup_semantic_scholar("Some Nonexistent Paper") == {}


def test_lookup_semantic_scholar_retries_on_429_then_succeeds(mocker):
    rate_limited = mocker.Mock(status_code=429)
    ok = mocker.Mock(status_code=200)
    ok.json.return_value = {"data": [{"title": "Found After Retry", "year": 2020}]}
    ok.raise_for_status.return_value = None

    mocker.patch("agents.literature_survey_agent.requests.get", side_effect=[rate_limited, ok])
    mocker.patch("agents.literature_survey_agent.time.sleep")

    result = lit.lookup_semantic_scholar("Some Paper")
    assert result["title"] == "Found After Retry"


def test_run_without_groq_key_skips_gracefully(monkeypatch):
    monkeypatch.setattr(lit.config, "GROQ_API_KEY", "")
    result = lit.run({"literature_text": "[1] Something, 2020.", "problem_statement": "x"})
    assert result["literature_score"] == 0
    assert result["citation_resolution_rate"] == 0
    assert "GROQ_API_KEY" in result["literature_flags"][0]


def test_run_without_literature_text(monkeypatch):
    monkeypatch.setattr(lit.config, "GROQ_API_KEY", "fake-key-for-this-test")
    result = lit.run({"literature_text": "", "problem_statement": "x"})
    assert result["literature_score"] == 0
    assert result["citations"] == []


def test_run_computes_citation_resolution_rate(monkeypatch, mocker):
    monkeypatch.setattr(lit.config, "GROQ_API_KEY", "fake-key-for-this-test")
    mocker.patch(
        "agents.literature_survey_agent.lookup_semantic_scholar",
        side_effect=[{"title": "Paper One", "year": 2021}, {}],
    )
    mocker.patch(
        "agents.literature_survey_agent.score_relevance_and_recency",
        return_value={"score": 70, "flags": [], "gap_summary": "A real gap."},
    )

    state = {
        "literature_text": '[1] Paper One, 2021.\n[2] Paper Two, 2022.',
        "problem_statement": "Some problem.",
    }
    result = lit.run(state)

    assert result["citation_resolution_rate"] == 0.5
    assert result["literature_score"] == 70
