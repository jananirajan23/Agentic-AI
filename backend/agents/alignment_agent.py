"""
Architecture-Modules Alignment Agent.

Combines two independent checks, per the requirements document's explicit
call for "embeddings and semantic similarity techniques" (Ch.4.3/Ch.5.1/
Ch.7.1/Ch.8.2) rather than LLM judgement alone:

1. Embeddings pass (deterministic, no API key needed): each diagram
   component and each module-description phrase is embedded with a local
   sentence-transformer model, and matched via cosine similarity. This is
   the "Generate semantic representations -> Calculate similarity ->
   Identify unmatched components / naming inconsistencies" pipeline from
   Ch.8.2's task decomposition, and is what actually produces the
   "Semantic Alignment" evaluation metric from Ch.11.1.
2. LLM pass (Groq): a more nuanced read that can reason about whether two
   differently-worded things are conceptually the same system, which a
   pure cosine-similarity cutoff sometimes can't.

The two scores are blended when both are available; either one alone is
still usable on its own (e.g. no GROQ_API_KEY configured -> embeddings
score only, still a real measurement rather than a flat 0).
"""

import json
import re
from typing import Dict, List

from groq import Groq

import config
from agents.embedding_util import cosine_similarity_matrix, embed, embeddings_available, load_error

MAX_MISMATCH_FLAGS_PER_SIDE = 6


def _strip_code_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def split_module_phrases(modules_text: str, max_phrases: int = 40) -> List[str]:
    """Splits the module/architecture description text into comparable
    units: one per line for bullet/line-based reports, falling back to
    sentence-splitting for paragraph-style text."""
    if not modules_text:
        return []

    phrases: List[str] = []
    for line in re.split(r"[\n\r]+", modules_text):
        line = line.strip(" -*•\t")
        if not line:
            continue
        if len(line) > 160:
            phrases.extend(s.strip() for s in re.split(r"(?<=[.!?])\s+", line) if s.strip())
        else:
            phrases.append(line)

    seen = set()
    out: List[str] = []
    for phrase in phrases:
        if len(phrase) < 3:
            continue
        key = phrase.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(phrase)
        if len(out) >= max_phrases:
            break
    return out


def embedding_alignment(diagram_components: List[str], module_phrases: List[str]) -> Dict:
    """Deterministic embeddings + cosine-similarity alignment check.

    Returns {"available": bool, "score": float|None, "flags": [...]}."""
    if not embeddings_available():
        return {
            "available": False,
            "score": None,
            "flags": [
                f"Embedding model unavailable ({load_error() or 'sentence-transformers not installed'}) "
                "— the deterministic semantic-similarity check was skipped."
            ],
        }

    if not diagram_components or not module_phrases:
        return {
            "available": True,
            "score": None,
            "flags": [],
        }

    comp_vecs = embed(diagram_components)
    mod_vecs = embed(module_phrases)
    if comp_vecs is None or mod_vecs is None:
        return {"available": False, "score": None, "flags": ["Embedding computation failed unexpectedly."]}

    sim = cosine_similarity_matrix(comp_vecs, mod_vecs)  # shape (num_components, num_modules)
    threshold = config.EMBEDDING_MATCH_THRESHOLD

    comp_best_idx = sim.argmax(axis=1)
    comp_best_sim = sim.max(axis=1)
    mod_best_sim = sim.max(axis=0)

    unmatched_components = []
    naming_flags = []
    matched_components = 0
    for i, comp in enumerate(diagram_components):
        best_sim = float(comp_best_sim[i])
        best_mod = module_phrases[int(comp_best_idx[i])]
        if best_sim >= threshold:
            matched_components += 1
            if best_sim < threshold + 0.15:
                naming_flags.append(
                    (
                        best_sim,
                        f"'{comp}' (diagram) only loosely matches module text \"{best_mod[:80]}\" "
                        f"(similarity {best_sim:.2f}) — consider consistent terminology.",
                    )
                )
        else:
            unmatched_components.append(
                (
                    best_sim,
                    f"'{comp}' appears in the architecture diagram but has no closely matching module "
                    f"description (closest: \"{best_mod[:80]}\", similarity {best_sim:.2f}).",
                )
            )

    matched_modules = int((mod_best_sim >= threshold).sum())
    unmatched_modules = [
        (float(mod_best_sim[j]), f"Module text \"{phrase[:80]}\" has no closely matching diagram component "
                                  f"(similarity {float(mod_best_sim[j]):.2f}).")
        for j, phrase in enumerate(module_phrases)
        if float(mod_best_sim[j]) < threshold
    ]

    # Surface the worst mismatches first, capped so a long module section
    # doesn't flood the report with low-value near-duplicate flags.
    unmatched_components.sort(key=lambda t: t[0])
    unmatched_modules.sort(key=lambda t: t[0])
    naming_flags.sort(key=lambda t: t[0])

    flags = (
        [f for _, f in unmatched_components[:MAX_MISMATCH_FLAGS_PER_SIDE]]
        + [f for _, f in unmatched_modules[:MAX_MISMATCH_FLAGS_PER_SIDE]]
        + [f for _, f in naming_flags[:MAX_MISMATCH_FLAGS_PER_SIDE]]
    )

    component_coverage = matched_components / len(diagram_components)
    module_coverage = matched_modules / len(module_phrases)
    score = round(100 * (component_coverage + module_coverage) / 2, 1)

    return {"available": True, "score": score, "flags": flags}


