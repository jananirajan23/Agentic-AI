"""
Architecture Structure Agent.

Extracts diagram components two ways and merges them:

1. OCR (agents/ocr_util.py, RapidOCR) reads the literal text labels drawn
   on the diagram — exact strings, no interpretation, no API key needed.
2. A Groq vision model reads the diagram for structure: components, data
   flow, and anything the diagram seems to be missing relative to the
   stated problem, using the OCR labels as grounding context.

Scoring is a simple, explainable heuristic over the vision readings — not
another LLM call — so the score is easy to justify to a faculty reviewer.
When no Groq key is configured, OCR labels alone still populate
`diagram_components` so the (embeddings-based) Alignment Agent downstream
still has something to compare against the module text.
"""

import base64
import json
import mimetypes
import re
from typing import Dict, List

from groq import Groq

import config
from agents.ocr_util import extract_text_labels, ocr_available

MISSING_COMPONENT_PENALTY = 10
ZERO_COMPONENT_PENALTY = 40

# qwen/qwen3.6-27b is a reasoning model: without reasoning_format="hidden" it
# prefixes its JSON answer with a <think>...</think> trace, which breaks
# json.loads outright. Worse, that reasoning pass is unbounded — it
# sometimes burns the *entire* token budget thinking and returns empty
# content (finish_reason "length") before ever writing the answer, even
# with reasoning_format="hidden" and a "/no_think" directive in the
# prompt (Qwen3's documented way to skip its thinking pass, which Groq
# honors most but not all of the time). A single retry on a genuinely
# empty/unparseable response is usually enough to get a real reading.
# 950 stays just under the 1000 output-tokens-per-minute cap this model
# has on the on-demand Groq tier (config.MAX_TOKENS's default 2000 gets
# the whole request rejected outright).
VISION_MAX_TOKENS = 950
VISION_MAX_ATTEMPTS = 3


def _strip_code_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def read_diagram(image_path: str, problem_statement: str, ocr_labels: List[str] | None = None) -> Dict:
    """One Groq vision call per diagram image. Returns a reading dict;
    falls back to an empty-but-explainable reading on any failure."""
    empty_reading = {
        "components": [],
        "data_flow": [],
        "missing_vs_problem": [],
        "notes": "",
        "image_path": image_path,
    }

    if not config.GROQ_API_KEY:
        empty_reading["notes"] = "GROQ_API_KEY is not configured — diagram was not read."
        return empty_reading

    mime_type, _ = mimetypes.guess_type(image_path)
    mime_type = mime_type or "image/png"

    try:
        with open(image_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
    except Exception as e:
        empty_reading["notes"] = f"Could not read image file: {e}"
        return empty_reading

    ocr_labels = ocr_labels or []
    ocr_context = (
        "Text labels an OCR pass detected directly on this image (may include noise or partial "
        "words — use them to ground exact component names, but rely on your own visual reading "
        "for structure):\n" + "\n".join(f"- {label}" for label in ocr_labels)
        if ocr_labels
        else "OCR did not detect any text labels on this image."
    )

    prompt_text = f"""This image is a system architecture / block / module diagram from a student capstone project report.

Project problem statement:
{problem_statement[:1200] or "(not provided)"}

{ocr_context}

Analyze the diagram and respond with STRICT JSON only, no markdown fences, exactly this shape:
{{"components": ["<component or module name>", ...], "data_flow": ["<short description of a data/control flow arrow or connection>", ...], "missing_vs_problem": ["<an element the problem statement implies but the diagram does not show>", ...], "notes": "<1-2 sentence overall observation>"}}

If the image is not a diagram at all, or is unreadable, return empty arrays and say so in "notes". /no_think"""

    client = Groq(api_key=config.GROQ_API_KEY)
    last_error: Exception | None = None
    for _attempt in range(VISION_MAX_ATTEMPTS):
        try:
            resp = client.chat.completions.create(
                model=config.GROQ_VISION_MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt_text},
                            {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{b64}"}},
                        ],
                    }
                ],
                max_tokens=VISION_MAX_TOKENS,
                temperature=0.2,
                reasoning_format="hidden",
            )
            content = _strip_code_fences(resp.choices[0].message.content or "")
            data = json.loads(content)
            return {
                "components": [str(c) for c in data.get("components", [])],
                "data_flow": [str(c) for c in data.get("data_flow", [])],
                "missing_vs_problem": [str(c) for c in data.get("missing_vs_problem", [])],
                "notes": str(data.get("notes", "")),
                "image_path": image_path,
            }
        except Exception as e:
            last_error = e
            continue

    empty_reading["notes"] = f"Diagram reading failed (model did not return valid JSON): {last_error}"
    return empty_reading


