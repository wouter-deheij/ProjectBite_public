"""
Parser for Food Engineering Plant Construction Survey (multi-year).

Available years: 2018–2022
URL pattern: https://www.foodengineeringmag.com/food-plant-construction-survey-list-{year}

Table columns per page:
  Company | City | State | Product | Type | Sq-Ft (x1000) | Cost ($M) | Firm | Date

Output columns (via InvestmentRecord):
  company, location, country, year,
  capex (USD M), currency, capex_2025_eur (EUR M, CPI-adjusted),
  capacity, facility_size_m2, source_url, confidence_score

Usage:
    python scripts/parse_foodeng_survey.py                        # all years
    python scripts/parse_foodeng_survey.py --years 2020 2021 2022
    python scripts/parse_foodeng_survey.py --min-cost 50
    python scripts/parse_foodeng_survey.py --output data/processed/foodeng_all.csv
"""

from __future__ import annotations

import argparse
import csv
import logging
import re
import sys
import time
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.investment_record import InvestmentRecord
from src.utils import confidence
from src.utils.inflation import is_plausible_capex, sqft_to_m2, to_2025_eur

logger = logging.getLogger(__name__)

URL_TEMPLATE = "https://www.foodengineeringmag.com/food-plant-construction-survey-list-{year}"
AVAILABLE_YEARS = [2018, 2019, 2020, 2021, 2022]
DEFAULT_OUTPUT = Path(__file__).parent.parent / "data" / "processed" / "foodeng_all.csv"
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


def fetch_and_parse_year(survey_year: int, min_cost: float = 0.0) -> list[InvestmentRecord]:
    url = URL_TEMPLATE.format(year=survey_year)
    logger.info("Fetching survey year %d: %s", survey_year, url)
    response = httpx.get(url, follow_redirects=True, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    table = soup.select_one("table")
    if not table:
        raise RuntimeError(f"No table found on page for year {survey_year}")

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
            source_url=url,
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
        "  Year %d → %d records | skipped: %s",
        survey_year,
        len(records),
        ", ".join(f"{k}={v}" for k, v in skipped.items() if v) or "none",
    )
    return records


def fetch_all_years(
    years: list[int] = AVAILABLE_YEARS,
    min_cost: float = 0.0,
) -> list[InvestmentRecord]:
    """Fetch and deduplicate records across all requested survey years."""
    all_records: list[InvestmentRecord] = []

    for i, year in enumerate(years):
        try:
            records = fetch_and_parse_year(year, min_cost=min_cost)
            all_records.extend(records)
        except Exception:
            logger.exception("Failed to parse survey year %d", year)
        if i < len(years) - 1:
            time.sleep(1)  # polite delay between pages

    # Deduplicate: same company + location + investment year → keep highest confidence
    best: dict[tuple, InvestmentRecord] = {}
    for r in all_records:
        key = r.dedup_key
        if key not in best or r.confidence_score > best[key].confidence_score:
            best[key] = r

    deduped = sorted(best.values(), key=lambda r: (r.year, r.company))
    dupes = len(all_records) - len(deduped)
    if dupes:
        logger.info("Removed %d duplicate records across survey years", dupes)
    logger.info("Total: %d unique records from %d survey pages", len(deduped), len(years))
    return deduped


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
    parser = argparse.ArgumentParser(
        description="Parse Food Engineering Plant Construction Survey (multi-year)."
    )
    parser.add_argument(
        "--years", type=int, nargs="+", default=AVAILABLE_YEARS,
        help=f"Survey years to fetch (default: {AVAILABLE_YEARS})",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--min-cost", type=float, default=0.0,
        help="Minimum capex in USD millions to include (default: 0)",
    )
    args = parser.parse_args()

    records = fetch_all_years(years=args.years, min_cost=args.min_cost)
    write_csv(records, args.output)
