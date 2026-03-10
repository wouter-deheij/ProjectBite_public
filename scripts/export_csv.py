"""
Export investment records to CSV with optional filters.

Usage:
    python scripts/export_csv.py
    python scripts/export_csv.py --country NL
    python scripts/export_csv.py --country NL --min-year 2022 --min-confidence 0.7
    python scripts/export_csv.py --output data/processed/nl_investments.csv
"""

from __future__ import annotations

import argparse
import csv
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.investment_record import InvestmentRecord

logger = logging.getLogger(__name__)

DEFAULT_INPUT = Path(__file__).parent.parent / "data" / "processed" / "investments_clean.csv"
DEFAULT_OUTPUT = Path(__file__).parent.parent / "data" / "processed" / "export.csv"


def export(
    input_path: Path = DEFAULT_INPUT,
    output_path: Path = DEFAULT_OUTPUT,
    country: str | None = None,
    min_year: int | None = None,
    min_confidence: float = 0.0,
) -> None:
    rows = _read_csv(input_path)
    filtered = _filter(rows, country=country, min_year=min_year, min_confidence=min_confidence)
    _write_csv(filtered, output_path)
    logger.info(
        "Exported %d/%d records to %s (country=%s, min_year=%s, min_confidence=%s)",
        len(filtered), len(rows), output_path, country, min_year, min_confidence,
    )


def _read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _filter(
    rows: list[dict],
    country: str | None,
    min_year: int | None,
    min_confidence: float,
) -> list[dict]:
    result = []
    for row in rows:
        if country and row.get("country", "").upper() != country.upper():
            continue
        if min_year:
            try:
                if int(row.get("year", 0)) < min_year:
                    continue
            except ValueError:
                continue
        try:
            if float(row.get("confidence_score", 0)) < min_confidence:
                continue
        except ValueError:
            continue
        result.append(row)
    return result


def _write_csv(rows: list[dict], path: Path) -> None:
    if not rows:
        logger.warning("No rows matched the filters")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=InvestmentRecord.CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Export investment records to filtered CSV.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--country", help="Filter by ISO 3166-1 alpha-2 country code (e.g. NL)")
    parser.add_argument("--min-year", type=int, help="Only include records from this year onwards")
    parser.add_argument("--min-confidence", type=float, default=0.0, help="Minimum confidence score (0.0–1.0)")
    args = parser.parse_args()
    export(
        input_path=args.input,
        output_path=args.output,
        country=args.country,
        min_year=args.min_year,
        min_confidence=args.min_confidence,
    )
