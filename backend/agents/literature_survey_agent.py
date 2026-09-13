"""
Literature Survey Agent.

Extracts citation candidates from the report's literature section (regex
first, LLM fallback for irregular formats), resolves them against
Semantic Scholar, and asks a Groq model to score relevance/recency and
summarize the research gap.
"""

import json
import re
import time
from datetime import datetime
from typing import Dict, List

import requests
from groq import Groq

import config
from agents.metrics import citation_resolution_rate

BRACKET_CITATION_RE = re.compile(r"\[\d{1,3}\]\s*[^\[]{10,400}?(?=\[\d{1,3}\]|\Z)", re.DOTALL)
AUTHOR_YEAR_RE = re.compile(
    r"[A-Z][A-Za-z\-\.]+(?:\s+(?:et al\.?|and|&)\s+[A-Z][A-Za-z\-\.]+)?\s*\(\s*(?:19|20)\d{2}[a-z]?\s*\)[^.\n]{0,250}"
)
TITLE_RE = re.compile(r'["“”]([^"“”]{5,250})["“”]')
YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")


def _strip_code_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def extract_citation_candidates(text: str) -> List[Dict]:
    """Regex pass over literature text for two common citation styles.
    De-duplicates and preserves order of first appearance."""
    candidates: List[Dict] = []
    seen = set()

    for pattern in (BRACKET_CITATION_RE, AUTHOR_YEAR_RE):
        for m in pattern.finditer(text):
            raw = re.sub(r"\s+", " ", m.group(0)).strip()
            if not raw or raw in seen:
                continue
            seen.add(raw)
            title_m = TITLE_RE.search(raw)
            year_m = YEAR_RE.search(raw)
            candidates.append(
                {
                    "raw_text": raw,
                    "title": title_m.group(1).strip() if title_m else raw[:120],
                    "year": int(year_m.group(0)) if year_m else None,
                }
            )

    return candidates


def llm_extract_citations(text: str) -> List[Dict]:
    """Fallback for irregular reference formatting the regex pass misses."""
    if not config.GROQ_API_KEY:
        return []

    client = Groq(api_key=config.GROQ_API_KEY)
    prompt = (
        "Extract every distinct citation or reference entry from the literature "
        "survey text below. Return ONLY a JSON array of objects shaped exactly "
        'like {"title": "<paper title>", "year": <integer year or null>}. '
        "No prose, no markdown code fences, no commentary — JSON only.\n\n"
        f"TEXT:\n{text[:8000]}"
    )
    try:
        resp = client.chat.completions.create(
            model=config.GROQ_TEXT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=config.MAX_TOKENS,
            temperature=0.1,
        )
        content = _strip_code_fences(resp.choices[0].message.content or "")
        data = json.loads(content)
        if not isinstance(data, list):
            return []
        out = []
        for item in data:
            if isinstance(item, dict) and item.get("title"):
                out.append(
                    {
                        "raw_text": str(item.get("title")),
                        "title": str(item.get("title")),
                        "year": item.get("year"),
                    }
                )
        return out
    except Exception:
        return []


SEMANTIC_SCHOLAR_RETRY_DELAYS = (2.0, 5.0)  # backoff on 429 — the public,
# keyless endpoint shares a very low global rate limit, so a 429 here is
# usually transient traffic, not "this paper doesn't exist" — treating it
# the same as a genuine no-match (as a single try does) silently drops
# real, resolvable citations from the literature score.


def lookup_semantic_scholar(title: str) -> Dict:
    """Look up one paper title on Semantic Scholar. Returns {} on failure."""
    delays = (0.0,) + SEMANTIC_SCHOLAR_RETRY_DELAYS
    headers = {"x-api-key": config.SEMANTIC_SCHOLAR_API_KEY} if config.SEMANTIC_SCHOLAR_API_KEY else {}
    try:
        for delay in delays:
            if delay:
                time.sleep(delay)
            resp = requests.get(
                config.SEMANTIC_SCHOLAR_API,
                params={"query": title, "fields": config.SEMANTIC_SCHOLAR_FIELDS, "limit": 1},
                headers=headers,
                timeout=10,
            )
            if resp.status_code == 429:
                continue
            resp.raise_for_status()
            results = resp.json().get("data", [])
            return results[0] if results else {}
        return {}
    except Exception:
        return {}
    finally:
        time.sleep(0.3)  # be polite to the public, keyless rate limit


