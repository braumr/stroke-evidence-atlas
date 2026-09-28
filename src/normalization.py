"""Recovery taxonomy and extracted-label normalization."""

from __future__ import annotations

import re
import csv
import os
from pathlib import Path

from .utils import clean_text


TAXONOMY_MAPPING_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "exports"
    / "taxonomy_audit"
    / "proposed_subgroup_mapping_revised_final.csv"
)


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
        "Cranioplasty / Cranial Reconstruction",
        ["cranioplasty", "cranial reconstruction", "skull reconstruction", "titanium mesh", "cranial implant"],
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
    (
        "Exercise / Physical Conditioning",
        [
            "exercise",
            "aerobic",
            "resistance",
            "strength",
            "fitness",
            "treadmill",
            "high intensity interval",
            "hiit",
            "cardiorespiratory",
            "inspiratory muscle training",
            "respiratory muscle training",
            "breathing training",
            "diaphragm training",
            "imt",
        ],
    ),
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
    "not reported in abstract",
    "not applicable",
    "not_applicable",
    "none",
}

REVIEW_TOPIC = "Needs Taxonomy Review"
UNSPECIFIED_TOPIC = "Unspecified / not intervention-specific"

SUBGROUP_ALIASES = {
    "citicoline": "Citicoline",
    "ceraxon": "Citicoline",
    "ceraxon citicoline": "Citicoline",
    "cerebrolysin": "Cerebrolysin",
    "mexidol": "Mexidol",
    "cytoflavin": "Cytoflavin",
    "edonerpic maleate": "Edonerpic Maleate",
    "virtual reality rehabilitation": "Virtual Reality / Digital Rehabilitation",
    "robot assisted rehabilitation": "Robotics / Assistive Technology",
    "robot assisted therapy": "Robotics / Assistive Technology",
    "robotic therapy": "Robotics / Assistive Technology",
    "functional electrical stimulation": "Functional Electrical Stimulation",
    "neuromuscular electrical stimulation": "Neuromuscular Electrical Stimulation",
    "transcranial direct current stimulation": "Noninvasive Brain Stimulation",
    "repetitive transcranial magnetic stimulation": "Noninvasive Brain Stimulation",
    "transcranial magnetic stimulation": "Noninvasive Brain Stimulation",
    "non invasive brain stimulation": "Noninvasive Brain Stimulation",
    "noninvasive brain stimulation": "Noninvasive Brain Stimulation",
    "vagus nerve stimulation": "Vagus Nerve Stimulation",
    "vagus nerve stimulation paired with rehabilitation": "Vagus Nerve Stimulation",
    "electroacupuncture": "Electroacupuncture",
    "acupuncture": "Electroacupuncture",
    "constraint induced movement therapy": "Constraint-Induced Movement Therapy",
    "ci therapy": "Constraint-Induced Movement Therapy",
    "mirror therapy": "Mirror Therapy",
    "motor imagery mental practice": "Motor Imagery / Mental Practice",
    "motor imagery": "Motor Imagery / Mental Practice",
    "mental practice": "Motor Imagery / Mental Practice",
    "aerobic exercise": "Exercise / Physical Conditioning",
    "aerobic training": "Exercise / Physical Conditioning",
    "exercise training": "Exercise / Physical Conditioning",
    "inspiratory muscle training": "Exercise / Physical Conditioning",
    "inspiratory muscle training imt": "Exercise / Physical Conditioning",
    "respiratory muscle training": "Exercise / Physical Conditioning",
    "breathing training": "Exercise / Physical Conditioning",
    "diaphragm training": "Exercise / Physical Conditioning",
    "resistance training": "Exercise / Physical Conditioning",
    "strength training": "Exercise / Physical Conditioning",
    "cognitive rehabilitation": "Cognitive Rehabilitation",
    "neuropsychological rehabilitation": "Cognitive Rehabilitation",
    "speech language aphasia rehabilitation": "Speech / Language / Aphasia Rehabilitation",
    "aphasia rehabilitation": "Speech / Language / Aphasia Rehabilitation",
    "goal attainment scaling": "Assessment / Outcome Measurement",
    "cranioplasty": "Cranioplasty / Cranial Reconstruction",
    "cranial reconstruction": "Cranioplasty / Cranial Reconstruction",
    "skull reconstruction": "Cranioplasty / Cranial Reconstruction",
    "titanium mesh": "Cranioplasty / Cranial Reconstruction",
    "customized 3d titanium mesh plates": "Cranioplasty / Cranial Reconstruction",
    "electrostimulation": "Electrical Stimulation",
    "transcutaneous electrical nerve stimulation": "Electrical Stimulation",
    "tens": "Electrical Stimulation",
    "peripheral nerve stimulation": "Electrical Stimulation",
    "functional electrostimulation and bfb stabilometric postural control": "Electrical Stimulation",
    "continuous theta burst stimulation": "Noninvasive Brain Stimulation",
    "continuous theta burst stimulation ctbs": "Noninvasive Brain Stimulation",
    "intermittent theta burst stimulation": "Noninvasive Brain Stimulation",
    "intermittent theta burst stimulation itbs": "Noninvasive Brain Stimulation",
    "intermittent theta burst stimulation itbs combined with routine rehabilitation": "Noninvasive Brain Stimulation",
    "intermittent theta burst stimulation combined with task oriented training": "Noninvasive Brain Stimulation",
    "transcranial alternating current stimulation": "Noninvasive Brain Stimulation",
    "tacs": "Noninvasive Brain Stimulation",
    "hd transcranial burst electrostimulation": "Noninvasive Brain Stimulation",
    "attention process training": "Cognitive Rehabilitation",
    "attention rehabilitation": "Cognitive Rehabilitation",
    "cognitive strategy training": "Cognitive Rehabilitation",
    "computer based cognitive retraining": "Cognitive Rehabilitation",
    "cbcr": "Cognitive Rehabilitation",
    "metacognitive contextual approach": "Cognitive Rehabilitation",
    "communication partner training": "Speech / Language / Aphasia Rehabilitation",
    "lee silverman voice treatment": "Speech / Language / Aphasia Rehabilitation",
    "lsvt": "Speech / Language / Aphasia Rehabilitation",
    "multi dimensional voice program": "Speech / Language / Aphasia Rehabilitation",
    "mdvp": "Speech / Language / Aphasia Rehabilitation",
    "intensive cognitive communication rehabilitation": "Speech / Language / Aphasia Rehabilitation",
    "iccr": "Speech / Language / Aphasia Rehabilitation",
    "community based rehabilitation": "Home / Community / Telerehabilitation",
    "home care activity desk training": "Home / Community / Telerehabilitation",
    "hcad training": "Home / Community / Telerehabilitation",
    "home programs for rehabilitation": "Home / Community / Telerehabilitation",
    "home based therapy programme": "Home / Community / Telerehabilitation",
    "videoconferencing for community based rehabilitation": "Home / Community / Telerehabilitation",
    "animal assisted therapy": "Animal Assisted Therapy",
    "animal assisted therapy aat": "Animal Assisted Therapy",
    "ayurvedic rehabilitative treatment": "Ayurvedic Rehabilitative Treatment",
    "ayurvedic rehabilitative treatment art": "Ayurvedic Rehabilitative Treatment",
    "rehabilitation gaming system": "Rehabilitation Gaming System (RGS)",
    "rehabilitation gaming system rgs": "Rehabilitation Gaming System (RGS)",
    "tissue plasminogen activator": "Tissue Plasminogen Activator",
    "tissue plasminogen activator rtpa": "Tissue Plasminogen Activator",
    "vocational intervention program": "Vocational Intervention Program (VIP)",
    "vocational intervention program vip": "Vocational Intervention Program (VIP)",
    "vocational intervention program vip 2 0": "Vocational Intervention Program (VIP)",
    "inpatient rehabilitation": "Inpatient Rehabilitation",
    "inpatient rehabilitation intervention": "Inpatient Rehabilitation",
    "inpatient rehabilitation treatment": "Inpatient Rehabilitation",
    "botulinum toxin": "Botulinum Toxin",
    "botulinum toxin a and rehabilitation": "Botulinum Toxin",
    "botulinum toxin intervention": "Botulinum Toxin",
    "botulinum toxin treatment": "Botulinum Toxin",
    "amphetamine": "Amphetamine",
    "amphetamine treatment combined with rehabilitation": "Amphetamine",
    "early rehabilitation and nursing intervention": "Early Rehabilitation and Nursing Intervention (ERNI)",
    "early rehabilitation and nursing intervention erni": "Early Rehabilitation and Nursing Intervention (ERNI)",
    "early rehabilitation nursing": "Early Rehabilitation and Nursing Intervention (ERNI)",
    "early physical rehabilitation": "Early Physical Rehabilitation",
    "early physical rehabilitation therapy": "Early Physical Rehabilitation",
    "intrathecal baclofen": "Intrathecal Baclofen",
    "intrathecal baclofen therapy": "Intrathecal Baclofen",
    "p a c e a physical activity centred education programme": "Physical Activity Centred Education Programme (PACE)",
    "physical activity centred education programme": "Physical Activity Centred Education Programme (PACE)",
    "on road driving remediation": "On-Road Driving Remediation",
    "on road driving remediation program": "On-Road Driving Remediation",
    "oculomotor therapy": "Neglect / Perceptual Rehabilitation",
    "oculomotor training": "Neglect / Perceptual Rehabilitation",
    "oculomotor training omt": "Neglect / Perceptual Rehabilitation",
    "oculomotor based vision therapy vision rehabilitation": "Neglect / Perceptual Rehabilitation",
    "reading related oculomotor rehabilitation": "Neglect / Perceptual Rehabilitation",
    "versional oculomotor training": "Neglect / Perceptual Rehabilitation",
    "cognitive and vocational rehabilitation": "Vocational Rehabilitation",
    "early vocational rehabilitation protocol": "Vocational Rehabilitation",
    "social support and vocational rehabilitation": "Vocational Rehabilitation",
    "vocational rehabilitation": "Vocational Rehabilitation",
    "vocational rehabilitation framework": "Vocational Rehabilitation",
    "vocational rehabilitation intervention": "Vocational Rehabilitation",
    "vocational rehabilitation services": "Vocational Rehabilitation",
    "intensive rehabilitation": "Intensive Rehabilitation",
    "intensive rehabilitation therapy": "Intensive Rehabilitation",
    "intensive rehabilitation treatments": "Intensive Rehabilitation",
    "bimanual rehabilitation": "Bimanual Training",
    "bimanual training": "Bimanual Training",
    "multidisciplinary interventions": "Multidisciplinary Rehabilitation",
    "multidisciplinary treatment": "Multidisciplinary Rehabilitation",
    "active rehabilitation training": "General Neurorehabilitation",
    "active rehabilitation treatment": "General Neurorehabilitation",
    "physical rehabilitation": "General Physical Rehabilitation",
    "physical rehabilitation interventions": "General Physical Rehabilitation",
    "rehabilitation": "General Neurorehabilitation",
    "rehabilitation therapy": "General Neurorehabilitation",
    "rehabilitation treatment": "General Neurorehabilitation",
    "rehabilitation process": "General Neurorehabilitation",
    "rehabilitation measures": "General Neurorehabilitation",
    "rehabilitative training": "General Neurorehabilitation",
    "medical rehabilitation": "General Neurorehabilitation",
    "in patient rehabilitation": "Inpatient Rehabilitation",
    "in-patient rehabilitation": "Inpatient Rehabilitation",
    "intensive inpatient multidisciplinary rehabilitation": "Intensive Rehabilitation",
    "early mobilization": "Early Physical Rehabilitation",
    "motor rehabilitation": "General Physical Rehabilitation",
    "occupational therapy": "Occupational Therapy",
    "task specific training": "Task-Specific Training",
    "task-specific training": "Task-Specific Training",
    "neuromodulation techniques": "Noninvasive Brain Stimulation",
    "motor cortex stimulation": "Noninvasive Brain Stimulation",
    "stem cell transplantation": "Stem Cell Therapy",
    "cellex": "Cellex",
    "control design consign decision support tool": "Decision Support Tools",
    "control design decision support tool": "Decision Support Tools",
}

