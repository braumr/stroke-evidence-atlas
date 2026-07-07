"""LLM abstract extraction with validation and resumable checkpointing."""

from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError
from tqdm import tqdm

from .db import get_connection, init_db
from .llm_client import LLMClient
from .normalization import intervention_family, normalize_intervention
from .utils import clean_text, parse_int, setup_logging, utc_now

LOGGER = setup_logging(__name__)


StudyType = Literal[
    "meta_analysis",
    "systematic_review",
    "randomized_controlled_trial",
    "cohort_study",
    "case_control_study",
    "case_series",
    "case_report",
    "animal_study",
    "mechanistic_study",
    "feasibility_study",
    "pilot_study",
    "narrative_review",
    "protocol",
    "diagnostic_biomarker",
    "epidemiology",
    "qualitative",
    "mixed_methods",
    "unknown",
]


class ProvenanceField(BaseModel):
    value: Any = None
    supporting_sentence: str = "unknown"


class Provenance(BaseModel):
    sample_size: ProvenanceField = Field(default_factory=ProvenanceField)
    intervention: ProvenanceField = Field(default_factory=ProvenanceField)
    outcome_measures: ProvenanceField = Field(default_factory=ProvenanceField)
    results: ProvenanceField = Field(default_factory=ProvenanceField)
    adverse_events: ProvenanceField = Field(default_factory=ProvenanceField)


class ExtractionResult(BaseModel):
    study_type: StudyType = "unknown"
    intervention: str = "unknown"
    intervention_category: str = "unknown"
    condition_category: str = "unknown"
    stroke_type: str = "unknown"
    participant_characteristics: str = "unknown"
    sample_size: int | None = None
    time_since_stroke: str = "unknown"
    stroke_phase: str = "unknown"
    dosage_intensity: str = "unknown"
    frequency: str = "unknown"
    duration: str = "unknown"
    comparator: str = "unknown"
    setting: str = "unknown"
    outcome_measures: list[str] = Field(default_factory=list)
    outcomes: list[str] = Field(default_factory=list)
    results_summary: str = "unknown"
    effect_direction: str = "unclear"
    limitations: list[str] = Field(default_factory=list)
    adverse_events: str = "unknown"
    safety_notes: str = "unknown"
    applicability_notes: str = "unknown"
    mechanistic_rationale: str = "unknown"
    neuroplasticity_mechanisms: list[str] = Field(default_factory=list)
    confidence_notes: str = "unknown"
    provenance: Provenance = Field(default_factory=Provenance)


SYSTEM_PROMPT = """You extract structured stroke rehabilitation evidence from PubMed abstracts.
Return strict JSON only. Do not include Markdown.
Use only the title and abstract supplied by the user.
Do not fabricate citations, PMIDs, sample sizes, intervention details, adverse events, or results.
If a detail is not stated, use "unknown", null, or an empty list as appropriate.
Do not force diagnostic, epidemiology, biomarker, protocol, animal, or mechanistic papers into clinical rehabilitation evidence.
Animal and mechanistic evidence must not be treated as human clinical proof."""


