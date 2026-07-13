"""Overview dashboard page."""

from __future__ import annotations

import html
import importlib
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
import src.filter_labels as filter_labels

filter_labels = importlib.reload(filter_labels)
STROKE_PHASE_FILTER_OPTIONS = filter_labels.STROKE_PHASE_FILTER_OPTIONS
STROKE_TYPE_FILTER_OPTIONS = filter_labels.STROKE_TYPE_FILTER_OPTIONS
study_type_filter_options = filter_labels.study_type_filter_options
study_type_matches_filter = filter_labels.study_type_matches_filter
stroke_phase_matches_filter = filter_labels.stroke_phase_matches_filter
stroke_type_matches_filter = filter_labels.stroke_type_matches_filter


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
    .overview-kpi {
        padding: 0.1rem 0 0.55rem 0;
    }
    .overview-kpi-label {
        min-height: 2.25rem;
        font-size: 0.84rem;
        font-weight: 650;
        line-height: 1.18;
        opacity: 0.72;
        white-space: normal;
        overflow-wrap: anywhere;
    }
    .overview-kpi-value {
        margin-top: 0.35rem;
        font-size: 1.45rem;
        font-weight: 400;
        line-height: 1.15;
    }
    </style>
    """,
    unsafe_allow_html=True,
)
st.title("Overview Dashboard")


def render_kpi(column: object, label: str, value: int) -> None:
    """Render a compact KPI block with labels that can wrap."""

    column.markdown(
        f"""
        <div class="overview-kpi">
            <div class="overview-kpi-label">{html.escape(label)}</div>
            <div class="overview-kpi-value">{html.escape(str(value))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


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
render_kpi(kpi_cols[0], "Total papers collected", total_papers)
render_kpi(kpi_cols[1], "Papers extracted", papers_extracted)
render_kpi(kpi_cols[2], "Recovery subgroups identified", interventions)
render_kpi(kpi_cols[3], "Randomized trials", rct_count)
render_kpi(kpi_cols[4], "Systematic review/meta-analysis count", review_count)

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
        study_types = study_type_filter_options(extractions["study_type"].dropna().unique())
        selected_stroke = st.multiselect("Stroke type", STROKE_TYPE_FILTER_OPTIONS)
        selected_study = st.multiselect("Study type", study_types)
        selected_phase = st.multiselect("Stroke phase", STROKE_PHASE_FILTER_OPTIONS)
        if selected_stroke:
            filtered_extractions = filtered_extractions[
                filtered_extractions["stroke_type"].apply(
                    lambda value: stroke_type_matches_filter(value, selected_stroke)
                )
            ]
        if selected_study:
            filtered_extractions = filtered_extractions[
                filtered_extractions["study_type"].apply(
                    lambda value: study_type_matches_filter(value, selected_study)
                )
            ]
        if selected_phase:
            filtered_extractions = filtered_extractions[
                filtered_extractions["stroke_phase"].apply(
                    lambda value: stroke_phase_matches_filter(value, selected_phase)
                )
            ]
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
st.subheader("Ranked Recovery Subgroups")
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
top_chart = ranked.head(10).sort_values("avg_overall_score")
chart_cols[0].plotly_chart(
    px.bar(
        top_chart,
        x="avg_overall_score",
        y=intervention_col,
        orientation="h",
        title="Top Recovery Subgroups",
        labels={"avg_overall_score": "Average overall score", intervention_col: "Recovery subgroup"},
    ),
    width="stretch",
)
group_counts = (
    ranked.groupby("intervention_category")
    .size()
    .reset_index(name="subgroup_count")
    .sort_values("subgroup_count")
)
chart_cols[1].plotly_chart(
    px.bar(
        group_counts,
        x="subgroup_count",
        y="intervention_category",
        orientation="h",
        title="Recovery Subgroups by Group",
        labels={"subgroup_count": "Subgroup count", "intervention_category": "Recovery group"},
    ),
    width="stretch",
)
evidence_tier_counts = (
    ranked.groupby("evidence_tier")
    .size()
    .reset_index(name="subgroup_count")
)
chart_cols[2].plotly_chart(
    px.bar(
        evidence_tier_counts,
        x="evidence_tier",
        y="subgroup_count",
        title="Recovery Subgroups by Evidence Tier",
        labels={"evidence_tier": "Evidence tier", "subgroup_count": "Subgroup count"},
    ),
    width="stretch",
)
