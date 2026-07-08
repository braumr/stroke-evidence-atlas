"""Aggregate paper-level scores into intervention summaries."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from statistics import mean
from typing import Any

from .db import get_connection, init_db
from .normalization import recovery_group
from .utils import clean_text, utc_now


HUMAN_EXCLUDED_TYPES = {"animal_study", "mechanistic_study", "protocol", "diagnostic_biomarker", "epidemiology"}


def _json_list(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
        if isinstance(parsed, list):
            return [clean_text(str(item)) for item in parsed if clean_text(str(item))]
    except json.JSONDecodeError:
        pass
    cleaned = clean_text(value)
    return [cleaned] if cleaned else []


def _top_join(values: list[str], limit: int = 8) -> str:
    counts = Counter(value for value in values if value and value.lower() != "unknown")
    return "; ".join(item for item, _ in counts.most_common(limit))


def _evidence_tier(rows: list[dict[str, Any]]) -> str:
    study_types = [row["study_type"] for row in rows]
    effects = {row.get("effect_direction") for row in rows}
    family = rows[0].get("intervention_family") or "Unspecified / not intervention-specific"
    human_count = sum(1 for study_type in study_types if study_type not in HUMAN_EXCLUDED_TYPES)
    rct_count = study_types.count("randomized_controlled_trial")
    review_count = study_types.count("systematic_review") + study_types.count("meta_analysis")
    animal_count = study_types.count("animal_study") + study_types.count("mechanistic_study")
    avg_clinical = mean(row["clinical_evidence_strength"] for row in rows)

    if family == "Unspecified / not intervention-specific":
        return "Insufficient evidence"
    if len(rows) >= 2 and ({"positive", "negative"}.issubset(effects) or {"positive", "no_effect"}.issubset(effects)):
        return "Conflicting evidence"
    if human_count == 0 and animal_count > 0:
        return "Mechanistic/preclinical only"
    if avg_clinical >= 72 and human_count >= 3 and (review_count >= 1 or rct_count >= 2):
        return "Strong clinical evidence"
    if avg_clinical >= 50 and (review_count >= 1 or rct_count >= 1 or human_count >= 3):
        return "Moderate clinical evidence"
    if human_count > 0:
        return "Emerging evidence"
    return "Insufficient evidence"


def aggregate_interventions() -> int:
    """Rebuild intervention-level summaries from extractions and scores."""

    init_db()
    with get_connection() as conn:
        rows = [
            dict(row)
            for row in conn.execute(
                """
                SELECT
                    e.*,
                    COALESCE(e.intervention_family, e.intervention_canonical, 'Unspecified / not intervention-specific') AS group_family,
                    s.neuroplasticity_potential,
                    s.clinical_evidence_strength,
                    s.safety_score,
                    s.practicality_score,
                    s.overall_score
                FROM study_extractions e
                JOIN scores s ON e.pmid = s.pmid
                    AND e.intervention_canonical = s.intervention_canonical
                WHERE e.intervention_canonical IS NOT NULL
                """
            ).fetchall()
        ]
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            family = row.get("group_family") or "Unspecified / not intervention-specific"
            row["intervention_family"] = family
            grouped[family].append(row)

        conn.execute("DELETE FROM intervention_summaries")
        for family, group in grouped.items():
            study_types = [row["study_type"] for row in group]
            outcome_measures: list[str] = []
            protocols: list[str] = []
            limitations: list[str] = []
            safety_notes: list[str] = []
            categories = [row["intervention_category"] for row in group if row["intervention_category"]]
            summary_category = recovery_group(
                intervention_family_value=family,
                intervention_category=Counter(categories).most_common(1)[0][0] if categories else None,
            )
            for row in group:
                outcome_measures.extend(_json_list(row.get("outcome_measures")))
                limitations.extend(_json_list(row.get("limitations")))
                protocol_parts = [
                    clean_text(row.get("dosage_intensity")),
                    clean_text(row.get("frequency")),
                    clean_text(row.get("duration")),
                ]
                protocol = "; ".join(part for part in protocol_parts if part and part.lower() != "unknown")
                if protocol:
                    protocols.append(protocol)
                safety = clean_text(row.get("safety_notes")) or clean_text(row.get("adverse_events"))
                if safety and safety.lower() != "unknown":
                    safety_notes.append(safety)

            human_count = sum(1 for study_type in study_types if study_type not in HUMAN_EXCLUDED_TYPES)
            conn.execute(
                """
                INSERT INTO intervention_summaries (
                    intervention_canonical, intervention_family, intervention_category, paper_count,
                    human_study_count, rct_count, systematic_review_count,
                    meta_analysis_count, animal_study_count,
                    avg_neuroplasticity_potential, avg_clinical_evidence_strength,
                    avg_safety_score, avg_practicality_score, avg_overall_score,
                    evidence_tier, common_outcome_measures, treatment_protocols,
                    key_limitations, safety_summary, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    family,
                    family,
                    summary_category,
                    len(group),
                    human_count,
                    study_types.count("randomized_controlled_trial"),
                    study_types.count("systematic_review"),
                    study_types.count("meta_analysis"),
                    study_types.count("animal_study"),
                    round(mean(row["neuroplasticity_potential"] for row in group), 2),
                    round(mean(row["clinical_evidence_strength"] for row in group), 2),
                    round(mean(row["safety_score"] for row in group), 2),
                    round(mean(row["practicality_score"] for row in group), 2),
                    round(mean(row["overall_score"] for row in group), 2),
                    _evidence_tier(group),
                    _top_join(outcome_measures),
                    _top_join(protocols),
                    _top_join(limitations),
                    _top_join(safety_notes),
                    utc_now(),
                ),
            )
    return len(grouped)
