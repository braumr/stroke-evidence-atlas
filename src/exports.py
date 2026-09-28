"""CSV export helpers."""

from __future__ import annotations

import csv

from .config import EXPORT_DIR, ensure_directories
from .db import get_connection, init_db
from .utils import normalize_missing_label


EXPORTS = {
    "papers": "papers.csv",
    "study_extractions": "extractions.csv",
    "intervention_summaries": "interventions.csv",
    "scores": "scores.csv",
    "recovery_domains": "recovery_domains.csv",
    "research_topics": "research_topics.csv",
    "taxonomy_aliases": "taxonomy_aliases.csv",
    "taxonomy_review_queue": "taxonomy_review_queue.csv",
}


def _format_export_sample_size(value: object) -> object:
    if value is None:
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
            path = EXPORT_DIR / filename
            cursor = conn.execute(f"SELECT * FROM {table}")
            column_names = [description[0] for description in cursor.description]
            with path.open("w", newline="", encoding="utf-8") as file_obj:
                writer = csv.DictWriter(file_obj, fieldnames=column_names)
                writer.writeheader()
                for row in cursor:
                    formatted = {}
                    for column in column_names:
                        value = row[column]
                        if table == "study_extractions" and column == "sample_size":
                            formatted[column] = _format_export_sample_size(value)
                        elif isinstance(value, str) or value is None:
                            formatted[column] = normalize_missing_label(value)
                        else:
                            formatted[column] = value
                    writer.writerow(formatted)
            written[table] = str(path)
    return written
