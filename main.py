"""Command-line entrypoint for Stroke Recovery Research Platform."""

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
    parser = argparse.ArgumentParser(description="Stroke Recovery Research Platform pipeline")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init-db", help="Initialize the SQLite database")
    init_parser.add_argument("--reset", action="store_true", help="Delete and recreate the SQLite database")

    collect_parser = subparsers.add_parser("collect", help="Collect PubMed papers")
    collect_parser.add_argument("--max-papers", type=int, default=MAX_PAPERS)
    collect_parser.add_argument("--query-domain", type=str, default=None)
    collect_parser.add_argument("--dry-run", action="store_true")

    collect_core_years_parser = subparsers.add_parser(
        "collect-core-years",
        help="Collect the broad PubMed core query one publication year at a time",
    )
    collect_core_years_parser.add_argument("--start-year", type=int, default=1900)
    collect_core_years_parser.add_argument("--end-year", type=int, default=None)
    collect_core_years_parser.add_argument("--retmax-per-year", type=int, default=9999)
    collect_core_years_parser.add_argument("--dry-run", action="store_true")

    extract_parser = subparsers.add_parser("extract", help="Extract structured evidence from abstracts")
    extract_parser.add_argument("--limit", type=int, default=None)
    extract_parser.add_argument("--force", action="store_true")
    extract_parser.add_argument("--model", type=str, default=DEFAULT_LLM_MODEL)
    extract_parser.add_argument("--dry-run", action="store_true")
    extract_parser.add_argument("--workers", type=int, default=1, help="Number of parallel extraction workers")
    extract_parser.add_argument("--batch-size", type=int, default=1, help="Number of papers per extraction request")
    extract_parser.add_argument(
        "--profile",
        choices=["full", "budget"],
        default="full",
        help="Extraction prompt profile. budget uses shorter outputs for lower API cost.",
    )
    extract_parser.add_argument("--max-cost-usd", type=float, default=None, help="Hard stop at estimated API cost")

    subparsers.add_parser("classify", help="Classify extracted studies into Recovery Domains and Research Topics")
    subparsers.add_parser("score", help="Score extracted evidence and aggregate research topics")
    subparsers.add_parser("export", help="Export CSV files")

    all_parser = subparsers.add_parser("all", help="Run collection, extraction, classification, optional scoring, and export")
    all_parser.add_argument("--max-papers", type=int, default=MAX_PAPERS)
    all_parser.add_argument("--limit", type=int, default=None)
    all_parser.add_argument("--force", action="store_true")
    all_parser.add_argument("--reset", action="store_true")
    all_parser.add_argument("--query-domain", type=str, default=None)
    all_parser.add_argument("--model", type=str, default=DEFAULT_LLM_MODEL)
    all_parser.add_argument("--dry-run", action="store_true")
    all_parser.add_argument("--skip-score", action="store_true", help="Classify and aggregate without recalculating scores")
    all_parser.add_argument("--workers", type=int, default=1, help="Number of parallel extraction workers")
    all_parser.add_argument("--batch-size", type=int, default=1, help="Number of papers per extraction request")
    all_parser.add_argument(
        "--profile",
        choices=["full", "budget"],
        default="full",
        help="Extraction prompt profile. budget uses shorter outputs for lower API cost.",
    )
    all_parser.add_argument("--max-cost-usd", type=float, default=None, help="Hard stop at estimated API cost")

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
        elif args.command == "collect-core-years":
            from src.collectors.pubmed import collect_pubmed_core_by_year

            inserted = collect_pubmed_core_by_year(
                args.start_year,
                args.end_year,
                args.retmax_per_year,
                args.dry_run,
            )
            print(f"Year-split core collection complete: {inserted} new papers inserted")
        elif args.command == "extract":
            from src.extractor import extract_pending
            from src.llm_client import usage_totals

            count = extract_pending(
                args.limit,
                args.force,
                args.model,
                args.dry_run,
                args.workers,
                args.batch_size,
                args.profile,
                args.max_cost_usd,
            )
            totals = usage_totals()
            print(f"Extraction complete: {count} papers extracted")
            print(
                "Estimated API usage: "
                f"requests={totals.requests}, input_tokens={totals.input_tokens}, "
                f"output_tokens={totals.output_tokens}, cost=${totals.estimated_cost_usd:.2f}"
            )
        elif args.command == "classify":
            from src.classification import classify_extractions

            count = classify_extractions()
            print(f"Classification complete: {count} extracted studies classified")
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
            from src.llm_client import usage_totals

            init_db()
            inserted = collect_pubmed(args.max_papers, args.query_domain, args.dry_run)
            extracted = extract_pending(
                args.limit,
                args.force,
                args.model,
                args.dry_run,
                args.workers,
                args.batch_size,
                args.profile,
                args.max_cost_usd,
            )
            if args.skip_score:
                from src.classification import classify_extractions

                classified = classify_extractions()
                scored = "skipped"
            else:
                from src.scoring import score_extractions

                scored = score_extractions()
                classified = scored
            written = export_csvs()
            totals = usage_totals()
            print(f"All complete: inserted={inserted}, extracted={extracted}, classified={classified}, scored={scored}")
            print(
                "Estimated API usage: "
                f"requests={totals.requests}, input_tokens={totals.input_tokens}, "
                f"output_tokens={totals.output_tokens}, cost=${totals.estimated_cost_usd:.2f}"
            )
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
