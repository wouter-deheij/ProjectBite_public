"""Scraper for government investment registers."""

from __future__ import annotations

import logging
import time

import httpx
from bs4 import BeautifulSoup

from scraper import confidence
from scraper.extractors import capex as capex_ext
from scraper.extractors import capacity as capacity_ext
from scraper.extractors import location as location_ext
from scraper.models import InvestmentRecord

logger = logging.getLogger(__name__)


def scrape(config: dict) -> list[InvestmentRecord]:
    records = []
    source_quality: float = config.get("source_quality", 0.9)
    delay = 1.0 / config.get("rate_limit_rps", 0.5)

    for seed_url in config["seed_urls"]:
        time.sleep(delay)
        try:
            page_records = _scrape_register_page(seed_url, source_quality)
            records.extend(page_records)
        except Exception:
            logger.exception("Failed to scrape government register: %s", seed_url)

    return records


def _scrape_register_page(url: str, source_quality: float) -> list[InvestmentRecord]:
    response = httpx.get(url, follow_redirects=True, timeout=15)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    # Government registers often expose data in tables.
    # This is a generic fallback; adapt selectors per source.
    records = []
    for row in soup.select("table tbody tr"):
        cells = [td.get_text(strip=True) for td in row.find_all("td")]
        if len(cells) < 3:
            continue

        text = " ".join(cells)
        capex_value, capex_certainty = capex_ext.extract(text)
        cap_value, cap_certainty = capacity_ext.extract(text)
        loc_value, country, loc_certainty = location_ext.extract(text)

        if not loc_value:
            continue

        import re
        year_matches = re.findall(r"\b(20[2-9]\d)\b", text)
        if not year_matches:
            continue

        record = InvestmentRecord(
            company=cells[0],
            location=loc_value,
            country=country,
            year=int(year_matches[0]),
            source_url=url,
            confidence_score=0.0,
            capex=capex_value,
            capacity=cap_value,
        )
        extraction_certainty = (capex_certainty + cap_certainty + loc_certainty) / 3
        record.confidence_score = confidence.score(record, source_quality, extraction_certainty)
        records.append(record)

    return records
