"""Scraper for company press release pages."""

from __future__ import annotations

import logging
import time

import httpx
from bs4 import BeautifulSoup

from src.utils import confidence
from src.parsing import capex as capex_ext
from src.parsing import capacity as capacity_ext
from src.parsing import location as location_ext
from src.models.investment_record import InvestmentRecord

logger = logging.getLogger(__name__)


def scrape(config: dict) -> list[InvestmentRecord]:
    records = []
    source_quality: float = config.get("source_quality", 1.0)
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
                record = _parse_article(url, source_quality)
                if record:
                    records.append(record)
            except Exception:
                logger.exception("Failed to parse article: %s", url)

    return records


def _discover_articles(seed_url: str) -> list[str]:
    """Return a list of article URLs found on a seed page."""
    response = httpx.get(seed_url, follow_redirects=True, timeout=15)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    # Heuristic: collect <a> tags that look like press release links.
    # Adapt per source as needed.
    links = []
    for a in soup.find_all("a", href=True):
        href: str = a["href"]
        if any(kw in href.lower() for kw in ("press", "news", "investor", "media")):
            if href.startswith("http"):
                links.append(href)
            else:
                from urllib.parse import urljoin
                links.append(urljoin(seed_url, href))
    return list(dict.fromkeys(links))  # dedupe, preserve order


def _parse_article(url: str, source_quality: float) -> InvestmentRecord | None:
    response = httpx.get(url, follow_redirects=True, timeout=15)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    text = soup.get_text(separator=" ", strip=True)

    capex_res = capex_ext.extract(text)
    cap_res = capacity_ext.extract(text)
    loc_res = location_ext.extract(text)

    if not loc_res.value:
        return None

    year = _extract_year(text)
    company = _extract_company(soup)

    if not company or not year:
        return None

    record = InvestmentRecord(
        company=company,
        location=loc_res.value,
        country=loc_res.country,
        year=year,
        source_url=url,
        confidence_score=0.0,  # filled below
        capex=capex_res.value,
        capacity=cap_res.value,
    )
    extraction_certainty = (capex_res.certainty + cap_res.certainty + loc_res.certainty) / 3
    record.confidence_score = confidence.score(record, source_quality, extraction_certainty)
    return record


def _extract_year(text: str) -> int | None:
    import re
    matches = re.findall(r"\b(20[2-9]\d)\b", text)
    return int(matches[0]) if matches else None


def _extract_company(soup: BeautifulSoup) -> str | None:
    # Try <meta name="author">, then <title>, then og:site_name
    for meta in soup.find_all("meta"):
        if meta.get("name") in ("author", "og:site_name") or meta.get("property") == "og:site_name":
            content = meta.get("content", "").strip()
            if content:
                return content
    title = soup.find("title")
    if title:
        # "Press Release | Company Name" → take last segment
        parts = [p.strip() for p in title.text.replace("–", "|").replace("—", "|").split("|")]
        if len(parts) > 1:
            return parts[-1]
    return None
