"""Recovery taxonomy classification for extracted studies."""

from __future__ import annotations

from typing import Any

from .aggregator import aggregate_interventions
from .db import get_connection, init_db
from .normalization import (
    REVIEW_TOPIC,
    intervention_family,
    is_approved_research_topic,
    recovery_group,
    taxonomy_key,
)
from .utils import clean_text, setup_logging, utc_now

LOGGER = setup_logging(__name__)


def classify_extractions(aggregate: bool = True) -> int:
    """Classify extracted studies into Research Topics and Recovery Domains."""

    init_db()
    with get_connection() as conn:
        rows = [
            dict(row)
            for row in conn.execute(
                """
                SELECT e.*, p.title, p.abstract
                FROM study_extractions e
                LEFT JOIN papers p ON e.pmid = p.pmid
                """
            ).fetchall()
        ]
        conn.execute("DELETE FROM taxonomy_review_queue WHERE status = 'needs_review'")
        for row in rows:
            evidence_text = " ".join(
                clean_text(row.get(field))
                for field in ["title", "abstract", "results_summary", "mechanistic_rationale"]
            )
            topic = intervention_family(
                row.get("intervention_raw"),
                row.get("intervention_canonical"),
                row.get("intervention_category"),
                evidence_text,
            )
            domain = recovery_group(
                row.get("intervention_raw"),
                row.get("intervention_canonical"),
                topic,
                row.get("intervention_category"),
                evidence_text,
            )
            _queue_taxonomy_review(conn, row, topic, domain)
            conn.execute(
                "UPDATE study_extractions SET intervention_family = ?, intervention_category = ? WHERE id = ?",
                (topic, domain, row["id"]),
            )

    if aggregate:
        aggregate_interventions()
    LOGGER.info("Classified %s extracted studies", len(rows))
    return len(rows)


def _queue_taxonomy_review(
    conn,
    row: dict[str, Any],
    suggested_topic: str,
    suggested_domain: str,
) -> None:
    """Record unmapped extracted labels for taxonomy review without blocking classification."""

    raw_label = clean_text(row.get("intervention_raw"))
    canonical_label = clean_text(row.get("intervention_canonical"))
    review_label = canonical_label or raw_label
    if not review_label:
        return
    if suggested_topic != REVIEW_TOPIC and is_approved_research_topic(suggested_topic):
        return

    label_key = taxonomy_key(review_label)
    if not label_key:
        return

    now = utc_now()
    conn.execute(
        """
        INSERT INTO taxonomy_review_queue (
            label_key, raw_label, canonical_label, suggested_topic, suggested_domain,
            occurrence_count, status, first_seen_at, last_seen_at
        )
        VALUES (?, ?, ?, ?, ?, 1, 'needs_review', ?, ?)
        ON CONFLICT(label_key) DO UPDATE SET
            raw_label = COALESCE(excluded.raw_label, taxonomy_review_queue.raw_label),
            canonical_label = COALESCE(excluded.canonical_label, taxonomy_review_queue.canonical_label),
            suggested_topic = excluded.suggested_topic,
            suggested_domain = excluded.suggested_domain,
            occurrence_count = taxonomy_review_queue.occurrence_count + 1,
            last_seen_at = excluded.last_seen_at
        """,
        (
            label_key,
            raw_label,
            canonical_label,
            suggested_topic,
            suggested_domain,
            now,
            now,
        ),
    )