EXTRACTION_PROMPT = """Extract JSON matching this schema exactly:
{
  "study_type": "meta_analysis | systematic_review | randomized_controlled_trial | cohort_study | case_control_study | case_series | case_report | animal_study | mechanistic_study | feasibility_study | pilot_study | narrative_review | protocol | diagnostic_biomarker | epidemiology | qualitative | mixed_methods | unknown",
  "intervention": "specific intervention name or unknown",
  "intervention_category": "motor_rehab | speech_language | cognitive_rehab | neuromodulation | robotics | virtual_reality | electrical_stimulation | exercise | mind_body | nutrition_sleep_systemic | caregiver_home | pharmacologic | diagnostic_biomarker | other | unknown",
  "condition_category": "ischemic_stroke | hemorrhagic_stroke | intracerebral_hemorrhage | subarachnoid_hemorrhage | traumatic_brain_injury | acquired_brain_injury | mixed_stroke | mixed_neurological | healthy_controls | not_applicable | unknown",
  "stroke_type": "ischemic | hemorrhagic | intracerebral_hemorrhage | subarachnoid_hemorrhage | mixed | not_stroke | unknown",
  "participant_characteristics": "age, severity, impairment type, inclusion details if available",
  "sample_size": null,
  "time_since_stroke": "acute/subacute/chronic timing or exact timing if available",
  "stroke_phase": "acute | subacute | chronic | mixed | unknown",
  "dosage_intensity": "dose or intensity if stated",
  "frequency": "frequency if stated",
  "duration": "intervention duration if stated",
  "comparator": "usual care | sham | active control | waitlist | none | unknown",
  "setting": "inpatient | outpatient | home | community | laboratory | mixed | unknown",
  "outcome_measures": [],
  "outcomes": [],
  "results_summary": "concise summary of reported results",
  "effect_direction": "positive | negative | mixed | no_effect | unclear",
  "limitations": [],
  "adverse_events": "reported adverse events or unknown",
  "safety_notes": "safety concerns, contraindications, tolerability, or unknown",
  "applicability_notes": "which patients/settings this evidence may apply to, based only on abstract",
  "mechanistic_rationale": "rehabilitation/neuroplasticity rationale stated or implied by abstract; use unknown if not present",
  "neuroplasticity_mechanisms": [],
  "confidence_notes": "brief explanation of extraction confidence",
  "provenance": {
    "sample_size": {"value": null, "supporting_sentence": "exact sentence or unknown"},
    "intervention": {"value": "string", "supporting_sentence": "exact sentence or unknown"},
    "outcome_measures": {"value": [], "supporting_sentence": "exact sentence or unknown"},
    "results": {"value": "string", "supporting_sentence": "exact sentence or unknown"},
    "adverse_events": {"value": "string", "supporting_sentence": "exact sentence or unknown"}
  }
}
"""


def _model_validate_json(raw_json: str) -> ExtractionResult:
    if hasattr(ExtractionResult, "model_validate_json"):
        return ExtractionResult.model_validate_json(raw_json)  # type: ignore[attr-defined]
    return ExtractionResult.parse_raw(raw_json)


def validate_extraction(raw_json: str) -> tuple[ExtractionResult, str]:
    """Validate and normalize LLM JSON."""

    parsed = _model_validate_json(raw_json)
    raw_dict = json.loads(raw_json)
    parsed.sample_size = parse_int(parsed.sample_size)
    return parsed, json.dumps(raw_dict, ensure_ascii=False)


def _repair_prompt(raw_response: str, error: str) -> str:
    return f"""The previous response failed JSON/schema validation.
Validation error:
{error}

Return repaired strict JSON only. Preserve only details supported by the title and abstract.

Invalid response:
{raw_response}
"""


def _serialize_list(values: list[str]) -> str:
    return json.dumps(values or [], ensure_ascii=False)


def build_extraction_prompt(title: str, abstract: str) -> str:
    """Build the user prompt without templating the JSON schema braces."""

    return f"{EXTRACTION_PROMPT}\n\nTitle: {title or 'unknown'}\nAbstract: {abstract}"


