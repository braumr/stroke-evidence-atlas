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
    "forced-use therapy": "Constraint-Induced Movement Therapy",
    "forced use therapy": "Constraint-Induced Movement Therapy",
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
    "virtual reality rehabilitation": "Virtual Reality Rehabilitation",
    "mirror therapy": "Mirror Therapy",
    "action observation": "Mirror Therapy",
    "action observation therapy": "Mirror Therapy",
    "motor imagery": "Motor Imagery / Mental Practice",
    "mental practice": "Motor Imagery / Mental Practice",
    "robot-assisted therapy": "Robot-Assisted Rehabilitation",
    "robot assisted therapy": "Robot-Assisted Rehabilitation",
    "robotic therapy": "Robot-Assisted Rehabilitation",
    "robot-assisted rehabilitation": "Robot-Assisted Rehabilitation",
    "robot assisted rehabilitation": "Robot-Assisted Rehabilitation",
    "aerobic exercise": "Aerobic Exercise",
    "aerobic training": "Aerobic Exercise",
    "resistance exercise": "Resistance Training",
    "resistance training": "Resistance Training",
    "strength training": "Resistance Training",
    "yoga": "Yoga",
    "tai chi": "Tai Chi",
    "tai chi chuan": "Tai Chi",
    "electroacupuncture": "Electroacupuncture",
}

FAMILY_KEYWORDS = [
    ("Sleep / Circadian Recovery", ["sleep", "sleep apnea", "circadian", "melatonin"]),
    (
        "Nutrition / Metabolic Support",
        ["nutrition", "protein intake", "vitamin d", "omega 3", "omega-3", "creatine", "malnutrition", "gut microbiome", "metabolic support"],
    ),
    (
        "Inflammation / Immune / Biological Repair",
        ["neuroinflammation", "inflammation", "immune", "microglia", "cytokine", "biological repair"],
    ),
    (
        "Pharmacologic / Molecular Recovery",
        ["bdnf", "synaptogenesis", "axon sprouting", "neurogenesis", "molecular", "cellular repair", "pharmac", "drug", "antagonist", "ccr5", "15-hetre", "15 hydroxy"],
    ),
    (
        "Vascular Risk / Cardiometabolic Management",
        ["blood pressure", "vascular risk", "cardiometabolic", "diabetes", "lipid"],
    ),
    ("Depression / Mood / Motivation", ["depression", "motivation", "engagement", "fatigue", "mood"]),
    ("Caregiver / Family Training", ["caregiver", "family-assisted", "family assisted", "family training"]),
    ("Home / Community / Telerehabilitation", ["home rehabilitation", "home-based", "community rehabilitation", "outpatient", "telerehabilitation", "remote therapy"]),
    ("Constraint-Induced Movement Therapy", ["constraint", "cimt", "forced use"]),
    ("Functional Electrical Stimulation", ["functional electrical stimulation", "fes"]),
    ("Neuromuscular Electrical Stimulation", ["neuromuscular electrical stimulation", "nmes"]),
    ("Electrical Stimulation", ["peroneal nerve stimulation", "electrical stimulation", "electric stimulation"]),
    ("Noninvasive Brain Stimulation", ["tdcs", "rtms", "tms", "transcranial direct current stimulation", "transcranial magnetic stimulation", "noninvasive cortical stimulation"]),
    ("Vagus Nerve Stimulation", ["vagus nerve stimulation", "vns"]),
    ("Brain-Computer Interface Rehabilitation", ["brain-computer interface", "brain computer interface", "bci"]),
    ("Virtual Reality / Digital Rehabilitation", ["virtual reality", "vr rehabilitation", "mixed reality", "exergaming", "serious game"]),
    ("Robotics / Assistive Technology", ["robot", "exoskeleton", "assistive technology"]),
    ("Speech / Language / Aphasia Rehabilitation", ["speech", "language", "aphasia", "dysarthria", "be clear"]),
    ("Cognitive Rehabilitation", ["cognitive training", "cognitive rehabilitation", "memory rehabilitation", "attention training", "executive function", "neuropsychological"]),
    ("Neglect / Perceptual Rehabilitation", ["neglect", "perceptual"]),
    ("Mind-Body / Behavioral Rehabilitation", ["mindfulness", "meditation", "yoga", "tai chi", "behavioral"]),
    ("Music / Art / Enriched Activity Therapy", ["music", "art therapy", "dance", "enriched activity"]),
    ("Exercise / Physical Conditioning", ["exercise", "aerobic", "resistance", "strength", "fitness", "treadmill", "high intensity interval", "hiit", "cardiorespiratory"]),
    ("Gait / Balance Rehabilitation", ["gait", "walking", "stepping", "balance", "locomotor"]),
    ("Upper-Limb Rehabilitation", ["upper limb", "upper-limb", "arm", "hand"]),
    ("Assessment / Outcome Measurement", ["outcome scale", "assessment", "measurement", "reliability", "predictive recovery model", "prediction model"]),
    ("Diagnostic / Biomarker", ["biomarker", "diagnostic", "imaging marker", "prognostic"]),
    ("General Neuroplasticity / Mechanisms", ["neuroplasticity", "plasticity", "mechanisms of plasticity", "neural recovery"]),
    ("General Neurorehabilitation", ["neurorehabilitation", "multimodal", "rehabilitation program", "general recovery", "stroke rehabilitation"]),
    ("Environmental Enrichment", ["environmental enrichment", "enriched environment"]),
]

