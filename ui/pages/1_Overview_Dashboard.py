"""Overview dashboard page."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.db import get_connection, init_db
from src.normalization import RECOVERY_GROUPS


st.set_page_config(page_title="Overview Dashboard", layout="wide")
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
st.title("Overview Dashboard")


@st.cache_data(ttl=30)
def load_data() -> dict[str, pd.DataFrame]:
    init_db()
    with get_connection() as conn:
        return {
            "papers": pd.read_sql_query("SELECT * FROM papers", conn),
            "extractions": pd.read_sql_query("SELECT * FROM study_extractions", conn),
            "scores": pd.read_sql_query("SELECT * FROM scores", conn),
            "summaries": pd.read_sql_query("SELECT * FROM intervention_summaries", conn),
        }


data = load_data()
papers = data["papers"]
extractions = data["extractions"]
summaries = data["summaries"]

if papers.empty and summaries.empty:
    st.info("No data yet. Run the pipeline commands from the README to populate the atlas.")
    st.stop()

total_papers = len(papers)
papers_extracted = int(extractions["pmid"].nunique()) if not extractions.empty else 0
intervention_col = "intervention_family" if "intervention_family" in summaries.columns else "intervention_canonical"
extraction_intervention_col = (
    "intervention_family" if "intervention_family" in extractions.columns else "intervention_canonical"
)
interventions = int(summaries[intervention_col].nunique()) if not summaries.empty else 0
rct_count = int((extractions["study_type"] == "randomized_controlled_trial").sum()) if not extractions.empty else 0
review_count = (
    int(extractions["study_type"].isin(["systematic_review", "meta_analysis"]).sum())
    if not extractions.empty
    else 0
)

kpi_cols = st.columns(5)
kpi_cols[0].metric("Total papers collected", total_papers)
kpi_cols[1].metric("Papers extracted", papers_extracted)
kpi_cols[2].metric("Recovery subgroups identified", interventions)
kpi_cols[3].metric("RCT count", rct_count)
kpi_cols[4].metric("Systematic review/meta-analysis count", review_count)

filtered_summaries = summaries.copy()
filtered_extractions = extractions.copy()

with st.sidebar:
    st.header("Filters")
    if not summaries.empty:
        category_order = {category: index for index, category in enumerate(RECOVERY_GROUPS)}
        categories = sorted(
            summaries["intervention_category"].dropna().unique(),
            key=lambda value: (category_order.get(str(value), len(category_order)), str(value)),
        )
        selected_categories = st.multiselect("Recovery group", categories)
        tiers = sorted(summaries["evidence_tier"].dropna().unique())
        selected_tiers = st.multiselect("Evidence tier", tiers)
        if selected_categories:
            filtered_summaries = filtered_summaries[filtered_summaries["intervention_category"].isin(selected_categories)]
        if selected_tiers:
            filtered_summaries = filtered_summaries[filtered_summaries["evidence_tier"].isin(selected_tiers)]
    if not extractions.empty:
        stroke_types = sorted(extractions["stroke_type"].dropna().unique())
        study_types = sorted(extractions["study_type"].dropna().unique())
        phases = sorted(extractions["stroke_phase"].dropna().unique())
        selected_stroke = st.multiselect("Stroke type", stroke_types)
        selected_study = st.multiselect("Study type", study_types)
        selected_phase = st.multiselect("Stroke phase", phases)
        if selected_stroke:
            filtered_extractions = filtered_extractions[filtered_extractions["stroke_type"].isin(selected_stroke)]
        if selected_study:
            filtered_extractions = filtered_extractions[filtered_extractions["study_type"].isin(selected_study)]
        if selected_phase:
            filtered_extractions = filtered_extractions[filtered_extractions["stroke_phase"].isin(selected_phase)]
        if selected_stroke or selected_study or selected_phase:
            allowed = set(filtered_extractions[extraction_intervention_col])
            filtered_summaries = filtered_summaries[filtered_summaries[intervention_col].isin(allowed)]

if filtered_summaries.empty:
    st.info("No recovery summaries match the selected filters.")
    st.stop()

ranked = filtered_summaries.sort_values("avg_overall_score", ascending=False)
display = ranked.rename(
    columns={
        intervention_col: "recovery subgroup",
        "intervention_category": "recovery group",
        "avg_overall_score": "average overall score",
        "avg_neuroplasticity_potential": "neuroplasticity potential",
        "avg_clinical_evidence_strength": "clinical evidence strength",
        "avg_safety_score": "safety",
        "avg_practicality_score": "practicality",
    }
)
st.subheader("Ranked recovery subgroups")
st.dataframe(
    display[
        [
            "recovery subgroup",
            "recovery group",
            "evidence_tier",
            "paper_count",
            "average overall score",
            "neuroplasticity potential",
            "clinical evidence strength",
            "safety",
            "practicality",
        ]
    ],
    width="stretch",
    hide_index=True,
)

chart_cols = st.columns(3)
top_chart = ranked.head(20).sort_values("avg_overall_score")
chart_cols[0].plotly_chart(
    px.bar(
        top_chart,
        x="avg_overall_score",
        y=intervention_col,
        orientation="h",
        labels={"avg_overall_score": "Overall score", intervention_col: "Recovery subgroup"},
    ),
    width="stretch",
)
chart_cols[1].plotly_chart(
    px.histogram(
        ranked,
        x="intervention_category",
        title="Recovery group distribution",
        labels={"intervention_category": "Recovery group"},
    ),
    width="stretch",
)
chart_cols[2].plotly_chart(
    px.histogram(ranked, x="evidence_tier", title="Evidence tier distribution"),
    width="stretch",
)
