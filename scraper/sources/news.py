"""Scraper for news articles about factory investments."""

from __future__ import annotations

import logging
import time

import httpx
import trafilatura

from scraper import confidence
from scraper.extractors import capex as capex_ext
from scraper.extractors import capacity as capacity_ext
from scraper.extractors import location as location_ext
from scraper.models import InvestmentRecord

logger = logging.getLogger(__name__)


def scrape(config: dict) -> list[InvestmentRecord]:
    records = []
    source_quality: float = config.get("source_quality", 0.7)
    delay = 1.0 / config.get("rate_limit_rps", 1.0)

    for seed_url in config["seed_urls"]:
        try:
            article_urls = _discover_articles(seed_url)
        except Exception:
            logger.exception("Failed to discover articles at %s", seed_url)
            continue

        for url in article_urls:
            time.sleep(delay)
            try:
                record = _parse_article(url, source_quality)
                if record:
                    records.append(record)
            except Exception:
                logger.exception("Failed to parse news article: %s", url)

    return records


def _discover_articles(seed_url: str) -> list[str]:
    from bs4 import BeautifulSoup
    from urllib.parse import urljoin

    response = httpx.get(seed_url, follow_redirects=True, timeout=15)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    links = []
    for a in soup.find_all("a", href=True):
        href: str = a["href"]
        if href.startswith("http"):
            links.append(href)
        else:
            links.append(urljoin(seed_url, href))
    return list(dict.fromkeys(links))


def _parse_article(url: str, source_quality: float) -> InvestmentRecord | None:
    import re

    response = httpx.get(url, follow_redirects=True, timeout=15)
    response.raise_for_status()

    # trafilatura strips boilerplate better than raw BeautifulSoup on news pages
    text = trafilatura.extract(response.text) or ""
    if not text:
        return None

    # Only process articles that mention investment-related keywords
    if not re.search(r"\b(investering|fabriek|plant|capex|milieu|capaciteit)\b", text, re.I):
        return None

    capex_value, capex_certainty = capex_ext.extract(text)
    cap_value, cap_certainty = capacity_ext.extract(text)
    loc_value, country, loc_certainty = location_ext.extract(text)

    if not loc_value:
        return None

    year_matches = re.findall(r"\b(20[2-9]\d)\b", text)
    if not year_matches:
        return None

    company = _extract_company_from_text(text)
    if not company:
        return None

    record = InvestmentRecord(
        company=company,
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
    return record


def _extract_company_from_text(text: str) -> str | None:
    """Naive heuristic: capitalised words before 'investeert' or 'bouwt'."""
    import re
    match = re.search(r"([A-Z][A-Za-z]+(?: [A-Z][A-Za-z]+)*)\s+(?:investeert|bouwt|opent|kondigt aan)", text)
    if match:
        return match.group(1)
    return None
