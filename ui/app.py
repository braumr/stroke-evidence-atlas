"""Stroke Evidence Atlas Streamlit entrypoint."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import DB_PATH


st.set_page_config(page_title="Stroke Evidence Atlas", layout="wide")
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
    </style>
    """,
    unsafe_allow_html=True,
)

ASSET_DIR = ROOT / "ui" / "assets"
BRAIN_IMAGE = ASSET_DIR / "neuroplasticity_brain.png"


hero_text, hero_image = st.columns([0.95, 1.35], vertical_alignment="center")
with hero_text:
    st.title("Stroke Recovery Atlas")
    st.write(
        "Explore aggregated research evidence across stroke recovery, rehabilitation, and neuroplasticity."
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
            <h3>Browse Recovery Areas</h3>
            <p>Explore recovery groups and subgroups created from AI-assisted extraction of PubMed research across areas such as physical rehabilitation, cognition, communication, technology, nerve/brain stimulation, lifestyle, biology, family support, and recovery science.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with scoring_col:
    st.markdown(
        """
        <div class="home-summary">
            <h3>Compare Evidence Signals</h3>
            <p>Sort recovery subgroups by overall evidence signal, neuroplasticity rationale, clinical evidence, safety, and practicality.</p>
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
