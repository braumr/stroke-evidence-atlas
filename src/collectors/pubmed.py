"""PubMed E-utilities collector."""

from __future__ import annotations

import json
import os
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any

import requests
from tenacity import retry, stop_after_attempt, wait_exponential
from tqdm import tqdm

from src.config import (
    NCBI_API_KEY,
    NCBI_EMAIL,
    NCBI_TOOL,
    PUBMED_FETCH_BATCH_SIZE,
    REQUESTS_PER_SECOND_WITH_KEY,
    REQUESTS_PER_SECOND_WITHOUT_KEY,
)
from src.db import get_connection, init_db
from src.search_strategy import get_query_domains
from src.utils import chunked, clean_text, setup_logging, utc_now

LOGGER = setup_logging(__name__)
ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


def _request_delay() -> float:
    rate = REQUESTS_PER_SECOND_WITH_KEY if NCBI_API_KEY else REQUESTS_PER_SECOND_WITHOUT_KEY
    return 1.0 / rate


def _base_params() -> dict[str, str]:
    params = {"tool": NCBI_TOOL}
    if NCBI_EMAIL:
        params["email"] = NCBI_EMAIL
    if NCBI_API_KEY:
        params["api_key"] = NCBI_API_KEY
    return params


@retry(wait=wait_exponential(multiplier=1, min=1, max=30), stop=stop_after_attempt(5))
def _get(url: str, params: dict[str, Any]) -> requests.Response:
    time.sleep(_request_delay())
    response = requests.get(url, params=params, timeout=45)
    response.raise_for_status()
    return response


def search_pmids(query: str, retmax: int) -> tuple[list[str], int]:
    """Search PubMed and return PMIDs plus the total query count."""

    params = {
        **_base_params(),
        "db": "pubmed",
        "term": query,
        "retmode": "json",
        "retmax": retmax,
        "sort": "relevance",
    }
    payload = _get(ESEARCH_URL, params).json()
    result = payload.get("esearchresult", {})
    pmids = [str(pmid) for pmid in result.get("idlist", [])]
    count = int(result.get("count", 0))
    return pmids, count


def _text(element: ET.Element | None) -> str:
    if element is None:
        return ""
    return clean_text("".join(element.itertext()))


def _abstract_parts(article: ET.Element) -> tuple[str, str]:
    parts = []
    conclusion_parts = []
    for node in article.findall(".//Abstract/AbstractText"):
        label = node.attrib.get("Label")
        text = _text(node)
        if not text:
            continue
        parts.append(f"{label}: {text}" if label else text)
        if label and label.strip().lower() in {"conclusion", "conclusions"}:
            conclusion_parts.append(text)
    return clean_text(" ".join(parts)), clean_text(" ".join(conclusion_parts))


def _authors(article: ET.Element) -> str:
    names = []
    for author in article.findall(".//AuthorList/Author"):
        collective = _text(author.find("CollectiveName"))
        if collective:
            names.append(collective)
            continue
        last = _text(author.find("LastName"))
        initials = _text(author.find("Initials"))
        full = clean_text(f"{last} {initials}")
        if full:
            names.append(full)
    return "; ".join(names)


def _mesh_terms(article: ET.Element) -> str:
    terms = []
    for descriptor in article.findall(".//MeshHeading/DescriptorName"):
        term = _text(descriptor)
        if term:
            terms.append(term)
    return "; ".join(terms)


def _doi(article: ET.Element) -> str:
    for article_id in article.findall(".//PubmedData/ArticleIdList/ArticleId"):
        if article_id.attrib.get("IdType") == "doi":
            return _text(article_id)
    for article_id in article.findall(".//ELocationID"):
        if article_id.attrib.get("EIdType") == "doi":
            return _text(article_id)
    return ""


def _publication_date(article: ET.Element) -> tuple[int | None, str]:
    pub_date = article.find(".//JournalIssue/PubDate")
    if pub_date is None:
        return None, ""
    year_text = _text(pub_date.find("Year")) or _text(pub_date.find("MedlineDate"))[:4]
    year = int(year_text) if year_text.isdigit() else None
    month = _text(pub_date.find("Month"))
    day = _text(pub_date.find("Day"))
    date = "-".join(part for part in [year_text, month, day] if part)
    return year, date


def parse_pubmed_xml(xml_text: str, query_source: str) -> list[dict[str, Any]]:
    """Parse PubMed efetch XML into paper dictionaries."""

    root = ET.fromstring(xml_text)
    papers = []
    for article in root.findall(".//PubmedArticle"):
        pmid = _text(article.find(".//MedlineCitation/PMID"))
        if not pmid:
            continue
        year, pub_date = _publication_date(article)
        abstract, abstract_conclusion = _abstract_parts(article)
        papers.append(
            {
                "pmid": pmid,
                "title": _text(article.find(".//ArticleTitle")),
                "abstract": abstract,
                "abstract_conclusion_text": abstract_conclusion or "not reported in abstract",
                "journal": _text(article.find(".//Journal/Title")),
                "publication_year": year,
                "publication_date": pub_date,
                "authors": _authors(article),
                "mesh_terms": _mesh_terms(article),
                "doi": _doi(article),
                "pubmed_url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                "source": "pubmed",
                "query_source": query_source,
            }
        )
    return papers