NON_SPECIFIC_VALUES = {
    "unknown",
    "not applicable",
    "not_applicable",
    "none",
}


def _normalize_key(value: str) -> str:
    cleaned = clean_text(value).lower()
    cleaned = cleaned.replace("/", " ").replace("‐", "-").replace("‑", "-").replace("–", "-").replace("—", "-")
    cleaned = re.sub(r"[^a-z0-9+\-\s]", " ", cleaned)
    cleaned = cleaned.replace("-", " ")
    return re.sub(r"\s+", " ", cleaned).strip()


def _clean_readable(value: str) -> str:
    cleaned = clean_text(value)
    cleaned = cleaned.replace("‐", "-").replace("‑", "-").replace("–", "-").replace("—", "-")
    return re.sub(r"\s+", " ", cleaned).strip()


def normalize_intervention(raw_intervention: str | None) -> str:
    """Return a canonical intervention name without over-normalizing."""

    cleaned = _clean_readable(raw_intervention or "")
    if not cleaned or cleaned.lower() == "unknown":
        return "unknown"

    key = _normalize_key(cleaned)
    for synonym, canonical in SYNONYM_MAP.items():
        if key == _normalize_key(synonym):
            return canonical

    for synonym, canonical in SYNONYM_MAP.items():
        normalized_synonym = _normalize_key(synonym)
        if re.search(rf"\b{re.escape(normalized_synonym)}\b", key):
            return canonical

    return cleaned


def intervention_family(
    raw_intervention: str | None,
    canonical_intervention: str | None = None,
    intervention_category: str | None = None,
    evidence_text: str | None = None,
) -> str:
    """Return a user-facing intervention family for aggregation and browsing."""

    raw = _clean_readable(raw_intervention or "")
    canonical = _clean_readable(canonical_intervention or "")
    category = _clean_readable(intervention_category or "")
    evidence = _clean_readable(evidence_text or "")
    if (
        (not raw or raw.lower() in NON_SPECIFIC_VALUES)
        and (not canonical or canonical.lower() in NON_SPECIFIC_VALUES)
        and (not category or category.lower() in NON_SPECIFIC_VALUES)
        and not evidence
    ):
        return "Unspecified / not intervention-specific"

    combined = _normalize_key(" ".join(part for part in [raw, canonical, category, evidence] if part))

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
        "speech_language": "Speech / Language / Aphasia Rehabilitation",
        "cognitive_rehab": "Cognitive Rehabilitation",
        "neuromodulation": "Noninvasive Brain Stimulation",
        "robotics": "Robotics / Assistive Technology",
        "virtual_reality": "Virtual Reality / Digital Rehabilitation",
        "electrical_stimulation": "Electrical Stimulation",
        "exercise": "Exercise / Physical Conditioning",
        "mind_body": "Mind-Body / Behavioral Rehabilitation",
        "nutrition_sleep_systemic": "Other Specific Recovery Domain",
        "caregiver_home": "Home / Community / Telerehabilitation",
        "pharmacologic": "Pharmacologic / Molecular Recovery",
        "diagnostic_biomarker": "Diagnostic / Biomarker",
    }
    if category in category_map:
        return category_map[category]

    return canonical or raw or "Unspecified / not intervention-specific"
