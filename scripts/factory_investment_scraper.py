"""
Main pipeline: fetch → parse → write interim JSON → score → deduplicate → write CSV.

Usage:
    python scripts/factory_investment_scraper.py
    python scripts/factory_investment_scraper.py --source press_releases
    python scripts/factory_investment_scraper.py --output data/processed/investments.csv
    python scripts/factory_investment_scraper.py --no-interim
"""

from __future__ import annotations

import argparse
import csv
import importlib
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.investment_record import InvestmentRecord
from src.models.parsed_page import ParsedPage

logger = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).parent.parent / "config" / "sources.yaml"
DEFAULT_OUTPUT = Path(__file__).parent.parent / "data" / "processed" / "investments.csv"
DEFAULT_INTERIM = Path(__file__).parent.parent / "data" / "interim"


def load_config(path: Path = CONFIG_PATH) -> dict:
    with path.open() as f:
        return yaml.safe_load(f)


def run(
    source_filter: str | None = None,
    output: Path = DEFAULT_OUTPUT,
    interim_dir: Path | None = DEFAULT_INTERIM,
) -> None:
    config = load_config()
    all_pages: list[ParsedPage] = []

    for source_cfg in config["sources"]:
        name = source_cfg["name"]
        source_type = source_cfg["type"]

        if source_filter and source_type != source_filter:
            continue

        logger.info("Scraping source: %s (%s)", name, source_type)
        try:
            module = importlib.import_module(f"src.scraping.{source_type}")
            pages: list[ParsedPage] = module.scrape(source_cfg)
            logger.info("  → %d pages from %s", len(pages), name)
            all_pages.extend(pages)
        except Exception:
            logger.exception("Failed to scrape source: %s", name)

    if interim_dir is not None:
        write_interim(all_pages, interim_dir)

    records = [r for p in all_pages if (r := p.to_investment_record())]
    records = deduplicate(records)
    write_csv(records, output)
    logger.info(
        "Wrote %d records (from %d pages) to %s",
        len(records),
        len(all_pages),
        output,
    )


def write_interim(pages: list[ParsedPage], interim_dir: Path) -> None:
    """Write all ParsedPages as NDJSON for debugging low-confidence records."""
    if not pages:
        return
    interim_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = interim_dir / f"{timestamp}.ndjson"
    with path.open("w", encoding="utf-8") as f:
        for page in pages:
            f.write(json.dumps(page.to_dict(), ensure_ascii=False) + "\n")
    logger.info("Wrote %d interim pages to %s", len(pages), path)


def deduplicate(records: list[InvestmentRecord]) -> list[InvestmentRecord]:
    """Keep the record with the highest confidence score per dedup key."""
    best: dict[tuple, InvestmentRecord] = {}
    for r in records:
        key = r.dedup_key
        if key not in best or r.confidence_score > best[key].confidence_score:
            best[key] = r
    return sorted(best.values(), key=lambda r: (r.country, r.company, r.year))


def write_csv(records: list[InvestmentRecord], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=InvestmentRecord.CSV_FIELDS)
        writer.writeheader()
        for r in records:
            writer.writerow(r.to_csv_row())


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Run the investment scraper pipeline.")
    parser.add_argument("--source", help="Only run sources of this type")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--no-interim",
        action="store_true",
        help="Skip writing interim NDJSON files",
    )
    args = parser.parse_args()
    run(
        source_filter=args.source,
        output=args.output,
        interim_dir=None if args.no_interim else DEFAULT_INTERIM,
    )
