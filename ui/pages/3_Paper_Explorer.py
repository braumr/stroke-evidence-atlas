"""Paper explorer and audit page."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.db import get_connection, init_db
from src.utils import normalize_missing_label


st.set_page_config(page_title="Paper Explorer", layout="wide")
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
st.title("Paper Explorer")


@st.cache_data(ttl=30)
def load_data() -> pd.DataFrame:
    init_db()
    with get_connection() as conn:
        return pd.read_sql_query(
            """
            SELECT
                p.pmid, p.title, p.abstract, p.abstract_conclusion_text,
                p.journal, p.publication_year, p.pubmed_url,
                COALESCE(es.status, 'pending') AS extraction_status,
                es.attempts, es.last_error, es.extracted_at,
                e.study_type, e.intervention_canonical, e.intervention_family, e.intervention_raw,
                e.intervention_category, e.condition_category, e.stroke_type,
                e.sample_size, e.stroke_phase, e.time_since_stroke,
                e.dosage_intensity, e.frequency, e.duration, e.comparator,
                e.setting, e.outcome_measures, e.outcomes, e.results_summary, e.conclusion_text,
                e.effect_direction, e.limitations, e.adverse_events,
                e.safety_notes, e.applicability_notes, e.mechanistic_rationale,
                e.neuroplasticity_mechanisms, e.confidence_notes,
                e.provenance_json,
                s.neuroplasticity_potential, s.clinical_evidence_strength,
                s.safety_score, s.practicality_score, s.overall_score,
                s.study_quality_tier, s.scoring_notes
            FROM papers p
            LEFT JOIN extraction_status es ON p.pmid = es.pmid
            LEFT JOIN study_extractions e ON p.pmid = e.pmid
            LEFT JOIN scores s ON e.pmid = s.pmid
                AND e.intervention_canonical = s.intervention_canonical
            """,
            conn,
        )


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


def is_missing(value: object) -> bool:
    """Return whether a pandas/SQLite value should be treated as missing."""

    if value is None:
        return True
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def display_value(value: object, default: str = "unknown") -> object:
    """Display missing values as explicit uncertainty instead of NaN."""

    if is_missing(value):
        return default
    normalized = normalize_missing_label(value)
    if isinstance(normalized, str) and not normalized.strip():
        return default
    return normalized


def display_text(value: object, default: str = "unknown") -> str:
    """Return a string safe for Streamlit dataframe serialization."""

    return str(display_value(value, default))


def display_score(value: object) -> object:
    """Display score values only when scoring exists."""

    if is_missing(value):
        return "not scored"
    return value


def clean_table(df: pd.DataFrame) -> pd.DataFrame:
    """Replace missing display values in the paper table."""

    cleaned = df.copy()
    display_defaults = {
        "PMID": "unknown",
        "title": "unknown",
        "journal": "unknown",
        "year": "unknown",
        "study type": "not extracted",
        "intervention family": "not extracted",
        "intervention_canonical": "not extracted",
        "sample size": "not reported in abstract",
        "effect direction": "not extracted",
        "extraction_status": "pending",
        "PubMed URL": "",
    }
    for column, default in display_defaults.items():
        if column in cleaned:
            cleaned[column] = cleaned[column].apply(lambda value, fallback=default: display_text(value, fallback))
    return cleaned


df = load_data()
if df.empty:
    st.info("No papers found. Run `python main.py collect --max-papers 25` to start.")
    st.stop()

filtered = df.copy()
with st.sidebar:
    st.header("Search and filters")
    keyword = st.text_input("Keyword search")
    years = sorted([int(year) for year in filtered["publication_year"].dropna().unique()])
    selected_years = st.multiselect("Year", years)
    study_types = sorted(filtered["study_type"].dropna().unique())
    intervention_filter_col = "intervention_family" if "intervention_family" in filtered.columns else "intervention_canonical"
    interventions = sorted(filtered[intervention_filter_col].dropna().unique())
    stroke_types = sorted(filtered["stroke_type"].dropna().unique())
    phases = sorted(filtered["stroke_phase"].dropna().unique())
    effects = sorted(filtered["effect_direction"].dropna().unique())
    statuses = sorted(filtered["extraction_status"].dropna().unique())
    selected_study = st.multiselect("Study type", study_types)
    selected_intervention = st.multiselect("Intervention family", interventions)
    selected_stroke = st.multiselect("Stroke type", stroke_types)
    selected_phase = st.multiselect("Phase", phases)
    selected_effect = st.multiselect("Effect direction", effects)
    selected_status = st.multiselect("Extraction status", statuses)

if keyword:
    keyword_lower = keyword.lower()
    filtered = filtered[
        filtered["title"].fillna("").str.lower().str.contains(keyword_lower)
        | filtered["abstract"].fillna("").str.lower().str.contains(keyword_lower)
        | filtered["journal"].fillna("").str.lower().str.contains(keyword_lower)
    ]
if selected_years:
    filtered = filtered[filtered["publication_year"].isin(selected_years)]
if selected_study:
    filtered = filtered[filtered["study_type"].isin(selected_study)]
if selected_intervention:
    filtered = filtered[filtered[intervention_filter_col].isin(selected_intervention)]
if selected_stroke:
    filtered = filtered[filtered["stroke_type"].isin(selected_stroke)]
if selected_phase:
    filtered = filtered[filtered["stroke_phase"].isin(selected_phase)]
if selected_effect:
    filtered = filtered[filtered["effect_direction"].isin(selected_effect)]
if selected_status:
    filtered = filtered[filtered["extraction_status"].isin(selected_status)]

st.caption(f"{len(filtered)} papers match the current filters.")
table = filtered.copy()
table["PubMed URL"] = table["pubmed_url"]
table = table.rename(
    columns={
        "pmid": "PMID",
        "publication_year": "year",
        "study_type": "study type",
        "intervention_family": "intervention family",
        "intervention_canonical": "intervention_canonical",
        "sample_size": "sample size",
        "effect_direction": "effect direction",
    }
)
table = clean_table(table)
st.dataframe(
    table[
        [
            "PMID",
            "title",
            "journal",
            "year",
            "extraction_status",
            "study type",
            "intervention family",
            "intervention_canonical",
            "sample size",
            "effect direction",
            "PubMed URL",
        ]
    ],
    width="stretch",
    hide_index=True,
    column_config={"PubMed URL": st.column_config.LinkColumn("PubMed URL")},
)

st.subheader("Paper details")
for _, row in filtered.head(50).iterrows():
    with st.expander(f"{row['pmid']} - {row['title']}"):
        st.markdown(f"[Open in PubMed]({row['pubmed_url']})")
        status = display_value(row.get("extraction_status"), "pending")
        st.write(f"Extraction status: {status}")
        st.markdown("**Abstract**")
        st.write(row["abstract"] or "No abstract stored.")
        conclusion = display_value(
            row.get("abstract_conclusion_text"),
            display_value(row.get("conclusion_text"), "not reported in abstract"),
        )
        st.markdown("**Conclusion from abstract**")
        st.write(conclusion)
        if status != "extracted":
            if status == "failed":
                st.error(f"Extraction failed after {display_value(row.get('attempts'), 0)} attempts.")
                if not is_missing(row.get("last_error")):
                    st.code(str(row.get("last_error")))
            else:
                st.info("This paper has been collected but not extracted yet, so structured fields and scores are not available.")
            continue
        st.markdown("**Extracted structured fields**")
        st.json(
            {
                "study_type": display_value(row.get("study_type")),
                "intervention_raw": display_value(row.get("intervention_raw")),
                "intervention_family": display_value(row.get("intervention_family")),
                "intervention_canonical": display_value(row.get("intervention_canonical")),
                "intervention_category": display_value(row.get("intervention_category")),
                "condition_category": display_value(row.get("condition_category")),
                "stroke_type": display_value(row.get("stroke_type")),
                "sample_size": display_value(row.get("sample_size"), "not reported in abstract"),
                "stroke_phase": display_value(row.get("stroke_phase")),
                "time_since_stroke": display_value(row.get("time_since_stroke")),
                "dosage_intensity": display_value(row.get("dosage_intensity")),
                "frequency": display_value(row.get("frequency")),
                "duration": display_value(row.get("duration")),
                "comparator": display_value(row.get("comparator")),
                "setting": display_value(row.get("setting")),
                "outcome_measures": parse_list(row.get("outcome_measures")),
                "outcomes": parse_list(row.get("outcomes")),
                "results_summary": display_value(row.get("results_summary")),
                "conclusion_text": display_value(row.get("conclusion_text"), "not reported in abstract"),
                "effect_direction": display_value(row.get("effect_direction")),
                "mechanistic_rationale": display_value(row.get("mechanistic_rationale")),
                "neuroplasticity_mechanisms": parse_list(row.get("neuroplasticity_mechanisms")),
                "confidence_notes": display_value(row.get("confidence_notes")),
            }
        )
        st.markdown("**Provenance/supporting sentences**")
        try:
            st.json(json.loads(row["provenance_json"]) if not is_missing(row["provenance_json"]) else {})
        except (TypeError, json.JSONDecodeError):
            st.write(display_value(row.get("provenance_json"), "No provenance stored."))
        st.markdown("**Scores**")
        st.json(
            {
                "neuroplasticity_potential": display_score(row.get("neuroplasticity_potential")),
                "clinical_evidence_strength": display_score(row.get("clinical_evidence_strength")),
                "safety_score": display_score(row.get("safety_score")),
                "practicality_score": display_score(row.get("practicality_score")),
                "overall_score": display_score(row.get("overall_score")),
                "study_quality_tier": display_score(row.get("study_quality_tier")),
            }
        )
        st.markdown("**Limitations and safety**")
        st.write(f"Limitations: {parse_list(row.get('limitations')) or 'unknown'}")
        st.write(f"Adverse events: {display_value(row.get('adverse_events'))}")
        st.write(f"Safety notes: {display_value(row.get('safety_notes'))}")