def _save_extraction(pmid: str, extraction: ExtractionResult, raw_json: str, force: bool = False) -> None:
    canonical = normalize_intervention(extraction.intervention)
    family = intervention_family(extraction.intervention, canonical, extraction.intervention_category)
    now = utc_now()
    with get_connection() as conn:
        if force:
            conn.execute("DELETE FROM study_extractions WHERE pmid = ?", (pmid,))
        conn.execute(
            """
            INSERT INTO study_extractions (
                pmid, study_type, intervention_raw, intervention_canonical,
                intervention_family, intervention_category, condition_category, stroke_type,
                participant_characteristics, sample_size, time_since_stroke,
                stroke_phase, dosage_intensity, frequency, duration, comparator,
                setting, outcome_measures, outcomes, results_summary,
                effect_direction, limitations, adverse_events, safety_notes,
                applicability_notes, mechanistic_rationale, neuroplasticity_mechanisms,
                confidence_notes, provenance_json, raw_llm_json, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                pmid,
                extraction.study_type,
                clean_text(extraction.intervention),
                canonical,
                family,
                extraction.intervention_category,
                extraction.condition_category,
                extraction.stroke_type,
                extraction.participant_characteristics,
                extraction.sample_size,
                extraction.time_since_stroke,
                extraction.stroke_phase,
                extraction.dosage_intensity,
                extraction.frequency,
                extraction.duration,
                extraction.comparator,
                extraction.setting,
                _serialize_list(extraction.outcome_measures),
                _serialize_list(extraction.outcomes),
                extraction.results_summary,
                extraction.effect_direction,
                _serialize_list(extraction.limitations),
                extraction.adverse_events,
                extraction.safety_notes,
                extraction.applicability_notes,
                extraction.mechanistic_rationale,
                _serialize_list(extraction.neuroplasticity_mechanisms),
                extraction.confidence_notes,
                extraction.provenance.model_dump_json()
                if hasattr(extraction.provenance, "model_dump_json")
                else extraction.provenance.json(),
                raw_json,
                now,
            ),
        )
        conn.execute(
            """
            UPDATE extraction_status
            SET status = 'extracted', extracted_at = ?, updated_at = ?, last_error = NULL
            WHERE pmid = ?
            """,
            (now, now, pmid),
        )


def _mark_skipped(pmid: str) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE extraction_status
            SET status = 'skipped_no_abstract', updated_at = ?
            WHERE pmid = ?
            """,
            (utc_now(), pmid),
        )


def _mark_failed(pmid: str, error: str) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE extraction_status
            SET status = 'failed', attempts = COALESCE(attempts, 0) + 1, last_error = ?, updated_at = ?
            WHERE pmid = ?
            """,
            (error[:2000], utc_now(), pmid),
        )


def get_papers_for_extraction(limit: int | None = None, force: bool = False) -> list[dict[str, Any]]:
    """Return papers that need extraction."""

    where = "1 = 1" if force else "COALESCE(es.status, 'pending') != 'extracted'"
    sql = f"""
        SELECT p.pmid, p.title, p.abstract, COALESCE(es.status, 'pending') AS status
        FROM papers p
        LEFT JOIN extraction_status es ON p.pmid = es.pmid
        WHERE {where}
        ORDER BY p.publication_year DESC, p.pmid DESC
    """
    params: tuple[Any, ...] = ()
    if limit:
        sql += " LIMIT ?"
        params = (limit,)
    with get_connection() as conn:
        return [dict(row) for row in conn.execute(sql, params).fetchall()]


def extract_pending(
    limit: int | None = None,
    force: bool = False,
    model: str | None = None,
    dry_run: bool = False,
) -> int:
    """Run extraction for pending papers and return successful extraction count."""

    init_db()
    papers = get_papers_for_extraction(limit=limit, force=force)
    if dry_run:
        print(f"{len(papers)} papers would be considered for extraction")
        return 0

    client = LLMClient(model=model)
    extracted = 0
    for paper in tqdm(papers, desc="Extracting abstracts"):
        pmid = paper["pmid"]
        abstract = clean_text(paper.get("abstract"))
        if not abstract:
            _mark_skipped(pmid)
            continue
        prompt = build_extraction_prompt(paper.get("title") or "unknown", abstract)
        try:
            raw = client.complete_json(SYSTEM_PROMPT, prompt)
            try:
                result, raw_json = validate_extraction(raw)
            except (ValidationError, json.JSONDecodeError, ValueError) as validation_error:
                repaired = client.complete_json(SYSTEM_PROMPT, _repair_prompt(raw, str(validation_error)))
                result, raw_json = validate_extraction(repaired)
            _save_extraction(pmid, result, raw_json, force=force)
            extracted += 1
        except Exception as exc:
            LOGGER.exception("Extraction failed for PMID %s", pmid)
            _mark_failed(pmid, str(exc))
    return extracted
