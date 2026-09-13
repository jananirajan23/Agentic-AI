"""
Reviewer-Lens backend configuration.

Central, side-effect-light config: environment reads, default constants,
and per-department tunables. No business logic lives here.
"""

import os

from dotenv import load_dotenv

# Loads variables from a `.env` file in backend/ (if present) into the
# process environment. Real environment variables always take precedence
# over the .env file, and it's a no-op if no .env file exists — so this is
# safe whether you're using a .env file, real env vars, or both.
load_dotenv()

# --- Groq API ---------------------------------------------------------
# Read at import time. Agents check for a falsy value and degrade
# gracefully (score 0 + explanatory flag) rather than crashing, so it's
# fine for this to be empty in dev/demo environments without a key.
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

# Model IDs are intentionally NOT hardcoded from memory — Groq deprecates
# and replaces models frequently (e.g. llama-3.3-70b-versatile was
# deprecated in favor of openai/gpt-oss-120b). Before shipping, confirm
# current production model IDs via `GET https://api.groq.com/openai/v1/models`
# or https://console.groq.com/docs/models, and update the env vars/defaults
# below as needed.
GROQ_TEXT_MODEL = os.environ.get("GROQ_TEXT_MODEL", "openai/gpt-oss-120b")
# qwen/qwen3.6-27b (the previous default) is a heavy "thinking" reasoning
# model: it frequently burns its entire output-token budget on an internal
# <think> pass and returns empty content before ever writing the JSON
# answer — confirmed via direct API testing (finish_reason "length",
# reasoning_tokens == max_tokens). qwen/qwen3.8-27b answers the same vision
# prompt directly, with no hidden reasoning pass, in ~200-300 tokens.
GROQ_VISION_MODEL = os.environ.get("GROQ_VISION_MODEL", "qwen/qwen3.8-27b")

MAX_TOKENS = 2000

# --- Semantic Scholar ---------------------------------------------------
SEMANTIC_SCHOLAR_API = "https://api.semanticscholar.org/graph/v1/paper/search"
SEMANTIC_SCHOLAR_FIELDS = "title,year,abstract,venue,citationCount"
# Optional: the public, keyless endpoint shares a very low global rate
# limit (confirmed hitting 429 in normal testing here). A free key raises
# that limit substantially — request one at
# https://www.semanticscholar.org/product/api#api-key-form and set it here.
SEMANTIC_SCHOLAR_API_KEY = os.environ.get("SEMANTIC_SCHOLAR_API_KEY", "")

RECENCY_WINDOW_YEARS = 5

# --- Section splitting ---------------------------------------------------
# Keyword lists used to slice raw PDF text into sections by heading match
# (case-insensitive substring match on a line). Adjust per department
# report template — see README "Extension points".
SECTION_HEADINGS = {
    "problem_statement": [
        "problem statement",
        "problem definition",
        "objective of the project",
        "objectives",
        "aim of the project",
        "motivation",
    ],
    "literature_survey": [
        "literature survey",
        "literature review",
        "related work",
        "existing system",
        "survey of existing",
    ],
    "modules": [
        "system modules",
        "modules",
        "module description",
        "functional requirements",
        "implementation",
    ],
    "architecture": [
        "system architecture",
        "architecture diagram",
        "system design",
        "proposed architecture",
        "block diagram",
        "design",
    ],
}

# --- Scoring ---------------------------------------------------------
SCORE_WEIGHTS = {
    "literature_score": 0.30,
    "architecture_score": 0.35,
    "alignment_score": 0.35,
}
assert abs(sum(SCORE_WEIGHTS.values()) - 1.0) < 1e-6, "SCORE_WEIGHTS must sum to 1.0"

# --- Storage ---------------------------------------------------------
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(_BASE_DIR, "data", "uploads")
REPORTS_DIR = os.path.join(_BASE_DIR, "data", "reports")
DB_PATH = os.environ.get("REVIEWERLENS_DB_PATH", os.path.join(_BASE_DIR, "data", "reviewerlens.db"))

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

# --- Auth --------------------------------------------------------------
# HS256 JWT for the faculty login/dashboard. The default is fine for local
# dev/demo only — set a real random JWT_SECRET env var before deploying
# anywhere reachable by more than one trusted person.
JWT_SECRET = os.environ.get("JWT_SECRET", "dev-insecure-secret-change-me-before-deploying-anywhere-real")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.environ.get("JWT_EXPIRE_MINUTES", "480"))

# --- Embeddings (Architecture-Modules Alignment Agent) ------------------
# Small, CPU-friendly sentence-embedding model — downloaded once from
# Hugging Face on first use and cached locally (~90MB).
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
# Minimum cosine similarity for a diagram component <-> module phrase to be
# considered "the same thing" rather than a naming inconsistency / gap.
EMBEDDING_MATCH_THRESHOLD = float(os.environ.get("EMBEDDING_MATCH_THRESHOLD", "0.45"))