SUBGROUP_RECOVERY_GROUPS = {
    "Citicoline": "Medical and Biological Recovery",
    "Cerebrolysin": "Medical and Biological Recovery",
    "Mexidol": "Medical and Biological Recovery",
    "Cytoflavin": "Medical and Biological Recovery",
    "Edonerpic Maleate": "Medical and Biological Recovery",
    "Pharmacologic / Molecular Recovery": "Medical and Biological Recovery",
    "Inflammation / Immune / Biological Repair": "Medical and Biological Recovery",
    "Vascular Risk / Cardiometabolic Management": "Medical and Biological Recovery",
    "Cranioplasty / Cranial Reconstruction": "Medical and Biological Recovery",
    "Constraint-Induced Movement Therapy": "Physical Rehabilitation",
    "Mirror Therapy": "Physical Rehabilitation",
    "Motor Imagery / Mental Practice": "Physical Rehabilitation",
    "Exercise / Physical Conditioning": "Physical Rehabilitation",
    "Gait / Balance Rehabilitation": "Physical Rehabilitation",
    "Upper-Limb Rehabilitation": "Physical Rehabilitation",
    "Functional Electrical Stimulation": "Brain and Nerve Stimulation",
    "Neuromuscular Electrical Stimulation": "Brain and Nerve Stimulation",
    "Electrical Stimulation": "Brain and Nerve Stimulation",
    "Noninvasive Brain Stimulation": "Brain and Nerve Stimulation",
    "Vagus Nerve Stimulation": "Brain and Nerve Stimulation",
    "Electroacupuncture": "Brain and Nerve Stimulation",
    "Virtual Reality / Digital Rehabilitation": "Rehabilitation Technology",
    "Robotics / Assistive Technology": "Rehabilitation Technology",
    "Brain-Computer Interface Rehabilitation": "Rehabilitation Technology",
    "Speech / Language / Aphasia Rehabilitation": "Cognition and Communication",
    "Cognitive Rehabilitation": "Cognition and Communication",
    "Neglect / Perceptual Rehabilitation": "Cognition and Communication",
    "Caregiver / Family Training": "Family and Home Support",
    "Home / Community / Telerehabilitation": "Family and Home Support",
    "Assessment / Outcome Measurement": "Testing and Prediction",
    "Diagnostic / Biomarker": "Testing and Prediction",
    "Sleep / Circadian Recovery": "Lifestyle and Daily Health",
    "Nutrition / Metabolic Support": "Lifestyle and Daily Health",
    "Depression / Mood / Motivation": "Lifestyle and Daily Health",
    "Mind-Body / Behavioral Rehabilitation": "Lifestyle and Daily Health",
    "Music / Art / Enriched Activity Therapy": "Lifestyle and Daily Health",
    "Animal Assisted Therapy": "Lifestyle and Daily Health",
    "Environmental Enrichment": "Lifestyle and Daily Health",
    "General Neuroplasticity / Mechanisms": "Recovery Science",
    "General Neurorehabilitation": "General Rehabilitation",
    "Multiple / broad rehabilitation approaches": "General Rehabilitation",
    "Vocational Rehabilitation": "Family and Home Support",
    "Ayurvedic Rehabilitative Treatment": "Medical and Biological Recovery",
    "Rehabilitation Gaming System (RGS)": "Rehabilitation Technology",
    "Tissue Plasminogen Activator": "Medical and Biological Recovery",
    "Vocational Intervention Program (VIP)": "Family and Home Support",
    "Inpatient Rehabilitation": "General Rehabilitation",
    "Botulinum Toxin": "Medical and Biological Recovery",
    "Amphetamine": "Medical and Biological Recovery",
    "Early Rehabilitation and Nursing Intervention (ERNI)": "General Rehabilitation",
    "Early Physical Rehabilitation": "Physical Rehabilitation",
    "Intrathecal Baclofen": "Medical and Biological Recovery",
    "Physical Activity Centred Education Programme (PACE)": "Physical Rehabilitation",
    "On-Road Driving Remediation": "Testing and Prediction",
    "Intensive Rehabilitation": "General Rehabilitation",
    "Bimanual Training": "Physical Rehabilitation",
    "Multidisciplinary Rehabilitation": "General Rehabilitation",
    "General Physical Rehabilitation": "Physical Rehabilitation",
    "Occupational Therapy": "Physical Rehabilitation",
    "Task-Specific Training": "Physical Rehabilitation",
    "Stem Cell Therapy": "Medical and Biological Recovery",
    "Cellex": "Medical and Biological Recovery",
    "Decision Support Tools": "Testing and Prediction",
    REVIEW_TOPIC: "Other",
    UNSPECIFIED_TOPIC: "Other",
}

