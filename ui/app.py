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
    </style>
    """,
    unsafe_allow_html=True,
)

ASSET_DIR = ROOT / "ui" / "assets"
BRAIN_IMAGE = ASSET_DIR / "neuroplasticity_brain.jpg"


hero_text, hero_image = st.columns([0.95, 1.35], vertical_alignment="center")
with hero_text:
    st.title("Stroke Evidence Atlas")
    st.write(
        "A local evidence atlas for exploring PubMed literature on stroke rehabilitation, "
        "brain injury recovery, and neuroplasticity."
    )
    if DB_PATH.exists():
        st.caption(f"Database: {DB_PATH}")
    else:
        st.info("No database found yet. Run `python main.py init-db` and then collect/extract/score data.")

with hero_image:
    if BRAIN_IMAGE.exists():
        st.image(str(BRAIN_IMAGE), width="stretch")

st.divider()

overview_col, scoring_col = st.columns(2)

with overview_col:
    st.subheader("What It Does")
    st.write(
        "Collects PubMed papers, extracts structured study details from abstracts, "
        "normalizes interventions into broader families, and stores everything locally in SQLite."
    )

with scoring_col:
    st.subheader("Scoring Method")
    st.write(
        "Overall score = 0.40 neuroplasticity potential + 0.35 clinical evidence strength "
        "+ 0.15 safety + 0.10 practicality. Intervention-family summaries average paper-level scores."
    )

st.caption(
    "Higher scores mean stronger signals in the collected abstracts, not a final ranking of what treatment is best."
)
