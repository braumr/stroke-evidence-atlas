"""LLM abstract extraction with validation and resumable checkpointing."""

from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError
from tqdm import tqdm

from .db import get_connection, init_db
from .llm_client import LLMClient
from .normalization import intervention_family, normalize_intervention, recovery_group
from .utils import clean_text, normalize_missing_label, normalize_missing_list, parse_int, setup_logging, utc_now

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
    conclusion: ProvenanceField = Field(default_factory=ProvenanceField)


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
    conclusion_text: str = "not reported in abstract"
    effect_direction: str = "unclear"
    limitations: list[str] = Field(default_factory=list)
    adverse_events: str = "unknown"
    safety_notes: str = "unknown"
    applicability_notes: str = "unknown"
    mechanistic_rationale: str = "unknown"
    neuroplasticity_mechanisms: list[str] = Field(default_factory=list)
    confidence_notes: str = "unknown"
    provenance: Provenance = Field(default_factory=Provenance)


REVIEW_OR_BACKGROUND_TYPES = {
    "meta_analysis",
    "systematic_review",
    "narrative_review",
    "mechanistic_study",
    "diagnostic_biomarker",
    "epidemiology",
    "protocol",
}


SYSTEM_PROMPT = """You extract structured stroke recovery and neuroplasticity evidence from PubMed abstracts.
Return strict JSON only. Do not include Markdown.
Use only the title and abstract supplied by the user.
Do not fabricate citations, PMIDs, sample sizes, intervention details, adverse events, or results.
Use only these missing-value labels: "not reported in abstract", "not applicable", and "unknown".
Use "not reported in abstract" when the field could apply but the abstract does not state it, such as dosage, frequency, duration, outcome measures, limitations, adverse events, or conclusion.
Use "not applicable" when the field does not logically apply to that paper, such as dosage/frequency/duration for a narrative review, comparator for a mechanism paper, treatment protocol for a biomarker-only paper, or adverse events for a general neuroplasticity review.
Use "unknown" only when it is genuinely unclear whether the information is missing or not applicable.
This atlas includes broad recovery domains, not only hands-on therapy interventions.
Nutrition, sleep, inflammation, pharmacology, molecular pathways, vascular risk management, mood, motivation, caregiver training, home rehab, telerehab, cognition, aphasia, biomarkers, and outcome measurement are valid evidence areas.
Assign the most specific broad recovery-related evidence area supported by the abstract.
Do not overuse unknown when a meaningful recovery or neuroplasticity domain is supported by the abstract.
Do not force diagnostic, epidemiology, biomarker, protocol, animal, or mechanistic papers into direct clinical rehabilitation evidence.
Animal and mechanistic evidence must not be treated as human clinical proof."""