def fetch_papers(pmids: list[str], query_source: str) -> list[dict[str, Any]]:
    """Fetch PubMed records for a list of PMIDs."""

    all_papers: list[dict[str, Any]] = []
    for batch in tqdm(list(chunked(pmids, PUBMED_FETCH_BATCH_SIZE)), desc="Fetching PubMed records"):
        params = {
            **_base_params(),
            "db": "pubmed",
            "id": ",".join(batch),
            "retmode": "xml",
        }
        response = _get(EFETCH_URL, params)
        all_papers.extend(parse_pubmed_xml(response.text, query_source))
    return all_papers


def store_paper(paper: dict[str, Any]) -> bool:
    """Insert or ignore one PubMed paper and checkpoint extraction status."""

    now = utc_now()
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT OR IGNORE INTO papers (
                pmid, title, abstract, journal, publication_year, publication_date,
                abstract_conclusion_text, authors, mesh_terms, doi, pubmed_url, source, query_source,
                created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                paper["pmid"],
                paper["title"],
                paper["abstract"],
                paper["journal"],
                paper["publication_year"],
                paper["publication_date"],
                paper.get("abstract_conclusion_text"),
                paper["authors"],
                paper["mesh_terms"],
                paper["doi"],
                paper["pubmed_url"],
                paper["source"],
                paper["query_source"],
                now,
                now,
            ),
        )
        conn.execute(
            """
            INSERT INTO extraction_status (pmid, status, attempts, updated_at)
            VALUES (?, 'pending', 0, ?)
            ON CONFLICT(pmid) DO UPDATE SET updated_at = excluded.updated_at
            """,
            (paper["pmid"], now),
        )
        return cur.rowcount > 0


def log_query(domain: dict[str, str], result_count: int) -> None:
    """Record a PubMed query."""

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO query_log (query_domain, query_name, query_text, result_count, run_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (domain["key"], domain["name"], domain["query"], result_count, utc_now()),
        )


def collect_pubmed(max_papers: int, query_domain: str | None = None, dry_run: bool = False) -> int:
    """Collect PubMed papers into SQLite and return newly inserted count."""

    init_db()
    domains = get_query_domains(query_domain)
    per_domain = max(max_papers if query_domain else max_papers // len(domains) + 25, 25)
    seen: set[str] = set()
    domain_hits: dict[str, list[str]] = {}

    for domain in domains:
        if len(seen) >= max_papers and not dry_run:
            break
        remaining = max(max_papers - len(seen), 0)
        retmax = per_domain if not query_domain else max_papers
        if not dry_run:
            retmax = min(max(retmax, remaining), max_papers)
        pmids, count = search_pmids(domain["query"], retmax=retmax)
        log_query(domain, count)
        unique_pmids = [pmid for pmid in pmids if pmid not in seen]
        seen.update(unique_pmids)
        domain_hits[domain["key"]] = unique_pmids
        LOGGER.info("%s: %s total results, %s unique queued", domain["key"], count, len(unique_pmids))
        if dry_run:
            continue

    if dry_run:
        print(json.dumps({key: len(value) for key, value in domain_hits.items()}, indent=2))
        return 0

    inserted = 0
    selected = list(seen)[:max_papers]
    # Preserve each paper's first matching domain as query_source.
    query_lookup = {
        pmid: key
        for key, pmids in domain_hits.items()
        for pmid in pmids
        if pmid in selected
    }
    for batch in chunked(selected, PUBMED_FETCH_BATCH_SIZE):
        query_source = ",".join(sorted({query_lookup.get(pmid, "unknown") for pmid in batch}))
        for paper in fetch_papers(list(batch), query_source=query_source):
            if store_paper(paper):
                inserted += 1
    LOGGER.info("Inserted %s new papers", inserted)
    return inserted


def _publication_year_query(query: str, year: int) -> str:
    """Restrict a PubMed query to a single publication year."""

    return f'({query}) AND ("{year}/01/01"[Date - Publication] : "{year}/12/31"[Date - Publication])'


def collect_pubmed_core_by_year(
    start_year: int = 1900,
    end_year: int | None = None,
    retmax_per_year: int = 9999,
    dry_run: bool = False,
) -> int:
    """Collect the broad core query year by year to avoid PubMed's broad-query cap."""

    init_db()
    end_year = end_year or datetime.now().year
    core_domain = get_query_domains("core")[0]
    inserted = 0

    for year in range(end_year, start_year - 1, -1):
        year_domain = dict(core_domain)
        year_domain["key"] = f"core_{year}"
        year_domain["name"] = f"{core_domain['name']} ({year})"
        year_domain["query"] = _publication_year_query(core_domain["query"], year)
        pmids, count = search_pmids(year_domain["query"], retmax=retmax_per_year)
        log_query(year_domain, count)
        LOGGER.info("%s: %s total results, %s queued", year_domain["key"], count, len(pmids))
        if dry_run:
            continue
        for batch in chunked(pmids, PUBMED_FETCH_BATCH_SIZE):
            for paper in fetch_papers(list(batch), query_source=year_domain["key"]):
                if store_paper(paper):
                    inserted += 1

    LOGGER.info("Inserted %s new year-split core papers", inserted)
    return inserted
