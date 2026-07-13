"""Recovery explorer page."""

from __future__ import annotations

import html
import importlib
import json
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.db import get_connection, init_db
import src.filter_labels as filter_labels
from src.utils import normalize_missing_label

filter_labels = importlib.reload(filter_labels)
normalize_effect_direction_label = filter_labels.normalize_effect_direction_label
normalize_stroke_phase_label = filter_labels.normalize_stroke_phase_label
normalize_stroke_type_label = filter_labels.normalize_stroke_type_label
normalize_study_type_label = filter_labels.normalize_study_type_label


REVIEW_OR_BACKGROUND_TYPES = {
    "meta_analysis",
    "systematic_review",
    "narrative_review",
    "mechanistic_study",
    "diagnostic_biomarker",
    "epidemiology",
    "protocol",
}


st.set_page_config(page_title="Recovery Explorer", layout="wide")
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
    .recovery-kpi {
        padding: 0.1rem 0 0.55rem 0;
    }
    .recovery-kpi-label {
        min-height: 2.25rem;
        font-size: 0.84rem;
        font-weight: 650;
        line-height: 1.18;
        opacity: 0.72;
        white-space: normal;
        overflow-wrap: anywhere;
    }
    .recovery-kpi-value {
        margin-top: 0.35rem;
        font-size: 1.45rem;
        font-weight: 400;
        line-height: 1.15;
    }
    </style>
    """,
    unsafe_allow_html=True,
)
st.title("Recovery Explorer")


def render_kpi(column: object, label: str, value: object) -> None:
    """Render a compact KPI block with labels that can wrap."""

    column.markdown(
        f"""
        <div class="recovery-kpi">
            <div class="recovery-kpi-label">{html.escape(label)}</div>
            <div class="recovery-kpi-value">{html.escape(str(value))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data(ttl=30)
def load_data() -> dict[str, pd.DataFrame]:
    init_db()
    with get_connection() as conn:
        return {
            "summaries": pd.read_sql_query("SELECT * FROM intervention_summaries", conn),
            "studies": pd.read_sql_query(
                """
                SELECT
                    e.*, p.title, p.publication_year, p.pubmed_url,
                    s.neuroplasticity_potential, s.clinical_evidence_strength,
                    s.safety_score, s.practicality_score, s.overall_score, s.scoring_notes
                FROM study_extractions e
                JOIN papers p ON e.pmid = p.pmid
                LEFT JOIN scores s ON e.pmid = s.pmid
                    AND e.intervention_canonical = s.intervention_canonical
                """,
                conn,
            ),
        }


def parse_list(value: str | None) -> str:
    if value is None or pd.isna(value):
        return "not reported in abstract"
    if not isinstance(value, str):
        return str(value)
    try:
        parsed = json.loads(value)
        if isinstance(parsed, list):
            return "; ".join(str(normalize_missing_label(item)) for item in parsed)
    except json.JSONDecodeError:
        pass
    return str(normalize_missing_label(value))


def display_value(value: object, default: str = "unknown") -> object:
    """Display missing pandas/SQLite values as plain uncertainty text."""

    if value is None or pd.isna(value):
        return default
    normalized = normalize_missing_label(value)
    if isinstance(normalized, str) and not normalized.strip():
        return default
    return normalized


def display_text(value: object, default: str = "unknown") -> str:
    """Return a string safe for Streamlit dataframe serialization."""

    return str(display_value(value, default))


def detail_default(row: pd.Series, field: str) -> str:
    """Return the display fallback for legacy missing values in detail fields."""

    study_type = str(row.get("study_type") or "").lower()
    if field in {"dosage_intensity", "frequency", "duration"} and study_type in REVIEW_OR_BACKGROUND_TYPES:
        return "not applicable"
    if field == "comparator" and study_type in {
        "mechanistic_study",
        "diagnostic_biomarker",
        "epidemiology",
        "narrative_review",
        "protocol",
    }:
        return "not applicable"
    if field in {"adverse_events", "safety_notes"} and study_type in {
        "narrative_review",
        "mechanistic_study",
        "diagnostic_biomarker",
        "epidemiology",
    }:
        return "not applicable"
    return "not reported in abstract"


def detail_value(row: pd.Series, field: str) -> str:
    """Display a scalar detail using field-aware missing-value labels."""

    default = detail_default(row, field)
    value = display_value(row.get(field), default)
    if value == "unknown" and default != "unknown":
        return default
    return str(value)


def detail_list(row: pd.Series, field: str) -> str:
    """Display a list detail using field-aware missing-value labels."""

    value = parse_list(row.get(field))
    default = detail_default(row, field)
    if value == "unknown" and default != "unknown":
        return default
    return value or default


data = load_data()
summaries = data["summaries"]
studies = data["studies"]

if summaries.empty:
    st.info("No recovery summaries yet. Run `python main.py score` after extraction.")
    st.stop()

intervention_col = "intervention_family" if "intervention_family" in summaries.columns else "intervention_canonical"
study_intervention_col = "intervention_family" if "intervention_family" in studies.columns else "intervention_canonical"

intervention = st.selectbox(
    "Recovery subgroup",
    sorted(summaries[intervention_col].dropna().unique()),
)
summary = summaries[summaries[intervention_col] == intervention].iloc[0]
supporting = studies[studies[study_intervention_col] == intervention].copy()

st.subheader(summary[intervention_col])
tier_col, paper_col, human_col, rct_col, review_col, score_col = st.columns([1.8, 1, 1, 1, 1.4, 1.2])
tier_col.markdown("**Evidence tier**")
tier_col.markdown(
    f"<div style='display:inline-block; padding:0.35rem 0.65rem; border-radius:0.45rem; "
    f"background-color:#eef6f4; color:#173f3a; font-weight:600;'>{display_value(summary['evidence_tier'])}</div>",
    unsafe_allow_html=True,
)
render_kpi(paper_col, "Paper count", int(summary["paper_count"]))
render_kpi(human_col, "Human studies", int(summary["human_study_count"]))
render_kpi(rct_col, "RCTs", int(summary["rct_count"]))
review_total = int(summary["systematic_review_count"]) + int(summary["meta_analysis_count"])
render_kpi(review_col, "Systematic review/meta-analysis", review_total)
render_kpi(score_col, "Average overall score", round(float(summary["avg_overall_score"]), 2))

score_df = pd.DataFrame(
    {
        "component": [
            "Neuroplasticity potential",
            "Clinical evidence strength",
            "Safety",
            "Practicality",
            "Overall",
        ],
        "score": [
            summary["avg_neuroplasticity_potential"],
            summary["avg_clinical_evidence_strength"],
            summary["avg_safety_score"],
            summary["avg_practicality_score"],
            summary["avg_overall_score"],
        ],
    }
)
st.plotly_chart(px.bar(score_df, x="component", y="score", range_y=[0, 100]), width="stretch")

detail_cols = st.columns(2)
detail_cols[0].markdown("**Recovery subgroup summary**")
detail_cols[0].write(f"Recovery group: {display_value(summary['intervention_category'])}")
if "intervention_canonical" in supporting:
    canonical_names = sorted(
        {
            str(value)
            for value in supporting["intervention_canonical"].dropna().unique()
            if str(value).strip() and str(value).lower() != "unknown"
        }
    )
    detail_cols[0].write(f"Paper-level extracted labels: {'; '.join(canonical_names) or 'unknown'}")
detail_cols[0].write(f"Common outcome measures: {display_value(summary['common_outcome_measures'])}")
detail_cols[0].write(f"Reported protocols: {display_value(summary['treatment_protocols'])}")
detail_cols[1].markdown("**Uncertainty and safety**")
detail_cols[1].write(f"Key limitations: {display_value(summary['key_limitations'])}")
detail_cols[1].write(f"Safety summary: {display_value(summary['safety_summary'])}")

if supporting.empty:
    st.info("No supporting studies found for this recovery subgroup.")
    st.stop()

supporting["outcome_measures"] = supporting["outcome_measures"].map(parse_list)
supporting["PubMed URL"] = supporting["pubmed_url"]
table = supporting.rename(
    columns={
        "pmid": "PMID",
        "publication_year": "year",
        "study_type": "study type",
        "sample_size": "sample size",
        "stroke_type": "stroke type",
        "stroke_phase": "phase",
        "effect_direction": "effect direction",
    }
)
display_columns = {
    "PMID": "unknown",
    "title": "unknown",
    "year": "unknown",
    "study type": "unknown",
    "sample size": "not reported in abstract",
    "stroke type": "unknown",
    "phase": "unknown",
    "outcome_measures": "unknown",
    "effect direction": "unknown",
    "PubMed URL": "",
}
if "stroke type" in table:
    table["stroke type"] = table["stroke type"].apply(normalize_stroke_type_label)
if "phase" in table:
    table["phase"] = table["phase"].apply(normalize_stroke_phase_label)
if "effect direction" in table:
    table["effect direction"] = table["effect direction"].apply(normalize_effect_direction_label)
if "study type" in table:
    table["study type"] = table["study type"].apply(normalize_study_type_label)
for column, default in display_columns.items():
    if column in table:
        table[column] = table[column].apply(lambda value, fallback=default: display_text(value, fallback))
st.subheader("Supporting studies")
st.dataframe(
    table[
        [
            "PMID",
            "title",
            "year",
            "study type",
            "sample size",
            "stroke type",
            "phase",
            "outcome_measures",
            "effect direction",
            "PubMed URL",
        ]
    ],
    width="stretch",
    hide_index=True,
    column_config={"PubMed URL": st.column_config.LinkColumn("PubMed URL")},
)

with st.expander("Study protocol, outcomes, limitations, safety, and applicability details"):
    for _, row in supporting.iterrows():
        st.markdown(f"**{row['pmid']} - {row['title']}**")
        st.write(f"Dosage/intensity: {detail_value(row, 'dosage_intensity')}")
        st.write(f"Frequency: {detail_value(row, 'frequency')}")
        st.write(f"Duration: {detail_value(row, 'duration')}")
        st.write(f"Outcomes: {detail_list(row, 'outcomes')}")
        st.write(f"Limitations: {detail_list(row, 'limitations')}")
        st.write(f"Adverse events: {detail_value(row, 'adverse_events')}")
        st.write(f"Safety notes: {detail_value(row, 'safety_notes')}")
        st.write(f"Applicability notes: {detail_value(row, 'applicability_notes')}")
        st.divider()
