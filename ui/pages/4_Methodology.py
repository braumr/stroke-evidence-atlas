"""Methodology page for the Stroke Recovery Atlas."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


st.set_page_config(page_title="Methodology", layout="wide")
st.markdown(
    """
    <style>
    a[data-testid="stSidebarNavLink"] span[label="app"] p {
        font-size: 0;
    }
    a[data-testid="stSidebarNavLink"] span[label="app"] p::after {
        content: "home";
        font-size: 1rem;
    }
    .methodology-section {
        margin-bottom: 1.25rem;
    }
    .methodology-section p,
    .methodology-section li {
        line-height: 1.55;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Methodology")
st.write(
    "Stroke Recovery Atlas organizes PubMed-indexed stroke recovery literature into searchable "
    "recovery areas, structured paper details, and transparent evidence signals."
)

st.markdown(
    """
    <div class="methodology-section">
    <h3>Data Source</h3>
    <p>
    The atlas uses PubMed records collected with a stroke recovery and neurorehabilitation search strategy.
    The current extraction layer is based on each paper's title and PubMed abstract.
    </p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="methodology-section">
    <h3>AI-Assisted Extraction</h3>
    <p>
    Abstracts are converted into structured fields including study type, recovery area, stroke type,
    stroke phase, intervention details, outcome measures, reported results, safety notes,
    neuroplasticity mechanisms, and source-provenance sentences when available.
    Missing fields are labeled as not reported in abstract, not applicable, or unknown.
    </p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="methodology-section">
    <h3>Recovery Groups and Subgroups</h3>
    <p>
    Paper-level extracted labels are normalized into recovery subgroups, then grouped into broader
    recovery groups such as Physical Rehabilitation, Cognition and Communication, Rehabilitation
    Technology, Brain and Nerve Stimulation, Lifestyle and Daily Health, Medical and Biological
    Recovery, Family and Home Support, Testing and Prediction, Recovery Science, and General
    Rehabilitation. Local taxonomy rules correct known synonym, spelling, and classification issues.
    </p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.subheader("Scoring Framework")
st.write(
    "Each extracted paper receives four component scores from 0 to 100. The overall score is a "
    "weighted evidence-navigation signal, not a formal treatment-effect estimate."
)
weights = pd.DataFrame(
    [
        {
            "component": "Neuroplasticity potential",
            "weight": "40%",
            "what it reflects": "Mechanistic rationale, neuroplasticity mechanisms, intensity, repetition, feedback, and related abstract signals.",
        },
        {
            "component": "Clinical evidence strength",
            "weight": "35%",
            "what it reflects": "Study design, human evidence level, sample size, stroke specificity, and intervention specificity.",
        },
        {
            "component": "Safety",
            "weight": "15%",
            "what it reflects": "Reported tolerability, adverse events, and category-level safety considerations.",
        },
        {
            "component": "Practicality",
            "weight": "10%",
            "what it reflects": "Likely real-world feasibility based on recovery group, setting, equipment needs, and delivery context.",
        },
    ]
)
st.dataframe(weights, width="stretch", hide_index=True)

st.markdown(
    """
    <div class="methodology-section">
    <h3>Ranking Logic</h3>
    <p>
    Recovery subgroups are ranked by their average overall score across included papers after filters are applied.
    The ranking combines neuroplasticity rationale, clinical evidence strength, safety, and practicality rather than
    ranking by paper count alone.
    </p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="methodology-section">
    <h3>Evidence Tiers</h3>
    <p>
    Evidence tiers are assigned at the recovery subgroup level using study mix, human-study count,
    review/RCT presence, average clinical evidence strength, and conflicting effect directions.
    Tiers include strong clinical evidence, moderate clinical evidence, emerging evidence,
    conflicting evidence, mechanistic/preclinical only, and insufficient evidence.
    </p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="methodology-section">
    <h3>Current Scope</h3>
    <p>
    The current version is abstract-based. It is designed for evidence discovery, comparison, and source auditing.
    Future versions may incorporate full-text sections where legally accessible, refine recovery taxonomy with domain
    experts, and update score weights or thresholds as the methodology matures.
    </p>
    </div>
    """,
    unsafe_allow_html=True,
)
