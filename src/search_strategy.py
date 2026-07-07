"""Structured PubMed search strategy for Version 1."""

from __future__ import annotations


STROKE_ABI_CONCEPT = """
(
  "Stroke"[Mesh] OR stroke[Title/Abstract] OR "ischemic stroke"[Title/Abstract]
  OR "haemorrhagic stroke"[Title/Abstract] OR "hemorrhagic stroke"[Title/Abstract]
  OR "intracerebral hemorrhage"[Title/Abstract] OR "intracerebral haemorrhage"[Title/Abstract]
  OR "Brain Injuries"[Mesh] OR "acquired brain injury"[Title/Abstract]
)
"""


QUERY_DOMAINS = [
    {
        "key": "core",
        "name": "Core stroke rehabilitation",
        "coverage": "Stroke rehabilitation, neurorehabilitation, recovery, and neuroplasticity.",
        "rehab_concept": """
        ("Rehabilitation"[Mesh] OR rehabilitation[Title/Abstract] OR neurorehabilitation[Title/Abstract]
         OR recovery[Title/Abstract] OR neuroplasticity[Title/Abstract] OR plasticity[Title/Abstract])
        """,
    },
    {
        "key": "motor",
        "name": "Motor recovery",
        "coverage": "Motor learning, task practice, gait, balance, upper/lower limb rehab, PT, and OT.",
        "rehab_concept": """
        ("Motor Skills"[Mesh] OR "Physical Therapy Modalities"[Mesh] OR "Occupational Therapy"[Mesh]
         OR "motor learning"[Title/Abstract] OR "task-specific training"[Title/Abstract]
         OR "repetitive task practice"[Title/Abstract] OR "gait training"[Title/Abstract]
         OR "balance training"[Title/Abstract] OR "upper limb rehabilitation"[Title/Abstract]
         OR "lower limb rehabilitation"[Title/Abstract] OR "physical therapy"[Title/Abstract]
         OR "occupational therapy"[Title/Abstract])
        """,
    },
    {
        "key": "cimt",
        "name": "Constraint-induced movement therapy and task practice",
        "coverage": "CIMT, modified CIMT, forced use therapy, and repetitive task practice.",
        "rehab_concept": """
        ("constraint-induced movement therapy"[Title/Abstract] OR "constraint induced movement therapy"[Title/Abstract]
         OR CIMT[Title/Abstract] OR mCIMT[Title/Abstract] OR "modified constraint-induced"[Title/Abstract]
         OR "forced use therapy"[Title/Abstract] OR "repetitive task practice"[Title/Abstract])
        """,
    },
    {
        "key": "imagery_mirror",
        "name": "Mirror therapy, motor imagery, and action observation",
        "coverage": "Mirror therapy, motor imagery, action observation, mental practice, and sensorimotor imagery.",
        "rehab_concept": """
        ("mirror therapy"[Title/Abstract] OR "motor imagery"[Title/Abstract]
         OR "action observation"[Title/Abstract] OR "mental practice"[Title/Abstract]
         OR "sensorimotor imagery"[Title/Abstract])
        """,
    },
    {
        "key": "robotics",
        "name": "Robotics and exoskeletons",
        "coverage": "Robot-assisted therapy, robotic devices, exoskeletons, gait robots, and upper limb robots.",
        "rehab_concept": """
        ("Robotics"[Mesh] OR robotic[Title/Abstract] OR "robot-assisted"[Title/Abstract]
         OR "robot assisted"[Title/Abstract] OR exoskeleton[Title/Abstract]
         OR "gait robot"[Title/Abstract] OR "upper limb robot"[Title/Abstract])
        """,
    },
    {
        "key": "virtual_reality",
        "name": "Virtual reality and exergaming",
        "coverage": "Virtual reality, exergaming, serious games, and augmented reality.",
        "rehab_concept": """
        ("Virtual Reality"[Mesh] OR "virtual reality"[Title/Abstract] OR "VR rehabilitation"[Title/Abstract]
         OR exergaming[Title/Abstract] OR "serious games"[Title/Abstract]
         OR "augmented reality"[Title/Abstract])
        """,
    },
    {
        "key": "neuromodulation",
        "name": "Electrical stimulation and neuromodulation",
        "coverage": "FES, NMES, TMS, rTMS, and tDCS.",
        "rehab_concept": """
        ("Electric Stimulation Therapy"[Mesh] OR "Transcranial Magnetic Stimulation"[Mesh]
         OR "functional electrical stimulation"[Title/Abstract] OR FES[Title/Abstract]
         OR "neuromuscular electrical stimulation"[Title/Abstract] OR NMES[Title/Abstract]
         OR "transcranial magnetic stimulation"[Title/Abstract] OR TMS[Title/Abstract]
         OR rTMS[Title/Abstract] OR "repetitive TMS"[Title/Abstract]
         OR "transcranial direct current stimulation"[Title/Abstract] OR tDCS[Title/Abstract])
        """,
    },
    {
        "key": "exercise",
        "name": "Exercise and conditioning",
        "coverage": "Aerobic exercise, resistance training, treadmill training, HIIT, and fitness.",
        "rehab_concept": """
        ("Exercise Therapy"[Mesh] OR "aerobic exercise"[Title/Abstract] OR "aerobic training"[Title/Abstract]
         OR "resistance exercise"[Title/Abstract] OR "resistance training"[Title/Abstract]
         OR "strength training"[Title/Abstract] OR "treadmill training"[Title/Abstract]
         OR "high-intensity interval training"[Title/Abstract] OR HIIT[Title/Abstract]
         OR "cardiorespiratory fitness"[Title/Abstract])
        """,
    },
    {
        "key": "speech_cognition",
        "name": "Speech, aphasia, cognition, and neglect",
        "coverage": "Speech/language therapy, aphasia, cognition, memory, attention, executive function, and neglect.",
        "rehab_concept": """
        ("Speech Therapy"[Mesh] OR "Cognitive Remediation"[Mesh] OR "speech therapy"[Title/Abstract]
         OR "aphasia therapy"[Title/Abstract] OR "language rehabilitation"[Title/Abstract]
         OR "cognitive rehabilitation"[Title/Abstract] OR "memory rehabilitation"[Title/Abstract]
         OR "attention training"[Title/Abstract] OR "executive function"[Title/Abstract]
         OR "neglect rehabilitation"[Title/Abstract])
        """,
    },
    {
        "key": "mind_body",
        "name": "Mind-body and behavioral interventions",
        "coverage": "Yoga, tai chi, mindfulness, meditation, music therapy, dance therapy, mood, and motivation.",
        "rehab_concept": """
        (yoga[Title/Abstract] OR "tai chi"[Title/Abstract] OR "tai ji"[Title/Abstract]
         OR meditation[Title/Abstract] OR mindfulness[Title/Abstract] OR "music therapy"[Title/Abstract]
         OR "dance therapy"[Title/Abstract] OR depression[Title/Abstract] OR motivation[Title/Abstract])
        """,
    },
    {
        "key": "systemic",
        "name": "Sleep, circadian rhythm, nutrition, and systemic factors",
        "coverage": "Sleep, sleep apnea, circadian rhythm, nutrition, supplements, inflammation, microbiome, and BP.",
        "rehab_concept": """
        (sleep[Title/Abstract] OR "sleep apnea"[Title/Abstract] OR "circadian rhythm"[Title/Abstract]
         OR nutrition[Title/Abstract] OR "protein intake"[Title/Abstract] OR "vitamin D"[Title/Abstract]
         OR "omega-3"[Title/Abstract] OR creatine[Title/Abstract] OR inflammation[Title/Abstract]
         OR "gut microbiome"[Title/Abstract] OR "blood pressure"[Title/Abstract])
        """,
    },
    {
        "key": "caregiver_home",
        "name": "Caregiver and home rehabilitation",
        "coverage": "Caregiver training, home rehab, telerehabilitation, community rehab, outpatient/intensive rehab.",
        "rehab_concept": """
        ("caregiver training"[Title/Abstract] OR "home-based rehabilitation"[Title/Abstract]
         OR telerehabilitation[Title/Abstract] OR "community rehabilitation"[Title/Abstract]
         OR "outpatient rehabilitation"[Title/Abstract] OR "intensive rehabilitation"[Title/Abstract])
        """,
    },
]


def build_query(rehab_concept: str) -> str:
    """Combine stroke/ABI and domain concepts into a PubMed query."""

    return f"{STROKE_ABI_CONCEPT} AND {rehab_concept}"


def get_query_domains(query_domain: str | None = None) -> list[dict[str, str]]:
    """Return configured query domains, optionally narrowed by key."""

    domains = []
    for domain in QUERY_DOMAINS:
        hydrated = dict(domain)
        hydrated["query"] = build_query(domain["rehab_concept"])
        domains.append(hydrated)

    if query_domain:
        matches = [domain for domain in domains if domain["key"] == query_domain]
        if not matches:
            valid = ", ".join(domain["key"] for domain in domains)
            raise ValueError(f"Unknown query domain '{query_domain}'. Valid domains: {valid}")
        return matches
    return domains
