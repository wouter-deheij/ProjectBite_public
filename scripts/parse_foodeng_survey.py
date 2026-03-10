"""
One-off parser for the Food Engineering 2021 Plant Construction Survey.

URL: https://www.foodengineeringmag.com/food-plant-construction-survey-list-2021

The page contains a single HTML table with columns:
  Company | City | State | Product | Type | Sq-Ft (x1000) | Cost ($M) | Firm | Date

Output columns (via InvestmentRecord):
  company, location, country, year,
  capex (USD M), currency, capex_2025_eur (EUR M, CPI-adjusted),
  capacity, facility_size_m2,
  source_url, confidence_score

Usage:
    python scripts/parse_foodeng_survey.py
    python scripts/parse_foodeng_survey.py --output data/processed/foodeng_2021.csv
    python scripts/parse_foodeng_survey.py --min-cost 50
"""

from __future__ import annotations

import argparse
import csv
import logging
import re
import sys
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.investment_record import InvestmentRecord
from src.utils import confidence
from src.utils.inflation import is_plausible_capex, sqft_to_m2, to_2025_eur

logger = logging.getLogger(__name__)

URL = "https://www.foodengineeringmag.com/food-plant-construction-survey-list-2021"
DEFAULT_OUTPUT = Path(__file__).parent.parent / "data" / "processed" / "foodeng_2021.csv"
SOURCE_CURRENCY = "USD"

_STATE = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
    "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
    "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
    "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming",
    "ON": "Ontario", "BC": "British Columbia", "AB": "Alberta", "QC": "Quebec",
    "SK": "Saskatchewan", "MB": "Manitoba",
}

_CA_PROVINCES = {"ON", "BC", "AB", "QC", "SK", "MB", "NS", "NB", "NL", "PE"}


def _parse_year(date_str: str) -> int | None:
    date_str = date_str.strip()
    m = re.search(r"\b(20\d{2})\b", date_str)
    if m:
        return int(m.group(1))
    m = re.search(r"\d+/(\d{2})$", date_str)
    if m:
        return 2000 + int(m.group(1))
    m = re.match(r"^(\d{2})$", date_str)
    if m:
        return 2000 + int(m.group(1))
    return None


def _parse_cost(cost_str: str) -> float | None:
    try:
        return float(cost_str.strip().replace(",", ""))
    except ValueError:
        return None


def _country(state: str) -> str:
    return "CA" if state in _CA_PROVINCES else "US"


def fetch_and_parse(min_cost: float = 0.0) -> list[InvestmentRecord]:
    logger.info("Fetching %s", URL)
    response = httpx.get(URL, follow_redirects=True, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    table = soup.select_one("table")
    if not table:
        raise RuntimeError("No table found on page")

    records = []
    skipped: dict[str, int] = {"short_row": 0, "no_year": 0, "implausible_capex": 0, "below_min_cost": 0}

    for row in table.select("tbody tr"):
        cells = [td.get_text(strip=True) for td in row.find_all("td")]
        if len(cells) < 9:
            skipped["short_row"] += 1
            continue

        company, city, state, _product, _type, sqft_raw, cost_raw, _firm, date_raw = cells[:9]

        year = _parse_year(date_raw)
        if not year:
            skipped["no_year"] += 1
            continue

        cost = _parse_cost(cost_raw)

        if cost is not None:
            if not is_plausible_capex(cost):
                logger.debug("Implausible capex %.2f for %s — skipping", cost, company)
                skipped["implausible_capex"] += 1
                continue
            if cost < min_cost:
                skipped["below_min_cost"] += 1
                continue

        location = f"{city}, {_STATE.get(state, state)}" if city else state
        country = _country(state)

        facility_m2: float | None = None
        try:
            sqft_k = float(sqft_raw.replace(",", ""))
            facility_m2 = sqft_to_m2(sqft_k * 1000)
        except (ValueError, TypeError):
            pass

        capex_2025_eur = to_2025_eur(cost, year, SOURCE_CURRENCY) if cost else None

        record = InvestmentRecord(
            company=company,
            location=location,
            country=country,
            year=year,
            source_url=URL,
            confidence_score=0.0,
            capex=cost,
            currency=SOURCE_CURRENCY if cost is not None else None,
            capex_2025_eur=capex_2025_eur,
            capacity=None,
            facility_size_m2=facility_m2,
        )
        record.confidence_score = confidence.score(record, source_quality=0.7, extraction_certainty=0.95)
        records.append(record)

    logger.info(
        "Parsed %d records | skipped: %s",
        len(records),
        ", ".join(f"{k}={v}" for k, v in skipped.items() if v),
    )
    return records


def write_csv(records: list[InvestmentRecord], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=InvestmentRecord.CSV_FIELDS)
        writer.writeheader()
        for r in records:
            writer.writerow(r.to_csv_row())
    logger.info("Wrote %d records to %s", len(records), path)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Parse Food Engineering 2021 survey.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--min-cost", type=float, default=0.0,
        help="Minimum capex in USD millions to include (default: 0)",
    )
    args = parser.parse_args()

    records = fetch_and_parse(min_cost=args.min_cost)
    write_csv(records, args.output)