RECOVERY_GROUPS = (
    "Physical Rehabilitation",
    "Cognition and Communication",
    "Rehabilitation Technology",
    "Brain and Nerve Stimulation",
    "Lifestyle and Daily Health",
    "Medical and Biological Recovery",
    "Family and Home Support",
    "Testing and Prediction",
    "Recovery Science",
    "General Rehabilitation",
    "Other",
)

RECOVERY_GROUP_ALIASES = {
    "motor_rehab": "Physical Rehabilitation",
    "speech_language": "Cognition and Communication",
    "cognitive_rehab": "Cognition and Communication",
    "neuromodulation": "Brain and Nerve Stimulation",
    "robotics": "Rehabilitation Technology",
    "virtual_reality": "Rehabilitation Technology",
    "electrical_stimulation": "Brain and Nerve Stimulation",
    "exercise": "Physical Rehabilitation",
    "mind_body": "Lifestyle and Daily Health",
    "nutrition_sleep_systemic": "Lifestyle and Daily Health",
    "caregiver_home": "Family and Home Support",
    "home_rehab": "Family and Home Support",
    "pharmacologic": "Medical and Biological Recovery",
    "diagnostic_biomarker": "Testing and Prediction",
    "assessment_outcome_measurement": "Testing and Prediction",
    "assessment outcome measurement": "Testing and Prediction",
    "general_neuroplasticity": "Recovery Science",
    "general neuroplasticity": "Recovery Science",
    "general_neurorehabilitation": "General Rehabilitation",
    "general neurorehabilitation": "General Rehabilitation",
    "environmental_enrichment": "Lifestyle and Daily Health",
    "inflammation_immune_biological repair": "Medical and Biological Recovery",
    "inflammation immune biological repair": "Medical and Biological Recovery",
    "vascular_cardiometabolic_management": "Medical and Biological Recovery",
    "vascular cardiometabolic management": "Medical and Biological Recovery",
    "not_applicable": "Other",
    "not applicable": "Other",
    "unknown": "Other",
    "other": "Other",
}