def score_architecture(readings: List[Dict]) -> Dict:
    """Explainable heuristic scoring over the vision readings."""
    if not readings:
        return {"score": 0, "flags": ["No diagram images were available to evaluate."]}

    score = 100
    flags: List[str] = []

    for reading in readings:
        label = reading.get("image_path", "diagram")
        short_label = label.split("\\")[-1].split("/")[-1]

        if not reading["components"]:
            score -= ZERO_COMPONENT_PENALTY
            flags.append(f"{short_label}: no readable components were identified in this diagram.")
            if reading.get("notes"):
                flags.append(f"{short_label}: {reading['notes']}")
            continue

        missing = reading.get("missing_vs_problem") or []
        if missing:
            score -= MISSING_COMPONENT_PENALTY * len(missing)
            for m in missing:
                flags.append(f"{short_label}: diagram appears to be missing '{m}' relative to the problem statement.")

    score = max(0, min(100, score))
    if not flags:
        flags.append("Diagram(s) appear structurally consistent with the stated problem.")

    return {"score": score, "flags": flags}


def _filter_ocr_labels(labels: List[str]) -> List[str]:
    """Drops OCR noise that isn't a plausible component/module label:
    single characters, pure punctuation/arrows, bare numbers."""
    out = []
    for label in labels:
        cleaned = label.strip()
        if len(cleaned) < 2 or not any(ch.isalpha() for ch in cleaned):
            continue
        out.append(cleaned)
    return out


def _normalize_for_dedup(text: str) -> str:
    return re.sub(r"\s+", "", text.lower())


def _merge_components(vision_components: List[str], ocr_labels: List[str]) -> List[str]:
    """Vision-read components first (already de-noised by the model),
    then any OCR label that isn't a near-duplicate of one already
    present — case-insensitive equality/substring (e.g. OCR's "DB" vs
    vision's "Database"), and whitespace-insensitive too (OCR sometimes
    drops the space in "ScoringEngine" vs. vision's "Scoring Engine")."""
    merged = list(vision_components)
    for label in _filter_ocr_labels(ocr_labels):
        low, norm = label.lower(), _normalize_for_dedup(label)
        is_duplicate = any(
            low == c.lower() or low in c.lower() or c.lower() in low or norm == _normalize_for_dedup(c)
            for c in merged
        )
        if not is_duplicate:
            merged.append(label)
    return merged


def run(state: dict) -> dict:
    """LangGraph node entry point. Returns only the keys this agent adds."""
    image_paths = state.get("diagram_image_paths") or []
    problem_statement = state.get("problem_statement") or ""

    if not image_paths:
        return {
            "diagram_components": [],
            "ocr_labels": [],
            "architecture_score": 0,
            "architecture_flags": ["No diagram images were found in the report to evaluate."],
        }

    ocr_by_image: Dict[str, List[str]] = {path: extract_text_labels(path) for path in image_paths}
    all_ocr_labels: List[str] = []
    for labels in ocr_by_image.values():
        for label in labels:
            if label not in all_ocr_labels:
                all_ocr_labels.append(label)

    ocr_flags: List[str] = []
    if not ocr_available():
        ocr_flags.append(
            "OCR engine could not be loaded (see agents/ocr_util.py) — diagram labels came from the "
            "vision model only, without an OCR cross-check."
        )
    elif not all_ocr_labels:
        ocr_flags.append(
            "OCR did not detect any text labels on the diagram(s) — they may be image-only shapes "
            "with no embedded text, or too low-resolution to read."
        )
    else:
        ocr_flags.append(f"OCR detected {len(all_ocr_labels)} text label(s) on the diagram(s).")

    if not config.GROQ_API_KEY:
        # Vision reading (and therefore the "missing vs. problem" scoring
        # heuristic) needs Groq, but OCR does not — surface OCR-derived
        # components anyway so the downstream, embeddings-based Alignment
        # Agent still has something to compare against the module text.
        return {
            "diagram_components": _filter_ocr_labels(all_ocr_labels),
            "ocr_labels": all_ocr_labels,
            "architecture_score": 0,
            "architecture_flags": [
                "GROQ_API_KEY is not configured — vision-based architecture scoring was skipped."
            ]
            + ocr_flags,
        }

    readings = [read_diagram(path, problem_statement, ocr_by_image.get(path)) for path in image_paths]

    result = score_architecture(readings)

    vision_components: List[str] = []
    for reading in readings:
        for c in reading["components"]:
            if c not in vision_components:
                vision_components.append(c)

    merged_components = _merge_components(vision_components, all_ocr_labels)

    return {
        "diagram_components": merged_components,
        "ocr_labels": all_ocr_labels,
        "architecture_score": result["score"],
        "architecture_flags": result["flags"] + ocr_flags,
    }
