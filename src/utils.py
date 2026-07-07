"""Small shared utilities."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator, Sequence, TypeVar

from .config import LOG_DIR, ensure_directories

T = TypeVar("T")


def utc_now() -> str:
    """Return an ISO-8601 UTC timestamp."""

    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def clean_text(value: str | None) -> str:
    """Normalize whitespace while preserving content."""

    if not value:
        return ""
    return " ".join(value.split())


def parse_int(value: object) -> int | None:
    """Parse an integer if possible, otherwise return None."""

    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def chunked(items: Sequence[T], size: int) -> Iterator[Sequence[T]]:
    """Yield fixed-size chunks from a sequence."""

    for start in range(0, len(items), size):
        yield items[start : start + size]


def setup_logging(name: str = "stroke_evidence_atlas") -> logging.Logger:
    """Configure console and file logging once."""

    ensure_directories()
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    file_handler = logging.FileHandler(Path(LOG_DIR) / "pipeline.log")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


def first_nonempty(values: Iterable[str | None]) -> str:
    """Return the first non-empty cleaned string."""

    for value in values:
        cleaned = clean_text(value)
        if cleaned:
            return cleaned
    return ""