RECOVERY_GROUP_KEYWORDS = [
    (
        "Brain and Nerve Stimulation",
        [
            "electroacupuncture",
            "functional electrical stimulation",
            "neuromuscular electrical stimulation",
            "electrical stimulation",
            "electric stimulation",
            "peroneal nerve stimulation",
            "vagus nerve stimulation",
            "vns",
            "tdcs",
            "rtms",
            "tms",
            "transcranial magnetic stimulation",
            "transcranial direct current stimulation",
            "noninvasive brain stimulation",
            "noninvasive cortical stimulation",
            "neuromodulation",
        ],
    ),
    (
        "Rehabilitation Technology",
        [
            "robot",
            "robotic",
            "exoskeleton",
            "assistive technology",
            "conversational agent",
            "conversational agents",
            "virtual reality",
            "mixed reality",
            "digital rehabilitation",
            "exergaming",
            "serious game",
            "brain computer interface",
            "brain computer",
            "bci",
        ],
    ),
    (
        "Cognition and Communication",
        [
            "aphasia",
            "speech",
            "language",
            "dysarthria",
            "cognitive",
            "memory",
            "attention",
            "executive function",
            "neuropsychological",
            "neglect",
            "perceptual",
        ],
    ),
    (
        "Family and Home Support",
        [
            "caregiver",
            "family",
            "home based",
            "home rehabilitation",
            "home program",
            "community rehabilitation",
            "telerehabilitation",
            "remote therapy",
        ],
    ),
    (
        "Lifestyle and Daily Health",
        [
            "sleep",
            "sleep apnea",
            "circadian",
            "fatigue",
            "nutrition",
            "protein",
            "vitamin",
            "omega 3",
            "omega",
            "creatine",
            "malnutrition",
            "mindfulness",
            "meditation",
            "yoga",
            "tai chi",
            "mood",
            "motivation",
            "depression",
            "engagement",
            "daily activity",
            "participation",
            "environmental enrichment",
            "enriched environment",
        ],
    ),
    (
        "Medical and Biological Recovery",
        [
            "pharmac",
            "drug",
            "medicine",
            "molecular",
            "cellular",
            "bdnf",
            "synaptogenesis",
            "axon",
            "neurogenesis",
            "inflammation",
            "neuroinflammation",
            "immune",
            "microglia",
            "cytokine",
            "metabolic",
            "blood pressure",
            "vascular risk",
            "cardiometabolic",
            "diabetes",
            "lipid",
            "surgical",
            "surgery",
            "cranioplasty",
            "cranial reconstruction",
            "skull reconstruction",
            "titanium mesh",
            "cranial implant",
            "neurotomy",
            "shunt",
            "ventricular shunt",
        ],
    ),
    (
        "Testing and Prediction",
        [
            "biomarker",
            "diagnostic",
            "assessment",
            "outcome measurement",
            "outcome scale",
            "measurement",
            "prediction",
            "predictive",
            "prognostic",
            "imaging marker",
            "reliability",
        ],
    ),
    (
        "Recovery Science",
        [
            "neuroplasticity",
            "plasticity",
            "mechanism",
            "neural recovery",
            "cortical reorganization",
            "animal model",
            "preclinical",
        ],
    ),
    (
        "Physical Rehabilitation",
        [
            "constraint",
            "cimt",
            "forced use",
            "mirror therapy",
            "motor imagery",
            "mental practice",
            "gait",
            "walking",
            "stepping",
            "balance",
            "locomotor",
            "upper limb",
            "arm",
            "hand",
            "exercise",
            "aerobic",
            "resistance",
            "strength",
            "fitness",
            "treadmill",
            "task specific",
            "task oriented",
            "motor rehabilitation",
            "physiotherapy",
            "stretch",
            "stretching",
        ],
    ),
    (
        "General Rehabilitation",
        [
            "neurorehabilitation",
            "rehabilitation program",
            "multidisciplinary rehabilitation",
            "complex rehabilitation",
            "comprehensive rehabilitation",
            "medical rehabilitation",
            "rehabilitation measures",
            "rehabilitation process",
            "rehabilitation techniques",
            "inpatient rehabilitation",
            "stroke unit",
            "neurointensive care",
            "stroke rehabilitation",
            "general recovery",
            "multimodal",
        ],
    ),
]


