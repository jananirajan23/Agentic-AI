"""
Shared OCR helper for the Architecture Structure Agent.

The requirements document names OCR specifically ("extracting components
and labels through OCR and document processing techniques", Ch.6/Ch.7.1/
Ch.8.2) as the extraction technique for architecture diagrams, run ahead
of / alongside the Groq vision model's structural reading. RapidOCR is
used instead of Tesseract because it's pure-Python + onnxruntime (no
separate system binary to install on Windows), which keeps `pip install
-r requirements.txt` sufficient to run the whole backend.
"""

from functools import lru_cache
from typing import List

_ENGINE = None
_LOAD_ERROR: str | None = None


def _get_engine():
    global _ENGINE, _LOAD_ERROR
    if _ENGINE is not None or _LOAD_ERROR is not None:
        return _ENGINE
    try:
        from rapidocr_onnxruntime import RapidOCR

        _ENGINE = RapidOCR()
    except Exception as e:  # pragma: no cover - exercised via mocking in tests
        _LOAD_ERROR = str(e)
        _ENGINE = None
    return _ENGINE


def ocr_available() -> bool:
    return _get_engine() is not None


def extract_text_labels(image_path: str, min_confidence: float = 0.5) -> List[str]:
    """Runs OCR over one diagram image and returns the detected text
    labels above `min_confidence`, longest-first-deduplicated. Returns []
    on any failure (missing engine, unreadable image, etc.) rather than
    raising — OCR is a supporting signal, not a hard dependency."""
    engine = _get_engine()
    if engine is None:
        return []

    try:
        result, _elapsed = engine(image_path)
    except Exception:
        return []

    if not result:
        return []

    labels: List[str] = []
    seen = set()
    for entry in result:
        # RapidOCR result rows: [box, text, confidence]
        try:
            text, confidence = entry[1], float(entry[2])
        except (IndexError, TypeError, ValueError):
            continue
        text = str(text).strip()
        if not text or confidence < min_confidence:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        labels.append(text)

    return labels


@lru_cache(maxsize=1)
def load_error() -> str | None:
    _get_engine()
    return _LOAD_ERROR
