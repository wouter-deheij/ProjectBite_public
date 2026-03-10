"""Scraper for government investment registers."""

from __future__ import annotations

import logging
import time

import httpx
from bs4 import BeautifulSoup

from src.models.investment_record import InvestmentRecord
from src.parsing.record_parser import RecordParser

logger = logging.getLogger(__name__)
_parser = RecordParser()


def scrape(config: dict) -> list[InvestmentRecord]:
    records = []
    delay = 1.0 / config.get("rate_limit_rps", 0.5)

    for seed_url in config["seed_urls"]:
        time.sleep(delay)
        try:
            page_records = _scrape_register_page(seed_url, config)
            records.extend(page_records)
        except Exception:
            logger.exception("Failed to scrape government register: %s", seed_url)

    return records


def _scrape_register_page(url: str, config: dict) -> list[InvestmentRecord]:
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
        page = _parser.parse(text, url, config)
        record = page.to_investment_record()
        if record:
            records.append(record)

    return records