def _normalize_key(value: str) -> str:
    cleaned = clean_text(value).lower()
    cleaned = cleaned.replace("/", " ").replace("‐", "-").replace("‑", "-").replace("–", "-").replace("—", "-")
    cleaned = re.sub(r"[^a-z0-9+\-\s]", " ", cleaned)
    cleaned = cleaned.replace("-", " ")
    return re.sub(r"\s+", " ", cleaned).strip()


def taxonomy_key(value: str) -> str:
    """Return the stable normalized key used for taxonomy lookup and review queues."""

    return _normalize_key(value)


def _clean_readable(value: str) -> str:
    cleaned = clean_text(value)
    cleaned = cleaned.replace("‐", "-").replace("‑", "-").replace("–", "-").replace("—", "-")
    return re.sub(r"\s+", " ", cleaned).strip()


def _load_taxonomy_mapping() -> tuple[dict[str, str], dict[str, str]]:
    """Load the approved recovery subgroup taxonomy mapping, when available."""

    subgroup_map: dict[str, str] = {}
    subgroup_group_map: dict[str, str] = {}
    if not TAXONOMY_MAPPING_PATH.exists():
        return subgroup_map, subgroup_group_map

    with TAXONOMY_MAPPING_PATH.open(newline="") as file_obj:
        for row in csv.DictReader(file_obj):
            source_subgroup = _clean_readable(row.get("recovery_subgroup", ""))
            proposed_subgroup = _clean_readable(row.get("proposed_subgroup", ""))
            proposed_group = _clean_readable(row.get("proposed_group", ""))
            if not source_subgroup or not proposed_subgroup or not proposed_group:
                continue

            subgroup_map[_normalize_key(source_subgroup)] = proposed_subgroup
            subgroup_group_map[_normalize_key(proposed_subgroup)] = proposed_group

    return subgroup_map, subgroup_group_map


