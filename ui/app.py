"""Stroke Recovery Research Platform Streamlit entrypoint."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import DB_PATH


st.set_page_config(page_title="Stroke Recovery Research Platform", layout="wide")
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
    .home-summary h3 {
        font-size: 1.08rem;
        font-weight: 700;
        line-height: 1.25;
        margin-bottom: 0.45rem;
    }
    .home-summary p {
        font-size: 0.94rem;
        line-height: 1.55;
        color: inherit;
        opacity: 0.72;
        margin-bottom: 0;
    }
    .home-why {
        max-width: 980px;
        margin-top: 2.2rem;
    }
    .home-why h2 {
        font-size: 1.35rem;
        font-weight: 700;
        line-height: 1.25;
        margin-bottom: 0.7rem;
    }
    .home-why p {
        font-size: 0.98rem;
        line-height: 1.65;
        color: inherit;
        opacity: 0.76;
        margin-bottom: 0.75rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

ASSET_DIR = ROOT / "ui" / "assets"
BRAIN_IMAGE = ASSET_DIR / "neuroplasticity_brain.png"


hero_text, hero_image = st.columns([0.95, 1.35], vertical_alignment="center")
with hero_text:
    st.title("Stroke Recovery Research Platform")
    st.write(
        "Discover and compare aggregated research evidence across stroke recovery, rehabilitation, and neuroplasticity."
    )
    if not DB_PATH.exists():
        st.info("No database found yet. Run `python main.py init-db` and then collect/extract/score data.")

with hero_image:
    if BRAIN_IMAGE.exists():
        st.image(str(BRAIN_IMAGE), width=680)

st.divider()

overview_col, scoring_col, audit_col = st.columns(3)

with overview_col:
    st.markdown(
        """
        <div class="home-summary">
            <h3>Browse Recovery Domains</h3>
            <p>Explore recovery domains and research topics created from AI-assisted extraction of PubMed paper abstracts and titles, including physical rehabilitation, cognition, communication, technology, nerve/brain stimulation, lifestyle, biology, family support, and recovery science.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with scoring_col:
    st.markdown(
        """
        <div class="home-summary">
            <h3>Compare Evidence Signals</h3>
            <p>Sort research topics by overall evidence signal, neuroplasticity rationale, clinical evidence, safety, and practicality.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.divider()

st.markdown(
    """
    <div class="home-why">
        <h2>Why Stroke Recovery Research Platform Exists</h2>
        <p>Stroke recovery research spans rehabilitation medicine, neuroscience, technology, and clinical care. Yet the evidence remains scattered, making it difficult to discover recovery domains or compare recovery approaches.</p>
        <p>Stroke Recovery Research Platform brings this literature into one structured, searchable platform so users can explore recovery domains, compare evidence signals, and trace findings back to PubMed-indexed sources.</p>
        <p>The goal is not to replace clinical judgment. Instead, Stroke Recovery Research Platform helps caregivers, researchers, clinicians, students, and others interested in stroke recovery navigate the research landscape more efficiently and transparently.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

with audit_col:
    st.markdown(
        """
        <div class="home-summary">
            <h3>Audit the Sources</h3>
            <p>Review abstracts, extracted study details, supporting sentences, and direct PubMed links before interpreting results.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
