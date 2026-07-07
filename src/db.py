"""SQLite database setup and helpers."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from .config import DB_PATH, ensure_directories
from .utils import utc_now


def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Return a SQLite connection with row access by column name."""

    ensure_directories()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(reset: bool = False) -> None:
    """Create all database tables idempotently."""

    ensure_directories()
    if reset and DB_PATH.exists():
        DB_PATH.unlink()

    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS papers (
                pmid TEXT PRIMARY KEY,
                title TEXT,
                abstract TEXT,
                journal TEXT,
                publication_year INTEGER,
                publication_date TEXT,
                authors TEXT,
                mesh_terms TEXT,
                doi TEXT,
                pubmed_url TEXT,
                source TEXT,
                query_source TEXT,
                created_at TEXT,
                updated_at TEXT
            );

            CREATE TABLE IF NOT EXISTS extraction_status (
                pmid TEXT PRIMARY KEY,
                status TEXT CHECK(status IN ('pending', 'extracted', 'failed', 'skipped_no_abstract')),
                attempts INTEGER DEFAULT 0,
                last_error TEXT,
                extracted_at TEXT,
                updated_at TEXT,
                FOREIGN KEY (pmid) REFERENCES papers(pmid)
            );

            CREATE TABLE IF NOT EXISTS study_extractions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pmid TEXT,
                study_type TEXT,
                intervention_raw TEXT,
                intervention_canonical TEXT,
                intervention_family TEXT,
                intervention_category TEXT,
                condition_category TEXT,
                stroke_type TEXT,
                participant_characteristics TEXT,
                sample_size INTEGER,
                time_since_stroke TEXT,
                stroke_phase TEXT,
                dosage_intensity TEXT,
                frequency TEXT,
                duration TEXT,
                comparator TEXT,
                setting TEXT,
                outcome_measures TEXT,
                outcomes TEXT,
                results_summary TEXT,
                effect_direction TEXT,
                limitations TEXT,
                adverse_events TEXT,
                safety_notes TEXT,
                applicability_notes TEXT,
                mechanistic_rationale TEXT,
                neuroplasticity_mechanisms TEXT,
                confidence_notes TEXT,
                provenance_json TEXT,
                raw_llm_json TEXT,
                created_at TEXT,
                FOREIGN KEY (pmid) REFERENCES papers(pmid)
            );

            CREATE TABLE IF NOT EXISTS scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pmid TEXT,
                intervention_canonical TEXT,
                intervention_family TEXT,
                intervention_category TEXT,
                neuroplasticity_potential REAL,
                clinical_evidence_strength REAL,
                safety_score REAL,
                practicality_score REAL,
                overall_score REAL,
                study_quality_tier TEXT,
                scoring_notes TEXT,
                created_at TEXT,
                FOREIGN KEY (pmid) REFERENCES papers(pmid)
            );

            CREATE TABLE IF NOT EXISTS intervention_summaries (
                intervention_canonical TEXT PRIMARY KEY,
                intervention_family TEXT,
                intervention_category TEXT,
                paper_count INTEGER,
                human_study_count INTEGER,
                rct_count INTEGER,
                systematic_review_count INTEGER,
                meta_analysis_count INTEGER,
                animal_study_count INTEGER,
                avg_neuroplasticity_potential REAL,
                avg_clinical_evidence_strength REAL,
                avg_safety_score REAL,
                avg_practicality_score REAL,
                avg_overall_score REAL,
                evidence_tier TEXT,
                common_outcome_measures TEXT,
                treatment_protocols TEXT,
                key_limitations TEXT,
                safety_summary TEXT,
                updated_at TEXT
            );

            CREATE TABLE IF NOT EXISTS query_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_domain TEXT,
                query_name TEXT,
                query_text TEXT,
                result_count INTEGER,
                run_at TEXT
            );

            CREATE TABLE IF NOT EXISTS pipeline_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                command TEXT,
                started_at TEXT,
                finished_at TEXT,
                status TEXT,
                notes TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_papers_year ON papers(publication_year);
            CREATE INDEX IF NOT EXISTS idx_extractions_pmid ON study_extractions(pmid);
            CREATE INDEX IF NOT EXISTS idx_extractions_intervention ON study_extractions(intervention_canonical);
            CREATE INDEX IF NOT EXISTS idx_scores_intervention ON scores(intervention_canonical);
            """
        )
        _ensure_column(conn, "study_extractions", "intervention_family", "TEXT")
        _ensure_column(conn, "scores", "intervention_family", "TEXT")
        _ensure_column(conn, "intervention_summaries", "intervention_family", "TEXT")
        conn.executescript(
            """
            CREATE INDEX IF NOT EXISTS idx_extractions_family ON study_extractions(intervention_family);
            CREATE INDEX IF NOT EXISTS idx_scores_family ON scores(intervention_family);
            """
        )


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    """Add a column to an existing SQLite table if it is missing."""

    columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def start_pipeline_run(command: str, notes: str = "") -> int:
    """Record a pipeline run start and return its row id."""

    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO pipeline_runs (command, started_at, status, notes)
            VALUES (?, ?, ?, ?)
            """,
            (command, utc_now(), "running", notes),
        )
        return int(cur.lastrowid)


def finish_pipeline_run(run_id: int, status: str, notes: str = "") -> None:
    """Record a pipeline run finish."""

    with get_connection() as conn:
        conn.execute(
            """
            UPDATE pipeline_runs
            SET finished_at = ?, status = ?, notes = ?
            WHERE id = ?
            """,
            (utc_now(), status, notes, run_id),
        )


def upsert_extraction_status(pmid: str, status: str = "pending") -> None:
    """Create an extraction status row without clobbering completed work."""

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO extraction_status (pmid, status, attempts, updated_at)
            VALUES (?, ?, 0, ?)
            ON CONFLICT(pmid) DO UPDATE SET
                updated_at = excluded.updated_at
            """,
            (pmid, status, utc_now()),
        )