TAXONOMY_SUBGROUP_MAP, TAXONOMY_SUBGROUP_GROUPS = _load_taxonomy_mapping()


def _taxonomy_subgroup(value: str) -> str:
    readable = _clean_readable(value)
    return TAXONOMY_SUBGROUP_MAP.get(_normalize_key(readable), readable)


def _allow_open_research_topics() -> bool:
    """Return whether previously unseen extracted labels may become research topics."""

    value = os.getenv("STROKE_ATLAS_ALLOW_OPEN_TOPICS", "")
    return value.lower() in {"1", "true", "yes", "on"}


def is_approved_research_topic(value: str | None) -> bool:
    """Return whether a research topic belongs to the controlled taxonomy."""

    topic = _taxonomy_subgroup(_clean_readable(value or ""))
    if not topic:
        return False
    if topic in {REVIEW_TOPIC, UNSPECIFIED_TOPIC}:
        return True
    return _group_for_subgroup(topic) is not None


def recovery_domain_records() -> list[dict[str, object]]:
    """Return controlled Recovery Domain records for database seeding."""

    return [
        {
            "domain_name": domain,
            "display_order": index,
            "status": "active",
        }
        for index, domain in enumerate(RECOVERY_GROUPS, start=1)
    ]


def research_topic_records() -> list[dict[str, str]]:
    """Return controlled Research Topic records for database seeding."""

    topics: dict[str, tuple[str, str]] = {}
    for topic, domain in SUBGROUP_RECOVERY_GROUPS.items():
        topics[_taxonomy_subgroup(topic)] = (domain, "code")
    for key, topic in TAXONOMY_SUBGROUP_MAP.items():
        domain = TAXONOMY_SUBGROUP_GROUPS.get(_normalize_key(topic))
        if domain:
            topics[_taxonomy_subgroup(topic)] = (domain, "taxonomy_mapping")

    return [
        {
            "topic_name": topic,
            "recovery_domain": domain,
            "status": "active",
            "source": source,
        }
        for topic, (domain, source) in sorted(topics.items(), key=lambda item: (item[1][0], item[0]))
    ]


