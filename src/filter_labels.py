"""User-facing labels and matching logic for app filters."""

from __future__ import annotations

from typing import Iterable

from src.utils import clean_text, normalize_missing_label

STROKE_TYPE_FILTER_OPTIONS = [
    "Ischemic Stroke",
    "Hemorrhagic Stroke",
    "Mixed Stroke Types",
    "Not Stroke-Specific / Not Reported",
]

EFFECT_DIRECTION_FILTER_OPTIONS = [
    "Positive",
    "Negative",
    "No Effect",
    "Mixed or Unclear",
]

STROKE_PHASE_FILTER_OPTIONS = [
    "Acute",
    "Subacute",
    "Chronic",
    "Multiple Phases",
    "Not Reported / Not Applicable",
]

STUDY_TYPE_UNKNOWN_LABEL = "Unknown / Not Reported"

STUDY_TYPE_DISPLAY_LABELS = {
    "animal_study": "Animal Study",
    "case_control_study": "Case-Control Study",
    "case_report": "Case Report",
    "case_series": "Case Series",
    "cohort_study": "Cohort Study",
    "epidemiology": "Epidemiology",
    "feasibility_study": "Feasibility Study",
    "mechanistic_study": "Mechanistic Study",
    "meta_analysis": "Meta-Analysis",
    "mixed_methods": "Mixed Methods",
    "narrative_review": "Narrative Review",
    "pilot_study": "Pilot Study",
    "protocol": "Protocol",
    "qualitative": "Qualitative",
    "randomized_controlled_trial": "Randomized Controlled Trial",
    "systematic_review": "Systematic Review",
}


def normalize_stroke_type_label(value: object) -> str:
    """Map extracted stroke-type labels to user-facing filter categories."""

    normalized = normalize_missing_label(value, "not reported in abstract")
    if not isinstance(normalized, str):
        return "Not Stroke-Specific / Not Reported"

    cleaned = clean_text(normalized).lower().replace("-", "_")
    cleaned = cleaned.replace(" / ", "|").replace("/", "|")
    if cleaned in {"ischemic", "ischaemic", "ischemic_stroke", "ischaemic_stroke"}:
        return "Ischemic Stroke"
    if cleaned in {
        "hemorrhagic",
        "haemorrhagic",
        "hemorrhagic_stroke",
        "haemorrhagic_stroke",
        "intracerebral_hemorrhage",
        "intracerebral_haemorrhage",
        "subarachnoid_hemorrhage",
        "subarachnoid_haemorrhage",
    }:
        return "Hemorrhagic Stroke"
    if cleaned in {
        "mixed",
        "mixed_stroke",
        "ischemic|hemorrhagic",
        "ischaemic|haemorrhagic",
        "ischemic | hemorrhagic",
        "ischaemic | haemorrhagic",
    }:
        return "Mixed Stroke Types"
    return "Not Stroke-Specific / Not Reported"


def stroke_type_matches_filter(value: object, selected_labels: Iterable[str]) -> bool:
    """Return whether a raw stroke type belongs in the selected display filters."""

    selected = set(selected_labels)
    if not selected:
        return True
    label = normalize_stroke_type_label(value)
    if label in selected:
        return True
    if label == "Mixed Stroke Types" and (
        "Ischemic Stroke" in selected or "Hemorrhagic Stroke" in selected
    ):
        return True
    return False


def normalize_effect_direction_label(value: object) -> str:
    """Map extracted effect-direction labels to user-facing filter categories."""

    normalized = normalize_missing_label(value, "unknown")
    if not isinstance(normalized, str):
        return "Mixed or Unclear"

    cleaned = clean_text(normalized).lower().replace("-", "_").replace(" ", "_")
    if cleaned in {"positive", "beneficial", "improved", "improvement"}:
        return "Positive"
    if cleaned in {"negative", "harmful", "worse", "worsened", "worsening"}:
        return "Negative"
    if cleaned in {"no_effect", "no_clear_effect", "neutral", "no_change", "none"}:
        return "No Effect"
    return "Mixed or Unclear"


def effect_direction_matches_filter(value: object, selected_labels: Iterable[str]) -> bool:
    """Return whether a raw effect direction belongs in the selected display filters."""

    selected = set(selected_labels)
    if not selected:
        return True
    return normalize_effect_direction_label(value) in selected


def normalize_stroke_phase_label(value: object) -> str:
    """Map extracted stroke-phase labels to user-facing filter categories."""

    normalized = normalize_missing_label(value, "not reported in abstract")
    if not isinstance(normalized, str):
        return "Not Reported / Not Applicable"

    cleaned = clean_text(normalized).lower().replace("-", "_")
    cleaned = cleaned.replace(" / ", "|").replace("/", "|").replace(" ", "_")
    if cleaned in {
        "unknown",
        "not_applicable",
        "not_reported",
        "not_reported_in_abstract",
    }:
        return "Not Reported / Not Applicable"
    if cleaned == "acute":
        return "Acute"
    if cleaned in {"subacute", "post_acute", "recovery", "rehabilitation"}:
        return "Subacute"
    if cleaned in {"chronic", "late"}:
        return "Chronic"
    if any(separator in cleaned for separator in {"|", ","}) or cleaned == "mixed":
        return "Multiple Phases"
    return "Not Reported / Not Applicable"


def stroke_phase_matches_filter(value: object, selected_labels: Iterable[str]) -> bool:
    """Return whether a raw stroke phase belongs in the selected display filters."""

    selected = set(selected_labels)
    if not selected:
        return True
    return normalize_stroke_phase_label(value) in selected


def normalize_study_type_label(value: object) -> str:
    """Map extracted study-type labels to user-facing filter labels."""

    normalized = normalize_missing_label(value, "unknown")
    if not isinstance(normalized, str):
        return STUDY_TYPE_UNKNOWN_LABEL

    cleaned = clean_text(normalized).lower().replace("-", "_").replace(" ", "_")
    if cleaned in {
        "unknown",
        "not_applicable",
        "not_reported",
        "not_reported_in_abstract",
    }:
        return STUDY_TYPE_UNKNOWN_LABEL
    label = STUDY_TYPE_DISPLAY_LABELS.get(cleaned)
    if label:
        return label
    return " ".join(part.capitalize() for part in cleaned.split("_") if part)


def study_type_filter_options(values: Iterable[object]) -> list[str]:
    """Return sorted user-facing study-type filter options from raw values."""

    labels = {normalize_study_type_label(value) for value in values}
    return sorted(labels, key=lambda label: (label == STUDY_TYPE_UNKNOWN_LABEL, label))


def study_type_matches_filter(value: object, selected_labels: Iterable[str]) -> bool:
    """Return whether a raw study type belongs in the selected display filters."""

    selected = set(selected_labels)
    if not selected:
        return True
    return normalize_study_type_label(value) in selected
