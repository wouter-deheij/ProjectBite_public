"""
Clean raw investment CSV: normalise company names, strip whitespace,
drop rows missing required fields.

Usage:
    python scripts/clean_factory_data.py
    python scripts/clean_factory_data.py --input data/processed/investments.csv
    python scripts/clean_factory_data.py --output data/processed/investments_clean.csv
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

REQUIRED_FIELDS = ("company", "location", "country", "year", "source_url")

DEFAULT_INPUT = Path(__file__).parent.parent / "data" / "processed" / "investments.csv"
DEFAULT_OUTPUT = Path(__file__).parent.parent / "data" / "processed" / "investments_clean.csv"


def clean(input_path: Path = DEFAULT_INPUT, output_path: Path = DEFAULT_OUTPUT) -> None:
    rows = _read_csv(input_path)
    cleaned = [_clean_row(r) for r in rows]
    valid = [r for r in cleaned if _is_valid(r)]

    dropped = len(rows) - len(valid)
    if dropped:
        logger.warning("Dropped %d rows missing required fields", dropped)

    _write_csv(valid, output_path)
    logger.info("Wrote %d clean rows to %s", len(valid), output_path)


def _read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _clean_row(row: dict) -> dict:
    return {k: v.strip() if isinstance(v, str) else v for k, v in row.items()}


def _is_valid(row: dict) -> bool:
    return all(row.get(f) for f in REQUIRED_FIELDS)


def _write_csv(rows: list[dict], path: Path) -> None:
    if not rows:
        logger.warning("No rows to write")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=InvestmentRecord.CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Clean raw investment CSV.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    clean(input_path=args.input, output_path=args.output)
