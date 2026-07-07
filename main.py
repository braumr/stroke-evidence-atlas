"""Command-line entrypoint for Stroke Evidence Atlas."""

from __future__ import annotations

import argparse
import sys

from src.config import DEFAULT_LLM_MODEL, MAX_PAPERS
from src.db import finish_pipeline_run, init_db, start_pipeline_run


try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    def load_dotenv() -> bool:
        return False


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Stroke Evidence Atlas V1 pipeline")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init-db", help="Initialize the SQLite database")
    init_parser.add_argument("--reset", action="store_true", help="Delete and recreate the SQLite database")

    collect_parser = subparsers.add_parser("collect", help="Collect PubMed papers")
    collect_parser.add_argument("--max-papers", type=int, default=MAX_PAPERS)
    collect_parser.add_argument("--query-domain", type=str, default=None)
    collect_parser.add_argument("--dry-run", action="store_true")

    extract_parser = subparsers.add_parser("extract", help="Extract structured evidence from abstracts")
    extract_parser.add_argument("--limit", type=int, default=None)
    extract_parser.add_argument("--force", action="store_true")
    extract_parser.add_argument("--model", type=str, default=DEFAULT_LLM_MODEL)
    extract_parser.add_argument("--dry-run", action="store_true")

    subparsers.add_parser("score", help="Score extracted evidence and aggregate interventions")
    subparsers.add_parser("export", help="Export CSV files")

    all_parser = subparsers.add_parser("all", help="Run collection, extraction, scoring, and export")
    all_parser.add_argument("--max-papers", type=int, default=MAX_PAPERS)
    all_parser.add_argument("--limit", type=int, default=None)
    all_parser.add_argument("--force", action="store_true")
    all_parser.add_argument("--reset", action="store_true")
    all_parser.add_argument("--query-domain", type=str, default=None)
    all_parser.add_argument("--model", type=str, default=DEFAULT_LLM_MODEL)
    all_parser.add_argument("--dry-run", action="store_true")

    return parser


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    args = build_parser().parse_args(argv)
    if args.command == "init-db":
        init_db(reset=args.reset)
        print("Database initialized")
        return 0

    if args.command == "all" and args.reset:
        init_db(reset=True)
    else:
        init_db()
    run_id = start_pipeline_run(args.command)
    try:
        if args.command == "collect":
            from src.collectors.pubmed import collect_pubmed

            inserted = collect_pubmed(args.max_papers, args.query_domain, args.dry_run)
            print(f"Collection complete: {inserted} new papers inserted")
        elif args.command == "extract":
            from src.extractor import extract_pending

            count = extract_pending(args.limit, args.force, args.model, args.dry_run)
            print(f"Extraction complete: {count} papers extracted")
        elif args.command == "score":
            from src.scoring import score_extractions

            count = score_extractions()
            print(f"Scoring complete: {count} extracted studies scored")
        elif args.command == "export":
            from src.exports import export_csvs

            written = export_csvs()
            for table, path in written.items():
                print(f"{table}: {path}")
        elif args.command == "all":
            from src.collectors.pubmed import collect_pubmed
            from src.exports import export_csvs
            from src.extractor import extract_pending
            from src.scoring import score_extractions

            init_db()
            inserted = collect_pubmed(args.max_papers, args.query_domain, args.dry_run)
            extracted = extract_pending(args.limit, args.force, args.model, args.dry_run)
            scored = score_extractions()
            written = export_csvs()
            print(f"All complete: inserted={inserted}, extracted={extracted}, scored={scored}")
            for table, path in written.items():
                print(f"{table}: {path}")
        finish_pipeline_run(run_id, "success")
        return 0
    except Exception as exc:
        finish_pipeline_run(run_id, "failed", str(exc))
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
