"""Configuration for the Stroke Evidence Atlas pipeline."""

from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
EXPORT_DIR = DATA_DIR / "exports"
LOG_DIR = DATA_DIR / "logs"
DB_PATH = DATA_DIR / "stroke_evidence.db"

MAX_PAPERS = 2000
DEFAULT_LLM_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

NCBI_EMAIL = os.getenv("NCBI_EMAIL", "")
NCBI_TOOL = "stroke-evidence-atlas"
NCBI_API_KEY = os.getenv("NCBI_API_KEY")

REQUESTS_PER_SECOND_WITHOUT_KEY = 3
REQUESTS_PER_SECOND_WITH_KEY = 10
PUBMED_FETCH_BATCH_SIZE = 100

EXTRACTION_STATUSES = {
    "pending",
    "extracted",
    "failed",
    "skipped_no_abstract",
}

SCORING_WEIGHTS = {
    "neuroplasticity_potential": 0.40,
    "clinical_evidence_strength": 0.35,
    "safety_score": 0.15,
    "practicality_score": 0.10,
}


def ensure_directories() -> None:
    """Create local data directories used by the project."""

    DATA_DIR.mkdir(exist_ok=True)
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
