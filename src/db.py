"""SQLite database setup and helpers."""

from __future__ import annotations

import sqlite3
import re
import urllib.request
from pathlib import Path

from .config import AUTO_DOWNLOAD_DB, DB_PATH, DEPLOYMENT_DB_MIN_BYTES, DEPLOYMENT_DB_URL, ensure_directories
from .normalization import recovery_domain_records, research_topic_records, taxonomy_alias_records
from .utils import utc_now


def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Return a SQLite connection with row access by column name."""

    ensure_directories()
    _ensure_deployment_database(db_path)
    conn = sqlite3.connect(db_path, timeout=60)
    conn.row_factory = sqlite3.Row
    # Rollback journaling is safer for SQLite databases stored on ExFAT/USB drives.
    conn.execute("PRAGMA journal_mode = DELETE")
    conn.execute("PRAGMA busy_timeout = 60000")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _ensure_deployment_database(db_path: Path) -> None:
    """Download the hosted full database when the bundled DB is missing or stale."""

    if not AUTO_DOWNLOAD_DB or not DEPLOYMENT_DB_URL:
        return
    if db_path.exists() and db_path.stat().st_size >= DEPLOYMENT_DB_MIN_BYTES:
        return

    db_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = db_path.with_suffix(f"{db_path.suffix}.download")
    urllib.request.urlretrieve(DEPLOYMENT_DB_URL, tmp_path)
    if tmp_path.stat().st_size < DEPLOYMENT_DB_MIN_BYTES:
        tmp_path.unlink(missing_ok=True)
        raise RuntimeError("Downloaded deployment database is smaller than expected.")
    tmp_path.replace(db_path)


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
                abstract_conclusion_text TEXT,
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
                conclusion_text TEXT,
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

            CREATE TABLE IF NOT EXISTS recovery_domains (
                domain_name TEXT PRIMARY KEY,
                display_order INTEGER,
                description TEXT,
                status TEXT DEFAULT 'active',
                created_at TEXT,
                updated_at TEXT
            );

            CREATE TABLE IF NOT EXISTS research_topics (
                topic_name TEXT PRIMARY KEY,
                recovery_domain TEXT,
                status TEXT DEFAULT 'active',
                source TEXT,
                notes TEXT,
                created_at TEXT,
                updated_at TEXT,
                FOREIGN KEY (recovery_domain) REFERENCES recovery_domains(domain_name)
            );

            CREATE TABLE IF NOT EXISTS taxonomy_aliases (
                alias_key TEXT PRIMARY KEY,
                alias_label TEXT,
                topic_name TEXT,
                recovery_domain TEXT,
                source TEXT,
                created_at TEXT,
                updated_at TEXT,
                FOREIGN KEY (topic_name) REFERENCES research_topics(topic_name),
                FOREIGN KEY (recovery_domain) REFERENCES recovery_domains(domain_name)
            );

            CREATE TABLE IF NOT EXISTS taxonomy_review_queue (
                label_key TEXT PRIMARY KEY,
                raw_label TEXT,
                canonical_label TEXT,
                suggested_topic TEXT,
                suggested_domain TEXT,
                occurrence_count INTEGER DEFAULT 0,
                status TEXT DEFAULT 'needs_review',
                first_seen_at TEXT,
                last_seen_at TEXT,
                notes TEXT
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
            CREATE INDEX IF NOT EXISTS idx_research_topics_domain ON research_topics(recovery_domain);
            CREATE INDEX IF NOT EXISTS idx_taxonomy_review_status ON taxonomy_review_queue(status);
            """
        )
        _ensure_column(conn, "papers", "abstract_conclusion_text", "TEXT")
        _backfill_abstract_conclusions(conn)
        _ensure_column(conn, "study_extractions", "intervention_family", "TEXT")
        _ensure_column(conn, "study_extractions", "conclusion_text", "TEXT")
        _backfill_missing_value_labels(conn)
        _ensure_column(conn, "scores", "intervention_family", "TEXT")
        _ensure_column(conn, "intervention_summaries", "intervention_family", "TEXT")
        conn.executescript(
            """
            CREATE INDEX IF NOT EXISTS idx_extractions_family ON study_extractions(intervention_family);
            CREATE INDEX IF NOT EXISTS idx_scores_family ON scores(intervention_family);
            """
        )
        _seed_taxonomy_tables(conn)


