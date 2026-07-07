"""CSV export helpers."""

from __future__ import annotations

import pandas as pd

from .config import EXPORT_DIR, ensure_directories
from .db import get_connection, init_db
from .utils import normalize_missing_label


EXPORTS = {
    "papers": "papers.csv",
    "study_extractions": "extractions.csv",
    "intervention_summaries": "interventions.csv",
    "scores": "scores.csv",
}


def _format_export_sample_size(value: object) -> object:
    if pd.isna(value):
        return "not reported in abstract"
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def export_csvs() -> dict[str, str]:
    """Export primary tables to CSV files."""

    init_db()
    ensure_directories()
    written: dict[str, str] = {}
    with get_connection() as conn:
        for table, filename in EXPORTS.items():
            df = pd.read_sql_query(f"SELECT * FROM {table}", conn)
            for column in df.select_dtypes(include=["object"]).columns:
                df[column] = df[column].map(
                    lambda value: "not reported in abstract" if pd.isna(value) else normalize_missing_label(value)
                )
            if table == "study_extractions" and "sample_size" in df.columns:
                df["sample_size"] = df["sample_size"].map(_format_export_sample_size)
            path = EXPORT_DIR / filename
            df.to_csv(path, index=False)
            written[table] = str(path)
    return written