def check_alignment(diagram_components: List[str], modules_text: str) -> Dict:
    if not config.GROQ_API_KEY:
        return {
            "score": None,
            "in_diagram_not_in_text": [],
            "in_text_not_in_diagram": [],
            "flags": [],
        }

    client = Groq(api_key=config.GROQ_API_KEY)
    components_list = "\n".join(f"- {c}" for c in diagram_components) or "(none identified)"

    prompt = f"""You are checking whether a capstone project report's architecture diagram and its written module description are consistent with each other.

Components identified in the architecture diagram:
{components_list}

Module / architecture description text from the report:
{(modules_text or "(not provided)")[:4000]}

Compare them. Flag only genuine mismatches — a component that is clearly present in one but absent from the other — not minor naming or phrasing differences (e.g. "DB" vs "Database" is the same thing, not a mismatch).

Respond with STRICT JSON only, no markdown fences, exactly this shape:
{{"score": <int 0-100, how well the diagram and text align>, "in_diagram_not_in_text": ["<component>", ...], "in_text_not_in_diagram": ["<module>", ...], "flags": ["<short human-readable flag>", ...]}}"""

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
            "in_diagram_not_in_text": [str(c) for c in data.get("in_diagram_not_in_text", [])],
            "in_text_not_in_diagram": [str(c) for c in data.get("in_text_not_in_diagram", [])],
            "flags": [str(f) for f in data.get("flags", [])],
        }
    except Exception:
        return {
            "score": None,
            "in_diagram_not_in_text": [],
            "in_text_not_in_diagram": [],
            "flags": ["LLM alignment scoring failed: the model did not return valid JSON."],
        }


def run(state: dict) -> dict:
    """LangGraph node entry point. Returns only the keys this agent adds."""
    diagram_components = state.get("diagram_components") or []
    modules_text = (state.get("modules_text") or "").strip()

    if not diagram_components and not modules_text:
        return {
            "alignment_score": 0,
            "alignment_flags": ["Neither diagram components nor module text were available to compare."],
            "embedding_alignment_score": 0,
        }

    module_phrases = split_module_phrases(modules_text)

    embedding_result = embedding_alignment(diagram_components, module_phrases)
    llm_result = check_alignment(diagram_components, modules_text)

    flags: List[str] = list(llm_result["flags"]) + list(embedding_result["flags"])
    for c in llm_result["in_diagram_not_in_text"]:
        flags.append(f"'{c}' appears in the architecture diagram but is not described in the module text.")
    for m in llm_result["in_text_not_in_diagram"]:
        flags.append(f"'{m}' is described in the module text but does not appear in the architecture diagram.")

    scores = [s for s in (embedding_result["score"], llm_result["score"]) if s is not None]
    if scores:
        final_score = round(sum(scores) / len(scores), 1)
    else:
        final_score = 0
        flags.append(
            "Alignment could not be scored: the embedding model is unavailable and GROQ_API_KEY is not "
            "configured."
        )

    if not flags:
        flags.append("Diagram and module description are well aligned.")

    return {
        "alignment_score": final_score,
        "alignment_flags": flags,
        "embedding_alignment_score": embedding_result["score"] if embedding_result["score"] is not None else 0,
    }
