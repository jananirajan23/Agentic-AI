"""
Shared LangGraph state for the Reviewer-Lens review pipeline.

Every node function receives the full ReviewState and returns only a
partial dict of the keys it adds or changes (never the whole state) —
this matters for the parallel `literature` / `architecture` branches,
which would otherwise both try to write the same shared keys and raise
InvalidUpdateError when they fan back in to `aggregate`.
"""

from typing import TypedDict, List, Dict, Any


class ReviewState(TypedDict, total=False):
    # --- input ---
    pdf_path: str

    # --- document_parser outputs ---
    problem_statement: str
    literature_text: str
    modules_text: str
    diagram_image_paths: List[str]
    parse_warnings: List[str]

    # --- literature_survey_agent outputs ---
    citations: List[Dict[str, Any]]  # {raw_text, title, year}
    literature_score: float
    literature_flags: List[str]
    research_gap_summary: str
    citation_resolution_rate: float  # resolved-on-Semantic-Scholar / total citations found

    # --- architecture_structure_agent outputs ---
    diagram_components: List[str]  # vision-read + OCR-read components, deduplicated
    ocr_labels: List[str]  # raw text labels read directly off the diagram via OCR
    architecture_score: float
    architecture_flags: List[str]

    # --- alignment_agent outputs ---
    alignment_score: float
    alignment_flags: List[str]
    embedding_alignment_score: float  # deterministic score from the embeddings pass alone

    # --- report_aggregator outputs ---
    composite_score: float
    all_flags: List[str]
    suggestions: List[str]
    report_path: str
