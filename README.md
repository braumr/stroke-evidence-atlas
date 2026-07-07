# Stroke Evidence Atlas

Stroke Evidence Atlas is a local research synthesis engine for stroke rehabilitation, brain injury recovery, and neuroplasticity evidence. Version 1 collects PubMed abstracts, extracts structured rehabilitation evidence with GPT-4o mini, stores results in SQLite, scores interventions with a transparent configurable framework, exports CSVs, and provides a simple Streamlit dashboard.

This project summarizes research literature only. It is not medical advice, a treatment plan, or a replacement for clinicians.

## What It Does

- Collects PubMed papers using NCBI E-utilities.
- Stores paper metadata, abstracts, extraction status, structured extractions, scores, and intervention summaries in SQLite.
- Extracts structured evidence from abstracts using the OpenAI API.
- Validates JSON locally and runs one repair prompt only when validation fails.
- Normalizes intervention names with a configurable Python synonym dictionary.
- Scores interventions using configurable, transparent component weights.
- Aggregates intervention-level summaries.
- Exports CSV files.
- Provides a multipage Streamlit dashboard.

## What It Does Not Do

Version 1 does not implement Semantic Scholar, Crossref, ClinicalTrials.gov, vector search, a knowledge graph, a chatbot, trend dashboards, caregiver AI assistance, Markdown report generation, full-text PDF parsing, or patient-specific treatment planning.

## Version 1 Scope

Implemented:

- PubMed collection only
- SQLite database
- GPT-4o mini abstract extraction
- Local JSON validation
- Repair prompt only when JSON validation fails
- Intervention normalization
- Transparent scoring
- CSV exports
- Streamlit pages for overview, interventions, and papers

Future collectors can be added under `src/collectors/`, but only PubMed is implemented in V1.

## Install

```bash
python -m venv .venv
```

Mac/Linux:

```bash
source .venv/bin/activate
```

Windows:

```powershell
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## API Key Setup

OpenAI extraction requires `OPENAI_API_KEY`. Do not hardcode keys in the project.

Mac/Linux:

```bash
export OPENAI_API_KEY="your_key_here"
```

Verify this terminal can see the key without printing it:

```bash
python -c "import os; print('OPENAI_API_KEY visible:', bool(os.getenv('OPENAI_API_KEY')))"
```

Windows PowerShell:

```powershell
setx OPENAI_API_KEY "your_key_here"
```

Optional local `.env` files are supported and ignored by git:

```bash
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4o-mini
NCBI_API_KEY=optional_ncbi_key
```

## Commands

Initialize the database:

```bash
python main.py init-db
```

Reset the database:

```bash
python main.py init-db --reset
```

Collect PubMed papers:

```bash
python main.py collect --max-papers 2000
```

Collect one query domain:

```bash
python main.py collect --query-domain motor
```

Extract structured evidence:

```bash
python main.py extract --limit 50
```

Force re-extraction:

```bash
python main.py extract --limit 50 --force
```

Score and aggregate:

```bash
python main.py score
```

Export CSVs:

```bash
python main.py export
```

Run all steps:

```bash
python main.py all --max-papers 2000
```

Launch Streamlit:

```bash
streamlit run ui/app.py
```

## Small Test

```bash
python main.py init-db
python main.py collect --max-papers 25
python main.py extract --limit 5
python main.py score
python main.py export
```

## Full Pipeline

```bash
python main.py all --max-papers 2000
```

## Resume and Checkpointing

Collection inserts papers as they are fetched and deduplicates only by exact PMID. Existing PMIDs are ignored rather than deleted. Each collected paper receives an `extraction_status` row.

Extraction checks `extraction_status` before processing. Already extracted papers are skipped unless `--force` is used. Papers without abstracts are marked `skipped_no_abstract`. Successful extractions are written immediately before status is updated to `extracted`. Failures increment attempts and store the last error. A crash does not require restarting from the beginning.

Scoring and aggregation are rerunnable without recollecting papers or rerunning LLM extraction.

## Scoring

Scores are research synthesis aids, not proof. Component scores use a 0-100 scale:

- `neuroplasticity_potential`: plausible recovery mechanism engagement
- `clinical_evidence_strength`: human clinical evidence strength
- `safety_score`: safety/tolerability signal and uncertainty
- `practicality_score`: real-world feasibility

Default weights in `src/config.py`:

- neuroplasticity potential: 0.40
- clinical evidence strength: 0.35
- safety: 0.15
- practicality: 0.10

Intervention-level evidence tiers are assigned during aggregation and distinguish strong, moderate, emerging, conflicting, insufficient, and mechanistic/preclinical evidence.

## Intervention Normalization and Families

The LLM extracts a raw intervention name. Python then normalizes that name with `src/normalization.py`. Examples include CIMT to `Constraint-Induced Movement Therapy`, FES to `Functional Electrical Stimulation`, tDCS to `Transcranial Direct Current Stimulation`, and VR rehabilitation to `Virtual Reality Rehabilitation`.

Unknown or unmatched interventions remain as cleaned raw names. The system avoids forcing interventions into incorrect categories.

The dashboard also derives a broader `intervention_family` for user-facing browsing. This keeps paper-level extracted names available for audit while grouping similar papers into clearer families such as `Brain-Computer Interface Rehabilitation`, `Speech and Language Therapy`, or `Exercise and Fitness Training`. Papers without a specific extractable intervention are grouped into `Unspecified / not intervention-specific` rather than treated as a real intervention.

## CSV Exports

CSV files are written to `data/exports/`:

- `papers.csv`
- `extractions.csv`
- `interventions.csv`
- `scores.csv`

Run:

```bash
python main.py export
```

## Limitations and Clinical Caution

The atlas depends on PubMed abstracts and structured extraction from those abstracts. It does not read full-text PDFs in Version 1. Abstracts may omit details about dosage, adverse events, patient characteristics, or results. LLM extraction may be imperfect, so provenance and paper-level audit views are included.

Do not use this project to generate patient-specific medical advice. It may summarize evidence, compare interventions, show uncertainty, and identify research gaps. It must distinguish clinical evidence from mechanistic, animal, weak, or emerging evidence.

## Future Expansion Ideas Not Implemented in V1

- Semantic Scholar collector
- Crossref collector
- ClinicalTrials.gov collector
- Full-text PDF parsing
- Trend dashboards
- Vector search
- Knowledge graph
- Report generation
- Patient/caregiver assistant
