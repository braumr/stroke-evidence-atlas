"""Transparent, configurable intervention scoring."""

from __future__ import annotations

import json
from typing import Any

from .aggregator import aggregate_interventions
from .classification import classify_extractions
from .config import SCORING_WEIGHTS
from .db import get_connection, init_db
from .utils import clean_text, setup_logging, utc_now

LOGGER = setup_logging(__name__)


STUDY_TYPE_SCORES = {
    "meta_analysis": 82,
    "systematic_review": 74,
    "randomized_controlled_trial": 78,
    "cohort_study": 60,
    "case_control_study": 52,
    "mixed_methods": 48,
    "pilot_study": 42,
    "feasibility_study": 38,
    "case_series": 28,
    "case_report": 20,
    "narrative_review": 30,
    "animal_study": 15,
    "mechanistic_study": 15,
    "protocol": 8,
    "diagnostic_biomarker": 10,
    "epidemiology": 15,
    "qualitative": 25,
    "unknown": 20,
}

CATEGORY_PRACTICALITY = {
    "Family and Home Support": 82,
    "Lifestyle and Daily Health": 76,
    "Physical Rehabilitation": 70,
    "Cognition and Communication": 62,
    "Rehabilitation Technology": 42,
    "Brain and Nerve Stimulation": 40,
    "Medical and Biological Recovery": 42,
    "Testing and Prediction": 30,
    "Recovery Science": 25,
    "General Rehabilitation": 58,
    "Other": 40,
}


def _clamp(value: float) -> float:
    return max(0.0, min(100.0, round(value, 2)))


