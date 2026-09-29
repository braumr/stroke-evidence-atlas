"""Configuration for the Stroke Recovery Research Platform pipeline."""

from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _load_project_env() -> None:
    """Load local .env values without requiring python-dotenv."""

    try:
        from dotenv import load_dotenv
    except ModuleNotFoundError:
        env_path = PROJECT_ROOT / ".env"
        if not env_path.exists():
            return
        for line in env_path.read_text().splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
        return

    load_dotenv(PROJECT_ROOT / ".env")


_load_project_env()


def _path_from_env(name: str, default: Path) -> Path:
    """Resolve a filesystem path from an environment variable or default."""

    value = os.getenv(name)
    return Path(value).expanduser() if value else default


DATA_DIR = _path_from_env("STROKE_ATLAS_DATA_DIR", PROJECT_ROOT / "data")
EXPORT_DIR = _path_from_env("STROKE_ATLAS_EXPORT_DIR", DATA_DIR / "exports")
LOG_DIR = _path_from_env("STROKE_ATLAS_LOG_DIR", DATA_DIR / "logs")
DB_PATH = _path_from_env("STROKE_ATLAS_DB_PATH", DATA_DIR / "stroke_evidence.db")
DEPLOYMENT_DB_URL = os.getenv(
    "STROKE_ATLAS_DB_URL",
    "https://github.com/braumr/stroke-evidence-atlas/releases/download/app-cohort-2026-09-29/stroke_evidence_app.db.gz",
)
DEPLOYMENT_DB_MIN_BYTES = int(os.getenv("STROKE_ATLAS_DB_MIN_BYTES", "25000000"))
AUTO_DOWNLOAD_DB = os.getenv("STROKE_ATLAS_AUTO_DOWNLOAD_DB", "1").lower() not in {"0", "false", "no"}

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

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