def score_relevance_and_recency(
    problem_statement: str, citations: List[Dict], resolved_papers: List[Dict], literature_text: str = ""
) -> Dict:
    if not config.GROQ_API_KEY:
        return {
            "score": 0,
            "flags": ["GROQ_API_KEY is not configured — literature scoring was skipped."],
            "gap_summary": "",
        }

    client = Groq(api_key=config.GROQ_API_KEY)
    current_year = datetime.now().year

    papers_desc = []
    for p in resolved_papers:
        if not p:
            continue
        title = p.get("title", "Unknown")
        year = p.get("year", "Unknown")
        abstract = (p.get("abstract") or "")[:300]
        papers_desc.append(f"- {title} ({year}): {abstract}")

    # Semantic Scholar resolution can fail for reasons that have nothing to
    # do with the report's quality (rate limits, transient network issues,
    # an obscure venue) — always show the model what the student actually
    # wrote, as written, so an unresolved citation isn't graded identically
    # to a missing one.
    raw_citations_desc = []
    for c in citations:
        title = c.get("title") or c.get("raw_text", "")[:120]
        year = c.get("year")
        raw_citations_desc.append(f"- {title} ({year if year else 'year not given'})")

    prompt = f"""You are a strict academic reviewer evaluating the literature survey of a student capstone project. Do not be lenient — a thin, generic, or outdated literature survey should score low.

Problem statement:
{problem_statement[:1500] or "(not provided)"}

Citations as written in the report ({len(citations)} found, self-reported by the student — not yet externally verified):
{chr(10).join(raw_citations_desc) if raw_citations_desc else "(none found)"}

Of those, resolved and corroborated via Semantic Scholar ({len(papers_desc)} resolved):
{chr(10).join(papers_desc) if papers_desc else "(none resolved — this may be an API/rate-limit issue rather than the citations being fake; judge recency and relevance from the self-reported list above, but still note in a flag that verification was unavailable)"}

Current year: {current_year}. Recency window for this evaluation: the last {config.RECENCY_WINDOW_YEARS} years.

Full literature survey section as written by the student:
{literature_text[:2500] or "(not provided)"}

Evaluate:
1. Relevance of these references to the stated problem.
2. Recency of the literature base against the recency window.
3. Whether the survey text above demonstrates a genuine, articulated research gap — judge this directly from what the student wrote, not from whether citations were externally resolved.

Respond with STRICT JSON only, no markdown fences, exactly this shape:
{{"score": <int 0-100>, "flags": ["<issue 1>", "..."], "gap_summary": "<1-3 sentence summary of the research gap this project addresses, or a note that none was demonstrated>"}}"""

    try:
        resp = client.chat.completions.create(
            model=config.GROQ_TEXT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=config.MAX_TOKENS,
            temperature=0.2,
        )
        content = _strip_code_fences(resp.choices[0].message.content or "")
        data = json.loads(content)
        return {
            "score": int(data.get("score", 0)),
            "flags": [str(f) for f in data.get("flags", [])],
            "gap_summary": str(data.get("gap_summary", "")),
        }
    except Exception:
        return {
            "score": 0,
            "flags": ["Literature scoring failed: the model did not return valid JSON."],
            "gap_summary": "",
        }


def run(state: dict) -> dict:
    """LangGraph node entry point. Returns only the keys this agent adds."""
    literature_text = (state.get("literature_text") or "").strip()
    problem_statement = state.get("problem_statement") or ""

    if not config.GROQ_API_KEY:
        return {
            "citations": [],
            "literature_score": 0,
            "literature_flags": ["GROQ_API_KEY is not configured — literature survey scoring was skipped."],
            "research_gap_summary": "",
            "citation_resolution_rate": 0,
        }

    if not literature_text:
        return {
            "citations": [],
            "literature_score": 0,
            "literature_flags": ["No literature survey section was found in the report."],
            "research_gap_summary": "",
            "citation_resolution_rate": 0,
        }

    candidates = extract_citation_candidates(literature_text)
    if len(candidates) < 2:
        llm_candidates = llm_extract_citations(literature_text)
        if len(llm_candidates) > len(candidates):
            candidates = llm_candidates

    candidates = candidates[:20]  # cap lookups per report

    resolved_papers = []
    for c in candidates:
        title = c.get("title")
        if not title:
            continue
        paper = lookup_semantic_scholar(title)
        if paper:
            resolved_papers.append(paper)

    result = score_relevance_and_recency(problem_statement, candidates, resolved_papers, literature_text)

    return {
        "citations": candidates,
        "literature_score": result["score"],
        "literature_flags": result["flags"],
        "research_gap_summary": result["gap_summary"],
        "citation_resolution_rate": citation_resolution_rate(len(candidates), len(resolved_papers)),
    }
