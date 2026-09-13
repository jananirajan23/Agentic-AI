"""
Document Parsing Agent.

Opens the uploaded PDF with PyMuPDF, splits the raw text into sections by
heading-keyword matching (config.SECTION_HEADINGS), and extracts diagram
images — either embedded raster images, or, if none are embedded (e.g. a
vector-drawn diagram), full-page renders as a fallback so the Architecture
Structure Agent always has something to look at.
"""

import os
from typing import Dict, List, Tuple

import pymupdf

import config

MIN_IMAGE_BYTES = 15 * 1024  # skip icons/logos, not real diagrams


def _split_into_sections(full_text: str) -> Tuple[Dict[str, str], List[str], List[str]]:
    """
    Scans lines for heading keywords (case-insensitive substring match) and
    slices the text between consecutive heading hits. Only short lines are
    considered heading candidates, to avoid matching a keyword that appears
    mid-paragraph.

    Returns (sections, found_keys, missing_keys).
    """
    lines = full_text.split("\n")

    all_patterns = [
        (key, kw.lower())
        for key, keywords in config.SECTION_HEADINGS.items()
        for kw in keywords
    ]

    hits: List[Tuple[int, str]] = []
    seen_keys: List[str] = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or len(stripped) > 100:
            continue
        low = stripped.lower()
        for key, kw in all_patterns:
            if key in seen_keys:
                continue
            if kw in low:
                hits.append((i, key))
                seen_keys.append(key)
                break

    hits.sort(key=lambda h: h[0])

    sections = {key: "" for key in config.SECTION_HEADINGS}
    for idx, (line_no, key) in enumerate(hits):
        start = line_no + 1
        end = hits[idx + 1][0] if idx + 1 < len(hits) else len(lines)
        sections[key] = "\n".join(lines[start:end]).strip()

    missing_keys = [k for k in config.SECTION_HEADINGS if k not in seen_keys]
    return sections, seen_keys, missing_keys


def _extract_embedded_images(doc: "pymupdf.Document", out_dir: str) -> List[str]:
    paths: List[str] = []
    for page_index in range(len(doc)):
        page = doc[page_index]
        for img_index, img in enumerate(page.get_images(full=True)):
            xref = img[0]
            try:
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                if len(image_bytes) < MIN_IMAGE_BYTES:
                    continue
                ext = base_image.get("ext", "png")
                out_path = os.path.join(out_dir, f"page{page_index + 1}_img{img_index + 1}.{ext}")
                with open(out_path, "wb") as f:
                    f.write(image_bytes)
                paths.append(out_path)
            except Exception:
                continue
    return paths


def _render_pages_as_fallback(doc: "pymupdf.Document", out_dir: str) -> List[str]:
    """No embedded raster images found — the diagram is likely vector-drawn
    directly on the page. Render every page to a PNG so the Architecture
    Structure Agent has something to read."""
    paths: List[str] = []
    for page_index in range(len(doc)):
        page = doc[page_index]
        pix = page.get_pixmap(dpi=150)
        out_path = os.path.join(out_dir, f"page{page_index + 1}_render.png")
        pix.save(out_path)
        paths.append(out_path)
    return paths


def parse_pdf(pdf_path: str) -> dict:
    doc = pymupdf.open(pdf_path)
    try:
        full_text = "\n".join(page.get_text() for page in doc)

        sections, found_keys, missing_keys = _split_into_sections(full_text)

        warnings: List[str] = []
        if not found_keys:
            sections["literature_survey"] = full_text
            warnings.append(
                "No section headings were recognized in this document, so the "
                "entire report text was treated as the literature survey. "
                "Check config.SECTION_HEADINGS against this report's actual "
                "heading text and add matching keywords for this template."
            )
        elif missing_keys:
            warnings.append(
                "Could not locate the following section(s): "
                + ", ".join(missing_keys)
                + ". Scoring for these areas may be based on incomplete text."
            )

        pdf_stem = os.path.splitext(os.path.basename(pdf_path))[0]
        image_dir = os.path.join(config.UPLOAD_DIR, f"{pdf_stem}_images")
        os.makedirs(image_dir, exist_ok=True)

        diagram_paths = _extract_embedded_images(doc, image_dir)
        if not diagram_paths:
            diagram_paths = _render_pages_as_fallback(doc, image_dir)

        modules_text = (
            sections.get("modules", "") + "\n\n" + sections.get("architecture", "")
        ).strip()

        return {
            "problem_statement": sections.get("problem_statement", ""),
            "literature_text": sections.get("literature_survey", ""),
            "modules_text": modules_text,
            "diagram_image_paths": diagram_paths,
            "parse_warnings": warnings,
        }
    finally:
        doc.close()


def run(state: dict) -> dict:
    """LangGraph node entry point. Returns only the keys this agent adds."""
    return parse_pdf(state["pdf_path"])
