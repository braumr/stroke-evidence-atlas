"""Intervention name normalization."""

from __future__ import annotations

import re

from .utils import clean_text


SYNONYM_MAP = {
    "cimt": "Constraint-Induced Movement Therapy",
    "mcimt": "Constraint-Induced Movement Therapy",
    "modified cimt": "Constraint-Induced Movement Therapy",
    "constraint-induced movement therapy": "Constraint-Induced Movement Therapy",
    "constraint induced movement therapy": "Constraint-Induced Movement Therapy",
    "functional electrical stimulation": "Functional Electrical Stimulation",
    "fes": "Functional Electrical Stimulation",
    "neuromuscular electrical stimulation": "Neuromuscular Electrical Stimulation",
    "nmes": "Neuromuscular Electrical Stimulation",
    "transcranial direct current stimulation": "Transcranial Direct Current Stimulation",
    "tdcs": "Transcranial Direct Current Stimulation",
    "repetitive transcranial magnetic stimulation": "Repetitive Transcranial Magnetic Stimulation",
    "repetitive tms": "Repetitive Transcranial Magnetic Stimulation",
    "rtms": "Repetitive Transcranial Magnetic Stimulation",
    "transcranial magnetic stimulation": "Transcranial Magnetic Stimulation",
    "tms": "Transcranial Magnetic Stimulation",
    "virtual reality": "Virtual Reality Rehabilitation",
    "vr rehabilitation": "Virtual Reality Rehabilitation",
    "mirror therapy": "Mirror Therapy",
    "motor imagery": "Motor Imagery / Mental Practice",
    "mental practice": "Motor Imagery / Mental Practice",
    "robot-assisted therapy": "Robot-Assisted Rehabilitation",
    "robot assisted therapy": "Robot-Assisted Rehabilitation",
    "robotic therapy": "Robot-Assisted Rehabilitation",
    "robot-assisted rehabilitation": "Robot-Assisted Rehabilitation",
    "aerobic exercise": "Aerobic Exercise",
    "aerobic training": "Aerobic Exercise",
    "resistance exercise": "Resistance Training",
    "resistance training": "Resistance Training",
    "strength training": "Resistance Training",
    "yoga": "Yoga",
    "tai chi": "Tai Chi",
    "tai chi chuan": "Tai Chi",
}

FAMILY_KEYWORDS = [
    ("Constraint-Induced Movement Therapy", ["constraint", "cimt", "forced use"]),
    ("Functional Electrical Stimulation", ["functional electrical stimulation", "fes"]),
    ("Neuromuscular Electrical Stimulation", ["neuromuscular electrical stimulation", "nmes"]),
    ("Transcranial Direct Current Stimulation", ["tdcs", "transcranial direct current stimulation"]),
    ("Transcranial Magnetic Stimulation", ["rtms", "tms", "transcranial magnetic stimulation"]),
    ("Vagus Nerve Stimulation", ["vagus nerve stimulation", "vns"]),
    ("Brain-Computer Interface Rehabilitation", ["brain-computer interface", "brain computer interface", "bci"]),
    ("Virtual Reality / Technology-Assisted Rehabilitation", ["virtual reality", "vr ", "serious game", "technology"]),
    ("Robot-Assisted Rehabilitation", ["robot", "exoskeleton"]),
    ("Speech and Language Therapy", ["speech", "language", "aphasia", "dysarthria", "be clear"]),
    ("Cognitive and Behavioral Rehabilitation", ["cognitive", "behavior", "neuropsychological", "attention", "memory"]),
    ("Music Therapy", ["music"]),
    ("Exercise and Fitness Training", ["exercise", "aerobic", "resistance", "strength", "fitness"]),
    ("Gait and Stepping Training", ["gait", "walking", "stepping", "treadmill", "locomotor"]),
    ("Pharmacologic / Molecular Target", ["pharmac", "drug", "antagonist", "ccr5", "15-hetre", "15 hydroxy"]),
    ("Neurorehabilitation / Multimodal Rehabilitation", ["neurorehabilitation", "multimodal", "rehabilitation program"]),
]

NON_SPECIFIC_VALUES = {
    "unknown",
    "not applicable",
    "not_applicable",
    "none",
}


def _normalize_key(value: str) -> str:
    cleaned = clean_text(value).lower()
    cleaned = cleaned.replace("/", " ")
    cleaned = re.sub(r"[^a-z0-9+\-\s]", " ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def normalize_intervention(raw_intervention: str | None) -> str:
    """Return a canonical intervention name without over-normalizing."""

    cleaned = clean_text(raw_intervention)
    if not cleaned or cleaned.lower() == "unknown":
        return "unknown"

    key = _normalize_key(cleaned)
    if key in SYNONYM_MAP:
        return SYNONYM_MAP[key]

    for synonym, canonical in SYNONYM_MAP.items():
        if re.search(rf"\b{re.escape(synonym)}\b", key):
            return canonical

    return cleaned


def intervention_family(
    raw_intervention: str | None,
    canonical_intervention: str | None = None,
    intervention_category: str | None = None,
) -> str:
    """Return a user-facing intervention family for aggregation and browsing."""

    raw = clean_text(raw_intervention)
    canonical = clean_text(canonical_intervention)
    category = clean_text(intervention_category)
    if (
        (not raw or raw.lower() in NON_SPECIFIC_VALUES)
        and (not canonical or canonical.lower() in NON_SPECIFIC_VALUES)
        and (not category or category.lower() in NON_SPECIFIC_VALUES)
    ):
        return "Unspecified / not intervention-specific"

    combined = _normalize_key(" ".join(part for part in [raw, canonical, category] if part))

    if not combined or combined in NON_SPECIFIC_VALUES:
        return "Unspecified / not intervention-specific"

    comma_count = raw.count(",") + raw.count(";")
    if comma_count >= 2 and not any(term in combined for term in ["brain computer", "bci", "virtual reality"]):
        return "Multiple / broad rehabilitation approaches"

    for family, keywords in FAMILY_KEYWORDS:
        if any(keyword in combined for keyword in keywords):
            return family

    category_map = {
        "motor_rehab": "Motor Rehabilitation",
        "speech_language": "Speech and Language Therapy",
        "cognitive_rehab": "Cognitive and Behavioral Rehabilitation",
        "neuromodulation": "Neuromodulation",
        "robotics": "Robot-Assisted Rehabilitation",
        "virtual_reality": "Virtual Reality / Technology-Assisted Rehabilitation",
        "electrical_stimulation": "Electrical Stimulation",
        "exercise": "Exercise and Fitness Training",
        "mind_body": "Mind-Body Interventions",
        "nutrition_sleep_systemic": "Sleep, Nutrition, and Systemic Factors",
        "caregiver_home": "Caregiver and Home Rehabilitation",
        "pharmacologic": "Pharmacologic / Molecular Target",
    }
    if category in category_map:
        return category_map[category]

    return canonical or raw or "Unspecified / not intervention-specific"
