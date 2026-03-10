"""Scraper for company press release pages."""

from __future__ import annotations

import logging
import time
from urllib.parse import urljoin

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
        try:
            article_urls = _discover_articles(seed_url)
        except Exception:
            logger.exception("Failed to discover articles at %s", seed_url)
            continue

        for url in article_urls:
            time.sleep(delay)
            try:
                record = _fetch_and_parse(url, config)
                if record:
                    records.append(record)
            except Exception:
                logger.exception("Failed to parse article: %s", url)

    return records


def _discover_articles(seed_url: str) -> list[str]:
    response = httpx.get(seed_url, follow_redirects=True, timeout=15)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    links = []
    for a in soup.find_all("a", href=True):
        href: str = a["href"]
        if any(kw in href.lower() for kw in ("press", "news", "investor", "media")):
            links.append(href if href.startswith("http") else urljoin(seed_url, href))
    return list(dict.fromkeys(links))


def _fetch_and_parse(url: str, config: dict) -> InvestmentRecord | None:
    response = httpx.get(url, follow_redirects=True, timeout=15)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    text = soup.get_text(separator=" ", strip=True)

    page = _parser.parse(text, url, config, soup=soup)
    return page.to_investment_record()
