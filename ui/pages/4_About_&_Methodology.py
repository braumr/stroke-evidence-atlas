"""About and methodology page for the Stroke Recovery Atlas."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


st.set_page_config(page_title="About & Methodology", layout="wide")
st.markdown(
    """
    <style>
    a[data-testid="stSidebarNavLink"] span[label="app"] p {
        font-size: 0;
    }
    a[data-testid="stSidebarNavLink"] span[label="app"] p::after {
        content: "Home";
        font-size: 1rem;
    }
    .methodology-card {
        border-top: 1px solid rgba(120, 120, 120, 0.28);
        padding-top: 0.85rem;
        margin-bottom: 1.15rem;
    }
    .methodology-card h3 {
        font-size: 1.05rem;
        font-weight: 700;
        margin: 0 0 0.4rem 0;
    }
    .methodology-card p {
        font-size: 0.94rem;
        line-height: 1.52;
        margin: 0;
    }
    .scope-note {
        border-left: 3px solid rgba(46, 134, 171, 0.75);
        padding: 0.35rem 0 0.35rem 0.8rem;
        margin: 0.75rem 0 1.25rem 0;
        font-size: 0.95rem;
        line-height: 1.5;
        opacity: 0.82;
    }
    .formula-box {
        border: 1px solid rgba(120, 120, 120, 0.28);
        border-radius: 6px;
        padding: 0.85rem 1rem;
        margin: 0.55rem 0 1rem 0;
        font-size: 0.96rem;
        line-height: 1.6;
    }
    .chip-wrap {
        display: flex;
        flex-wrap: wrap;
        gap: 0.45rem;
        margin-top: 0.65rem;
    }
    .method-chip {
        border: 1px solid rgba(120, 120, 120, 0.35);
        border-radius: 999px;
        padding: 0.28rem 0.62rem;
        font-size: 0.86rem;
        line-height: 1.2;
        white-space: nowrap;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("About & Methodology")
st.write(
    "Stroke Recovery Atlas is an abstract-level research navigation tool. It organizes "
    "PubMed-indexed stroke recovery literature into recovery areas, structured paper details, "
    "and evidence signals that can be explored and audited."
)
st.markdown(
    """
    <div class="scope-note">
    It is designed for recovery discovery and source review, not medical advice or formal clinical guideline recommendations.
    </div>
    """,
    unsafe_allow_html=True,
)

source_col, extraction_col = st.columns(2)
with source_col:
    st.markdown(
        """
        <div class="methodology-card">
            <h3>Data Source</h3>
            <p>Stroke Recovery Atlas uses PubMed records collected through a stroke recovery and neurorehabilitation search strategy.</p>
            <p>The current extraction layer uses each paper’s title and PubMed abstract.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with extraction_col:
    st.markdown(
        """
        <div class="methodology-card">
            <h3>AI-Assisted Extraction</h3>
            <p>Abstracts are converted into structured fields such as study type, recovery area, stroke type, stroke phase, outcomes, safety notes, mechanisms, and supporting sentences.</p>
            <p>Missing fields are labeled as not reported in abstract, not applicable, or unknown.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown(
    """
    <div class="methodology-card">
        <h3>Recovery Taxonomy</h3>
        <p>Paper-level extracted labels are normalized into recovery subgroups, then grouped into broader recovery groups. Local taxonomy rules correct known synonym, spelling, and classification issues.</p>
        <div class="chip-wrap">
            <span class="method-chip">Physical Rehabilitation</span>
            <span class="method-chip">Cognition and Communication</span>
            <span class="method-chip">Rehabilitation Technology</span>
            <span class="method-chip">Brain and Nerve Stimulation</span>
            <span class="method-chip">Lifestyle and Daily Health</span>
            <span class="method-chip">Medical and Biological Recovery</span>
            <span class="method-chip">Family and Home Support</span>
            <span class="method-chip">Testing and Prediction</span>
            <span class="method-chip">Recovery Science</span>
            <span class="method-chip">General Rehabilitation</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.subheader("Scoring Framework")
st.markdown(
    """
    <div class="scope-note">
    Scores do not judge whether a paper is good or bad. They estimate how strongly the abstract supports
    a specific recovery approach under this app's scoring rubric. A lower score may reflect limited
    abstract detail, narrative or review format, missing safety reporting, or indirect evidence rather
    than poor research quality.
    </div>
    """,
    unsafe_allow_html=True,
)
st.write(
    "Each extracted paper receives four component scores from 0 to 100. The overall score is a "
    "weighted evidence-navigation signal, not a formal treatment-effect estimate."
)
st.markdown(
    """
    <div class="formula-box">
        <strong>Overall score =</strong><br>
        40% Neuroplasticity potential<br>
        + 35% Clinical evidence strength<br>
        + 15% Safety<br>
        + 10% Practicality
    </div>
    """,
    unsafe_allow_html=True,
)

weights = pd.DataFrame(
    [
        {
            "Component": "Neuroplasticity potential",
            "Weight": "40%",
            "Basis": "Mechanisms, intensity, repetition, feedback, motor learning, and related abstract signals.",
        },
        {
            "Component": "Clinical evidence strength",
            "Weight": "35%",
            "Basis": "Study design, human evidence level, sample size, stroke specificity, and intervention specificity.",
        },
        {
            "Component": "Safety",
            "Weight": "15%",
            "Basis": "Reported tolerability, adverse events, and category-level safety considerations.",
        },
        {
            "Component": "Practicality",
            "Weight": "10%",
            "Basis": "Feasibility based on recovery group, setting, equipment needs, and delivery context.",
        },
    ]
)
st.dataframe(
    weights,
    width="stretch",
    hide_index=True,
    column_config={
        "Component": st.column_config.TextColumn("Component", width="medium"),
        "Weight": st.column_config.TextColumn("Weight", width="small"),
        "Basis": st.column_config.TextColumn("Basis", width="large"),
    },
)

st.markdown(
    """
    <div class="methodology-card">
        <h3>Ranking Logic</h3>
        <p>Recovery subgroups are ranked by average overall score across included papers after filters are applied.</p>
        <p>The ranking combines neuroplasticity rationale, clinical evidence strength, safety, and practicality rather than paper count alone.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.subheader("Evidence Tiers")
tiers = pd.DataFrame(
    [
        {
            "Tier": "Strong clinical evidence",
            "Definition": "Higher average clinical score with multiple human studies and review or repeated RCT support.",
        },
        {
            "Tier": "Moderate clinical evidence",
            "Definition": "Moderate clinical signal with review, RCT, or several human studies.",
        },
        {
            "Tier": "Emerging evidence",
            "Definition": "Some human evidence, but not enough for moderate or strong support.",
        },
        {
            "Tier": "Conflicting evidence",
            "Definition": "Included papers contain opposing positive and negative or no-effect directions.",
        },
        {
            "Tier": "Mechanistic/preclinical only",
            "Definition": "Evidence is primarily animal or mechanistic rather than direct human clinical evidence.",
        },
        {
            "Tier": "Insufficient evidence",
            "Definition": "Evidence is too sparse, nonspecific, or weakly tied to a recovery subgroup.",
        },
    ]
)
st.dataframe(
    tiers,
    width="stretch",
    hide_index=True,
    column_config={
        "Tier": st.column_config.TextColumn("Tier", width="medium"),
        "Definition": st.column_config.TextColumn("Definition", width="large"),
    },
)
