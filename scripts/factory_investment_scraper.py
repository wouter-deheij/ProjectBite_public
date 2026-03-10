"""
Main pipeline: fetch → cache → extract → score → deduplicate → write CSV.

Usage:
    python scripts/factory_investment_scraper.py
    python scripts/factory_investment_scraper.py --source press_releases
    python scripts/factory_investment_scraper.py --output data/processed/investments.csv
"""

from __future__ import annotations

import argparse
import csv
import importlib
import logging
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.investment_record import InvestmentRecord

logger = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).parent.parent / "config" / "sources.yaml"
DEFAULT_OUTPUT = Path(__file__).parent.parent / "data" / "processed" / "investments.csv"


def load_config(path: Path = CONFIG_PATH) -> dict:
    with path.open() as f:
        return yaml.safe_load(f)


def run(source_filter: str | None = None, output: Path = DEFAULT_OUTPUT) -> None:
    config = load_config()
    records: list[InvestmentRecord] = []

    for source_cfg in config["sources"]:
        name = source_cfg["name"]
        source_type = source_cfg["type"]

        if source_filter and source_type != source_filter:
            continue

        logger.info("Scraping source: %s (%s)", name, source_type)
        try:
            module = importlib.import_module(f"src.scraping.{source_type}")
            new_records = module.scrape(source_cfg)
            logger.info("  → %d records from %s", len(new_records), name)
            records.extend(new_records)
        except Exception:
            logger.exception("Failed to scrape source: %s", name)

    records = deduplicate(records)
    write_csv(records, output)
    logger.info("Wrote %d records to %s", len(records), output)


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
    args = parser.parse_args()
    run(source_filter=args.source, output=args.output)
