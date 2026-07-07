"""CSV export helpers."""

from __future__ import annotations

import pandas as pd

from .config import EXPORT_DIR, ensure_directories
from .db import get_connection, init_db


EXPORTS = {
    "papers": "papers.csv",
    "study_extractions": "extractions.csv",
    "intervention_summaries": "interventions.csv",
    "scores": "scores.csv",
}


def export_csvs() -> dict[str, str]:
    """Export primary tables to CSV files."""

    init_db()
    ensure_directories()
    written: dict[str, str] = {}
    with get_connection() as conn:
        for table, filename in EXPORTS.items():
            df = pd.read_sql_query(f"SELECT * FROM {table}", conn)
            path = EXPORT_DIR / filename
            df.to_csv(path, index=False)
            written[table] = str(path)
    return written