def _json_list(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
    except json.JSONDecodeError:
        return [value]
    return []


def _quality_tier(study_type: str) -> str:
    if study_type in {"meta_analysis", "systematic_review"}:
        return "review_synthesis"
    if study_type == "randomized_controlled_trial":
        return "controlled_clinical"
    if study_type in {"cohort_study", "case_control_study"}:
        return "observational_human"
    if study_type in {"animal_study", "mechanistic_study"}:
        return "preclinical_or_mechanistic"
    if study_type == "protocol":
        return "protocol_only"
    return "lower_or_uncertain"


def score_neuroplasticity(row: dict[str, Any]) -> tuple[float, list[str]]:
    """Score plausible neuroplasticity engagement from extracted fields."""

    score = 35.0
    notes = ["base score reflects uncertain mechanism unless abstract states more"]
    mechanisms = set(_json_list(row.get("neuroplasticity_mechanisms")))
    score += min(len([m for m in mechanisms if m != "unknown"]) * 7, 35)
    if mechanisms:
        notes.append(f"mechanisms: {', '.join(sorted(mechanisms))}")

    combined = " ".join(
        clean_text(row.get(field)).lower()
        for field in ["intervention_raw", "dosage_intensity", "frequency", "duration", "mechanistic_rationale"]
    )
    keyword_bumps = {
        "repet": 8,
        "task": 6,
        "intensive": 6,
        "high-intensity": 6,
        "feedback": 5,
        "motor learning": 7,
        "aerobic": 5,
        "imagery": 5,
        "stimulation": 5,
    }
    for keyword, bump in keyword_bumps.items():
        if keyword in combined:
            score += bump
            notes.append(f"abstract suggests {keyword}")

    effect = row.get("effect_direction")
    if effect == "positive":
        score += 5
    elif effect in {"negative", "no_effect"}:
        score -= 5

    return _clamp(score), notes


def score_clinical_evidence(row: dict[str, Any]) -> tuple[float, list[str]]:
    """Score human clinical evidence strength by study design and size."""

    study_type = row.get("study_type") or "unknown"
    score = float(STUDY_TYPE_SCORES.get(study_type, 20))
    notes = [f"study type score: {study_type}"]

    sample_size = row.get("sample_size")
    if isinstance(sample_size, int):
        if sample_size >= 200:
            score += 8
            notes.append("larger sample size")
        elif sample_size >= 50:
            score += 4
            notes.append("moderate sample size")
        elif sample_size < 15:
            score -= 5
            notes.append("small sample size")

    if row.get("stroke_type") == "not_stroke":
        score -= 15
        notes.append("not stroke-specific")
    if row.get("intervention_family") == "Unspecified / not intervention-specific":
        score -= 12
        notes.append("not tied to a specific research topic")
    if study_type in {"animal_study", "mechanistic_study", "protocol", "diagnostic_biomarker", "epidemiology"}:
        notes.append("not treated as direct clinical rehabilitation proof")

    return _clamp(score), notes


def score_safety(row: dict[str, Any]) -> tuple[float, list[str]]:
    """Score safety/tolerability with cautious uncertainty handling."""

    category = row.get("intervention_category") or "unknown"
    score = 62.0
    notes = ["middle score used when safety reporting is limited"]
    text = " ".join(clean_text(row.get(field)).lower() for field in ["adverse_events", "safety_notes", "limitations"])

    if any(term in text for term in ["no adverse", "safe", "well tolerated", "well-tolerated"]):
        score += 18
        notes.append("abstract reports favorable safety/tolerability")
    if any(term in text for term in ["serious adverse", "adverse event", "dropout", "pain", "seizure"]):
        score -= 18
        notes.append("abstract mentions adverse events or tolerability concerns")
    if category in {"Brain and Nerve Stimulation", "Medical and Biological Recovery"}:
        score -= 5
        notes.append("requires contraindication/screening awareness")
    if category in {"Lifestyle and Daily Health", "Family and Home Support", "Physical Rehabilitation"}:
        score += 5
        notes.append("generally practical safety profile, still patient-specific")

    return _clamp(score), notes


def score_practicality(row: dict[str, Any]) -> tuple[float, list[str]]:
    """Score real-world feasibility."""

    category = row.get("intervention_category") or "unknown"
    score = float(CATEGORY_PRACTICALITY.get(category, 40))
    notes = [f"category practicality baseline: {category}"]
    setting = clean_text(row.get("setting")).lower()
    intervention = clean_text(row.get("intervention_raw")).lower()

    if setting in {"home", "community", "outpatient"}:
        score += 10
        notes.append(f"setting suggests {setting} feasibility")
    if any(term in intervention for term in ["robot", "exoskeleton", "virtual reality", "transcranial"]):
        score -= 8
        notes.append("equipment or specialist supervision likely needed")
    if "caregiver" in intervention or category == "Family and Home Support":
        score += 8
        notes.append("home/caregiver delivery may improve reach")

    return _clamp(score), notes


def score_row(row: dict[str, Any]) -> dict[str, Any]:
    """Score one extraction row."""

    neuro, neuro_notes = score_neuroplasticity(row)
    clinical, clinical_notes = score_clinical_evidence(row)
    safety, safety_notes = score_safety(row)
    practicality, practical_notes = score_practicality(row)
    overall = _clamp(
        neuro * SCORING_WEIGHTS["neuroplasticity_potential"]
        + clinical * SCORING_WEIGHTS["clinical_evidence_strength"]
        + safety * SCORING_WEIGHTS["safety_score"]
        + practicality * SCORING_WEIGHTS["practicality_score"]
    )
    notes = {
        "neuroplasticity_potential": neuro_notes,
        "clinical_evidence_strength": clinical_notes,
        "safety_score": safety_notes,
        "practicality_score": practical_notes,
        "weights": SCORING_WEIGHTS,
        "caution": "Scores are synthesis aids, not proof or medical advice.",
    }
    return {
        "pmid": row["pmid"],
        "intervention_canonical": row["intervention_canonical"],
        "intervention_family": row["intervention_family"],
        "intervention_category": row["intervention_category"],
        "neuroplasticity_potential": neuro,
        "clinical_evidence_strength": clinical,
        "safety_score": safety,
        "practicality_score": practicality,
        "overall_score": overall,
        "study_quality_tier": _quality_tier(row.get("study_type") or "unknown"),
        "scoring_notes": json.dumps(notes, ensure_ascii=False),
    }


def score_extractions() -> int:
    """Rerun scoring for all current study extractions and aggregate summaries."""

    init_db()
    classify_extractions(aggregate=False)
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
        conn.execute("DELETE FROM scores")
        for row in rows:
            scored = score_row(row)
            conn.execute(
                """
                INSERT INTO scores (
                    pmid, intervention_canonical, intervention_family, intervention_category,
                    neuroplasticity_potential, clinical_evidence_strength,
                    safety_score, practicality_score, overall_score,
                    study_quality_tier, scoring_notes, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    scored["pmid"],
                    scored["intervention_canonical"],
                    scored["intervention_family"],
                    scored["intervention_category"],
                    scored["neuroplasticity_potential"],
                    scored["clinical_evidence_strength"],
                    scored["safety_score"],
                    scored["practicality_score"],
                    scored["overall_score"],
                    scored["study_quality_tier"],
                    scored["scoring_notes"],
                    utc_now(),
                ),
            )
    aggregate_interventions()
    LOGGER.info("Scored %s extracted studies", len(rows))
    return len(rows)