def _seed_taxonomy_tables(conn: sqlite3.Connection) -> None:
    """Seed controlled Recovery Domain and Research Topic lookup tables."""

    now = utc_now()
    for row in recovery_domain_records():
        conn.execute(
            """
            INSERT INTO recovery_domains (
                domain_name, display_order, status, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(domain_name) DO UPDATE SET
                display_order = excluded.display_order,
                status = excluded.status,
                updated_at = excluded.updated_at
            """,
            (row["domain_name"], row["display_order"], row["status"], now, now),
        )

    for row in research_topic_records():
        conn.execute(
            """
            INSERT INTO research_topics (
                topic_name, recovery_domain, status, source, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(topic_name) DO UPDATE SET
                recovery_domain = excluded.recovery_domain,
                status = excluded.status,
                source = excluded.source,
                updated_at = excluded.updated_at
            """,
            (
                row["topic_name"],
                row["recovery_domain"],
                row["status"],
                row["source"],
                now,
                now,
            ),
        )

    for row in taxonomy_alias_records():
        conn.execute(
            """
            INSERT INTO taxonomy_aliases (
                alias_key, alias_label, topic_name, recovery_domain, source, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(alias_key) DO UPDATE SET
                alias_label = excluded.alias_label,
                topic_name = excluded.topic_name,
                recovery_domain = excluded.recovery_domain,
                source = excluded.source,
                updated_at = excluded.updated_at
            """,
            (
                row["alias_key"],
                row["alias_label"],
                row["topic_name"],
                row["recovery_domain"],
                row["source"],
                now,
                now,
            ),
        )


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    """Add a column to an existing SQLite table if it is missing."""

    columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def _extract_conclusion_from_abstract(abstract: str | None) -> str | None:
    """Extract a labeled conclusion section from stored PubMed abstract text."""

    if not abstract:
        return None
    match = re.search(
        r"\bCONCLUSIONS?\s*:\s*(.+?)(?=\s+[A-Z][A-Z /-]{2,}\s*:|$)",
        abstract,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    conclusion = " ".join(match.group(1).split())
    return conclusion or None


def _backfill_abstract_conclusions(conn: sqlite3.Connection) -> None:
    """Populate parsed conclusion text for existing structured abstracts."""

    rows = conn.execute(
        """
        SELECT pmid, abstract
        FROM papers
        WHERE abstract_conclusion_text IS NULL
            AND abstract IS NOT NULL
            AND (
                abstract LIKE '%CONCLUSION:%'
                OR abstract LIKE '%CONCLUSIONS:%'
                OR abstract LIKE '%Conclusion:%'
                OR abstract LIKE '%Conclusions:%'
            )
        """
    ).fetchall()
    for row in rows:
        conclusion = _extract_conclusion_from_abstract(row["abstract"])
        if conclusion:
            conn.execute(
                "UPDATE papers SET abstract_conclusion_text = ? WHERE pmid = ?",
                (conclusion, row["pmid"]),
            )


def _backfill_missing_value_labels(conn: sqlite3.Connection) -> None:
    """Set explicit labels for old blank conclusion fields without changing content."""

    conn.execute(
        """
        UPDATE papers
        SET abstract_conclusion_text = 'not reported in abstract'
        WHERE abstract_conclusion_text IS NULL
            OR TRIM(abstract_conclusion_text) = ''
        """
    )
    conn.execute(
        """
        UPDATE study_extractions
        SET conclusion_text = 'not reported in abstract'
        WHERE conclusion_text IS NULL
            OR TRIM(conclusion_text) = ''
            OR LOWER(TRIM(conclusion_text)) IN ('unknown', 'n/a', 'na')
        """
    )


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
