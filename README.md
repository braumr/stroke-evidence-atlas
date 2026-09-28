# Stroke Recovery Research Platform

AI-assisted evidence mapping for stroke recovery, neurorehabilitation, and neuroplasticity research.

Stroke Recovery Research Platform is a local research synthesis dashboard that collects PubMed literature, extracts structured study information from abstracts, groups papers into recovery domains and research topics, scores evidence signals, and presents the results in an interactive Streamlit app. It is designed for research exploration and evidence mapping, not medical advice.

## Why This Project Exists

Stroke recovery research is spread across many domains: physical rehabilitation, occupational therapy, speech/language therapy, cognitive rehabilitation, robotics, electrical stimulation, noninvasive brain stimulation, exercise, sleep, nutrition, mood, caregiver training, neuroplasticity mechanisms, and biomarkers.

A normal PubMed search returns papers, but it does not organize them into a usable recovery map. Stroke Recovery Research Platform turns scattered abstracts into a structured, searchable evidence landscape.

## What the Application Does

- Collects PubMed papers using structured search queries
- Stores raw paper metadata and abstracts in SQLite
- Uses GPT-4o mini to extract structured evidence from abstracts
- Normalizes extracted labels into research topics
- Groups research topics into recovery domains
- Scores evidence using transparent components
- Displays research topic summaries, supporting studies, and paper-level details
- Links every paper back to PubMed

## System Workflow

```text
PubMed Search Queries
        ↓
Paper Collection
        ↓
SQLite Database
        ↓
LLM Abstract Extraction
        ↓
Research Topic Normalization
        ↓
Taxonomy Review Queue
        ↓
Evidence Scoring
        ↓
Research Topic Aggregation
        ↓
Streamlit Evidence Dashboard
```

PubMed collection gathers paper metadata and abstracts, then stores them locally. The extraction layer sends title and abstract text to the LLM and validates structured JSON output before saving it.

Normalization groups similar extracted labels into controlled research topics. Unmapped extracted labels are placed in a `Needs Taxonomy Review` bucket and written to `taxonomy_review_queue` instead of automatically becoming new official topics. Scoring is optional; the project can classify extracted studies into Recovery Domains and Research Topics without recalculating numeric evidence scores.

## Architecture Overview

```text
stroke-evidence-atlas/
├── main.py
├── src/
│   ├── collectors/
│   ├── extractor.py
│   ├── scoring.py
│   ├── aggregator.py
│   ├── normalization.py
│   └── db.py
├── ui/
│   ├── app.py
│   └── pages/
└── data/
    └── stroke_evidence.db
```

`main.py` controls the pipeline commands. `src/collectors/pubmed.py` handles PubMed collection, `extractor.py` manages LLM extraction, `normalization.py` standardizes extracted labels into research topics and recovery domains, `scoring.py` creates evidence scores, and `aggregator.py` builds research topic summaries. The `ui/` folder contains the Streamlit dashboard, while SQLite is the local source of truth.

## Database Design

The app uses SQLite as its primary datastore.

- `papers`: raw PubMed metadata, abstracts, journal information, and links
- `extraction_status`: processing state for each paper, including extracted, pending, failed, or skipped
- `study_extractions`: structured fields extracted from each abstract
- `scores`: paper-level evidence scores and scoring notes
- `intervention_summaries`: aggregated research-topic evidence summaries
- `recovery_domains`: controlled high-level Recovery Domain taxonomy
- `research_topics`: controlled Research Topic taxonomy mapped to Recovery Domains
- `taxonomy_aliases`: synonym and alias mappings used during normalization
- `taxonomy_review_queue`: extracted labels that need human taxonomy review before becoming approved topics
- `query_log`: search query metadata and collection history

Database screenshots from DBeaver can be added here.

## Database Screenshots

_Add DBeaver schema screenshots here._

## LLM Extraction Logic

The system sends PubMed title and abstract text to GPT-4o mini and asks for structured JSON. It extracts fields such as study type, recovery domain, research topic, stroke type, sample size, timing after stroke, dosage or intensity when available, outcome measures, results summary, limitations, adverse events, safety notes, and neuroplasticity mechanisms.

The system uses abstracts only. It does not read PDFs or full-text articles, and it is instructed not to invent details that are not present in the abstract. Missing fields may be marked as `not reported in abstract`, `not applicable`, or `unknown`.

## Evidence Scoring and Research Topic Aggregation

Scores are exploratory research signals, not medical truth scores. Each paper receives component scores for:

- Neuroplasticity Potential
- Clinical Evidence Strength
- Safety
- Practicality

Paper-level extractions are grouped into research topics such as Constraint-Induced Movement Therapy, Vagus Nerve Stimulation, Robotics / Assistive Technology, Exercise / Physical Conditioning, Sleep / Circadian Recovery, Nutrition / Metabolic Support, Cognitive Rehabilitation, and Speech / Language / Aphasia Rehabilitation.

The dashboard then shows paper counts, study types, evidence tiers, scores, protocols, outcomes, limitations, and supporting PubMed studies.

## Streamlit Dashboard

The app navigation is:

**Home | Recovery Explorer | Recovery Detail | Paper Explorer | Methodology**

**Recovery Explorer**
- Shows high-level paper, research topic, RCT, and review counts
- Ranks research topics by average overall score
- Provides filters for recovery domain, evidence tier, stroke type, study type, and phase

**Recovery Detail**
- Lets users select a research topic
- Shows paper counts, human studies, RCTs, review counts, and score components
- Lists supporting studies, extracted protocols, outcomes, limitations, and safety details

**Paper Explorer**
- Provides paper-level audit views for individual PubMed records
- Shows abstracts, conclusions when available, structured extracted fields, provenance, and scores
- Links each record back to PubMed

## Example Use Case

A user interested in Vagus Nerve Stimulation can select that research topic in Recovery Detail and review paper count, human studies, RCT count, systematic review/meta-analysis count, average evidence scores, extracted paper-level names, common outcome measures, treatment protocols when reported, safety notes, and supporting PubMed papers.

## Screenshots

### Recovery Explorer

_Add screenshot here._

### Recovery Detail

_Add screenshot here._

### Paper Explorer

_Add screenshot here._

## How to Run Locally

GPT extraction requires an OpenAI API key.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export OPENAI_API_KEY="your_key_here"
python main.py collect --max-papers 2000
python main.py extract
python main.py classify
streamlit run ui/app.py
```

On Windows:

```powershell
.venv\Scripts\activate
setx OPENAI_API_KEY "your_key_here"
```

CSV exports can be generated with:

```bash
python main.py export
```

Scoring can be run when numeric evidence signals are needed:

```bash
python main.py score
```

For larger extraction batches where classification matters more than scoring:

```bash
python main.py all --max-papers 5000 --limit 5000 --skip-score
```

## Limitations

Stroke Recovery Research Platform uses abstract-only extraction, so it can miss details found in full papers. LLM extraction may make mistakes, which is why PubMed links and paper-level audit views are included for verification.

Scores are exploratory evidence signals, not clinical recommendations. The app does not provide medical advice, and the search strategy, normalization dictionary, and extraction rules can be improved over time.

## Tech Stack

- Python
- SQLite
- PubMed E-utilities
- OpenAI GPT-4o mini
- Streamlit
- pandas
- Plotly