def taxonomy_alias_records() -> list[dict[str, str]]:
    """Return alias-to-topic records for database seeding and review."""

    records: dict[str, dict[str, str]] = {}
    for alias, topic in SUBGROUP_ALIASES.items():
        canonical_topic = _taxonomy_subgroup(topic)
        domain = _group_for_subgroup(canonical_topic) or "Other"
        records[_normalize_key(alias)] = {
            "alias_key": _normalize_key(alias),
            "alias_label": alias,
            "topic_name": canonical_topic,
            "recovery_domain": domain,
            "source": "alias",
        }
    for alias, canonical in SYNONYM_MAP.items():
        topic = intervention_family(canonical, canonical)
        domain = recovery_group(canonical_intervention=canonical, intervention_family_value=topic)
        records.setdefault(
            _normalize_key(alias),
            {
                "alias_key": _normalize_key(alias),
                "alias_label": alias,
                "topic_name": topic,
                "recovery_domain": domain,
                "source": "synonym",
            },
        )
    return sorted(records.values(), key=lambda row: row["alias_key"])


def _is_specific_label(value: str) -> bool:
    key = _normalize_key(value)
    return bool(key and key not in NON_SPECIFIC_VALUES)


def _alias_subgroup(value: str) -> str | None:
    key = _normalize_key(value)
    if not key:
        return None
    exact = SUBGROUP_ALIASES.get(key)
    if exact:
        return exact
    for alias, subgroup in SUBGROUP_ALIASES.items():
        if re.search(rf"\b{re.escape(alias)}\b", key):
            return subgroup
    return None


def _keyword_family(value: str) -> str | None:
    key = _normalize_key(value)
    if not key:
        return None
    for family, keywords in FAMILY_KEYWORDS:
        if any(keyword in key for keyword in keywords):
            return family
    return None