EXTRACTION_PROMPT = """Extract JSON matching this schema exactly:
{
  "study_type": "meta_analysis | systematic_review | randomized_controlled_trial | cohort_study | case_control_study | case_series | case_report | animal_study | mechanistic_study | feasibility_study | pilot_study | narrative_review | protocol | diagnostic_biomarker | epidemiology | qualitative | mixed_methods | unknown",
  "intervention": "specific intervention name or unknown",
  "intervention_category": "best broad Recovery Group: Physical Rehabilitation | Cognition and Communication | Rehabilitation Technology | Brain and Nerve Stimulation | Lifestyle and Daily Health | Medical and Biological Recovery | Family and Home Support | Testing and Prediction | Recovery Science | General Rehabilitation | Other",
  "condition_category": "ischemic_stroke | hemorrhagic_stroke | intracerebral_hemorrhage | subarachnoid_hemorrhage | traumatic_brain_injury | acquired_brain_injury | mixed_stroke | mixed_neurological | healthy_controls | not_applicable | unknown",
  "stroke_type": "ischemic | hemorrhagic | intracerebral_hemorrhage | subarachnoid_hemorrhage | mixed | not_stroke | unknown",
  "participant_characteristics": "age, severity, impairment type, inclusion details if available, or not reported in abstract",
  "sample_size": null,
  "time_since_stroke": "acute/subacute/chronic timing or exact timing if available",
  "stroke_phase": "acute | subacute | chronic | mixed | unknown",
  "dosage_intensity": "dose or intensity if stated, not reported in abstract, or not applicable",
  "frequency": "frequency if stated, not reported in abstract, or not applicable",
  "duration": "intervention duration if stated, not reported in abstract, or not applicable",
  "comparator": "usual care | sham | active control | waitlist | none | not reported in abstract | not applicable | unknown",
  "setting": "inpatient | outpatient | home | community | laboratory | mixed | unknown",
  "outcome_measures": [],
  "outcomes": [],
  "results_summary": "concise summary of reported results",
  "conclusion_text": "conclusion/conclusions text if explicitly present in the abstract; otherwise not reported in abstract",
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
    "adverse_events": {"value": "string", "supporting_sentence": "exact sentence or unknown"},
    "conclusion": {"value": "string", "supporting_sentence": "exact sentence or unknown"}
  }
}

Classification guidance:
- Use the intervention field for a specific therapy/intervention when present.
- If no hands-on therapy is described, still classify the paper into the best supported recovery-related domain.
- Valid broad domains include motor rehabilitation, upper-limb rehabilitation, gait/balance rehabilitation, CIMT, mirror therapy/motor imagery, robotics/assistive technology, virtual reality/digital rehabilitation, electrical stimulation, noninvasive brain stimulation, brain-computer interfaces, exercise/conditioning, speech/language/aphasia, cognitive rehabilitation, neglect/perceptual rehabilitation, mind-body/behavioral rehabilitation, music/art/enriched activity, sleep/circadian recovery, nutrition/metabolic support, inflammation/immune/biological repair, pharmacologic/molecular recovery, vascular/cardiometabolic management, depression/mood/motivation, caregiver/family training, home/community/telerehabilitation, environmental enrichment, general neurorehabilitation, general neuroplasticity/mechanisms, assessment/outcome measurement, and diagnostic/biomarker.
- Preserve uncertainty and do not fabricate treatment protocol details.
- Do not invent a conclusion. conclusion_text must be copied or summarized only from a conclusion/conclusions statement present in the PubMed abstract; otherwise use "not reported in abstract".
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
    _cleanup_extraction(parsed)
    return parsed, json.dumps(raw_dict, ensure_ascii=False)


def _cleanup_extraction(parsed: ExtractionResult) -> None:
    """Normalize missing-value labels and field-specific applicability locally."""

    study_type = parsed.study_type
    not_applicable_protocol = study_type in REVIEW_OR_BACKGROUND_TYPES
    not_applicable_comparator = study_type in {
        "mechanistic_study",
        "diagnostic_biomarker",
        "epidemiology",
        "narrative_review",
        "protocol",
    }

    def field_label(value: object, default: str) -> str:
        normalized = normalize_missing_label(value, default)
        if normalized == "unknown" and default != "unknown":
            return default
        return str(normalized)

    parsed.intervention = str(normalize_missing_label(parsed.intervention, "unknown"))
    parsed.intervention_category = str(normalize_missing_label(parsed.intervention_category, "unknown"))
    parsed.condition_category = str(normalize_missing_label(parsed.condition_category, "unknown"))
    parsed.stroke_type = str(normalize_missing_label(parsed.stroke_type, "unknown"))
    parsed.participant_characteristics = str(normalize_missing_label(parsed.participant_characteristics))
    parsed.time_since_stroke = str(normalize_missing_label(parsed.time_since_stroke))
    parsed.stroke_phase = str(normalize_missing_label(parsed.stroke_phase, "unknown"))
    parsed.setting = str(normalize_missing_label(parsed.setting, "unknown"))
    parsed.results_summary = str(normalize_missing_label(parsed.results_summary))
    parsed.conclusion_text = str(normalize_missing_label(parsed.conclusion_text))
    if parsed.conclusion_text in {"unknown", "not applicable"}:
        parsed.conclusion_text = "not reported in abstract"
    parsed.effect_direction = str(normalize_missing_label(parsed.effect_direction, "unclear"))
    parsed.safety_notes = str(normalize_missing_label(parsed.safety_notes))
    parsed.applicability_notes = str(normalize_missing_label(parsed.applicability_notes))
    parsed.mechanistic_rationale = str(normalize_missing_label(parsed.mechanistic_rationale))
    parsed.confidence_notes = str(normalize_missing_label(parsed.confidence_notes, "unknown"))

    protocol_default = "not applicable" if not_applicable_protocol else "not reported in abstract"
    parsed.dosage_intensity = field_label(parsed.dosage_intensity, protocol_default)
    parsed.frequency = field_label(parsed.frequency, protocol_default)
    parsed.duration = field_label(parsed.duration, protocol_default)

    comparator_default = "not applicable" if not_applicable_comparator else "not reported in abstract"
    parsed.comparator = field_label(parsed.comparator, comparator_default)

    adverse_default = "not applicable" if study_type in {"narrative_review", "mechanistic_study", "diagnostic_biomarker", "epidemiology"} else "not reported in abstract"
    parsed.adverse_events = field_label(parsed.adverse_events, adverse_default)

    parsed.outcome_measures = normalize_missing_list(parsed.outcome_measures)
    parsed.outcomes = normalize_missing_list(parsed.outcomes)
    parsed.limitations = normalize_missing_list(parsed.limitations)
    parsed.neuroplasticity_mechanisms = normalize_missing_list(parsed.neuroplasticity_mechanisms, "unknown")


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


def _save_extraction(
    pmid: str,
    extraction: ExtractionResult,
    raw_json: str,
    force: bool = False,
    evidence_text: str = "",
) -> None:
    canonical = normalize_intervention(extraction.intervention)
    family = intervention_family(extraction.intervention, canonical, extraction.intervention_category, evidence_text)
    group = recovery_group(
        extraction.intervention,
        canonical,
        family,
        extraction.intervention_category,
        evidence_text,
    )
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
                setting, outcome_measures, outcomes, results_summary, conclusion_text,
                effect_direction, limitations, adverse_events, safety_notes,
                applicability_notes, mechanistic_rationale, neuroplasticity_mechanisms,
                confidence_notes, provenance_json, raw_llm_json, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                pmid,
                extraction.study_type,
                clean_text(extraction.intervention),
                canonical,
                family,
                group,
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
                extraction.conclusion_text,
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
            _save_extraction(
                pmid,
                result,
                raw_json,
                force=force,
                evidence_text=f"{paper.get('title') or ''} {abstract}",
            )
            extracted += 1
        except Exception as exc:
            LOGGER.exception("Extraction failed for PMID %s", pmid)
            _mark_failed(pmid, str(exc))
    return extracted
