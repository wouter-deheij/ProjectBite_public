"""Scraper for news articles about factory investments."""

from __future__ import annotations

import logging
import re
import time
from urllib.parse import urljoin

import httpx
import trafilatura
from bs4 import BeautifulSoup

from src.models.parsed_page import ParsedPage
from src.parsing.record_parser import RecordParser

logger = logging.getLogger(__name__)
_parser = RecordParser()

_INVESTMENT_KEYWORDS = re.compile(
    r"\b(investering|fabriek|plant|capex|milieu|capaciteit)\b", re.I
)


def scrape(config: dict) -> list[ParsedPage]:
    pages = []
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
                page = _parse_article(url, config)
                if page:
                    pages.append(page)
            except Exception:
                logger.exception("Failed to parse news article: %s", url)

    return pages


def _discover_articles(seed_url: str) -> list[str]:
    response = httpx.get(seed_url, follow_redirects=True, timeout=15)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    links = []
    for a in soup.find_all("a", href=True):
        href: str = a["href"]
        links.append(href if href.startswith("http") else urljoin(seed_url, href))
    return list(dict.fromkeys(links))


def _parse_article(url: str, config: dict) -> ParsedPage | None:
    response = httpx.get(url, follow_redirects=True, timeout=15)
    response.raise_for_status()

    # trafilatura strips boilerplate better than raw BeautifulSoup on news pages
    text = trafilatura.extract(response.text) or ""
    if not text or not _INVESTMENT_KEYWORDS.search(text):
        return None

    return _parser.parse(text, url, config)