def _group_for_subgroup(value: str) -> str | None:
    subgroup = _clean_readable(value)
    key = _normalize_key(subgroup)
    if key in TAXONOMY_SUBGROUP_GROUPS:
        return TAXONOMY_SUBGROUP_GROUPS[key]

    subgroup = _taxonomy_subgroup(subgroup)
    key = _normalize_key(subgroup)
    taxonomy_group = TAXONOMY_SUBGROUP_GROUPS.get(key)
    if taxonomy_group:
        return taxonomy_group

    subgroup = _taxonomy_subgroup(_alias_subgroup(value) or subgroup)
    key = _normalize_key(subgroup)
    taxonomy_group = TAXONOMY_SUBGROUP_GROUPS.get(key)
    if taxonomy_group:
        return taxonomy_group

    for known_subgroup, group in SUBGROUP_RECOVERY_GROUPS.items():
        if key == _normalize_key(known_subgroup):
            return group
    return None


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


def recovery_group(
    raw_intervention: str | None = None,
    canonical_intervention: str | None = None,
    intervention_family_value: str | None = None,
    intervention_category: str | None = None,
    evidence_text: str | None = None,
) -> str:
    """Return the broad user-facing Recovery Domain for a paper or research topic."""

    raw = _clean_readable(raw_intervention or "")
    canonical = _clean_readable(canonical_intervention or "")
    family = _clean_readable(intervention_family_value or "")
    category = _clean_readable(intervention_category or "")
    evidence = _clean_readable(evidence_text or "")
    label_text = " ".join(part for part in [raw, canonical, family] if _is_specific_label(part))
    combined = _normalize_key(" ".join(part for part in [label_text, category, evidence] if part))
    category_key = _normalize_key(category)

    for part in [family, canonical, raw]:
        label_group = _group_for_subgroup(part)
        if label_group:
            return label_group

    label_group = _group_from_text(label_text)
    if label_group:
        return label_group

    alias = RECOVERY_GROUP_ALIASES.get(category_key)
    if alias and alias != "Other":
        return alias

    if category in RECOVERY_GROUPS and category != "Other":
        return category

    if not combined or combined in NON_SPECIFIC_VALUES:
        return "Other"

    evidence_group = _group_from_text(evidence)
    if evidence_group:
        return evidence_group

    if alias:
        return alias

    return "Other"


def _group_from_text(value: str) -> str | None:
    key = _normalize_key(value)
    if not key:
        return None
    for group, keywords in RECOVERY_GROUP_KEYWORDS:
        if any(keyword in key for keyword in keywords):
            return group
    return None


def intervention_family(
    raw_intervention: str | None,
    canonical_intervention: str | None = None,
    intervention_category: str | None = None,
    evidence_text: str | None = None,
) -> str:
    """Return a user-facing Research Topic for aggregation and browsing."""

    raw = _clean_readable(raw_intervention or "")
    canonical = _clean_readable(canonical_intervention or "")
    category = _clean_readable(intervention_category or "")
    evidence = _clean_readable(evidence_text or "")
    if (
        not _is_specific_label(raw)
        and not _is_specific_label(canonical)
        and not _is_specific_label(category)
        and not evidence
    ):
        return UNSPECIFIED_TOPIC

    label_parts = [part for part in [canonical, raw] if _is_specific_label(part)]
    label_text = " ".join(label_parts)
    combined = _normalize_key(" ".join(part for part in [label_text, category, evidence] if part))

    if not combined or combined in NON_SPECIFIC_VALUES:
        return UNSPECIFIED_TOPIC

    if label_text:
        for part in label_parts:
            alias = _alias_subgroup(part)
            if alias:
                return _taxonomy_subgroup(alias)
            family = _keyword_family(part)
            if family:
                return _taxonomy_subgroup(family)
        alias = _alias_subgroup(label_text)
        if alias:
            return _taxonomy_subgroup(alias)
        family = _keyword_family(label_text)
        if family:
            return _taxonomy_subgroup(family)
        comma_count = raw.count(",") + raw.count(";")
        if comma_count >= 2 and not any(term in combined for term in ["brain computer", "bci", "virtual reality"]):
            return _taxonomy_subgroup("Multiple / broad rehabilitation approaches")
        if _allow_open_research_topics():
            return _taxonomy_subgroup(canonical or raw)
        return REVIEW_TOPIC

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
        return _taxonomy_subgroup(category_map[category])

    family = _keyword_family(evidence)
    if family:
        return _taxonomy_subgroup(family)

    return UNSPECIFIED_TOPIC
