"""Central parser: text + optional HTML → ParsedPage.

All extraction logic lives here so that scraping modules are purely
responsible for fetching HTML and discovering URLs.

Usage:
    parser = RecordParser()
    page = parser.parse(text, url, source_cfg, soup=soup)
    record = page.to_investment_record()  # None if required fields missing
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from src.models.extraction_result import ExtractionResult
from src.models.parsed_page import ParsedPage
from src.parsing import capex as capex_ext
from src.parsing import capacity as capacity_ext
from src.parsing import location as location_ext
from src.utils import confidence

if TYPE_CHECKING:
    from bs4 import BeautifulSoup


class RecordParser:
    def parse(
        self,
        text: str,
        source_url: str,
        source_cfg: dict,
        soup: BeautifulSoup | None = None,
    ) -> ParsedPage:
        """Extract all fields from page text and return a ParsedPage."""
        capex_res = capex_ext.extract(text)
        cap_res = capacity_ext.extract(text)
        loc_res = location_ext.extract(text)
        year_res = self._extract_year(text)
        company_res = self._extract_company(text, soup)

        source_quality: float = source_cfg.get("source_quality", 1.0)
        extraction_certainty = (
            capex_res.certainty
            + cap_res.certainty
            + loc_res.certainty
            + year_res.certainty
            + company_res.certainty
        ) / 5

        # Build a temporary record for the confidence scorer
        from src.models.investment_record import InvestmentRecord
        tmp = InvestmentRecord(
            company=company_res.value or "",
            location=loc_res.value or "",
            country=loc_res.country,
            year=int(year_res.value) if year_res.value else 0,
            source_url=source_url,
            confidence_score=0.0,
            capex=capex_res.value,
            capacity=cap_res.value,
        )
        conf = confidence.score(tmp, source_quality, extraction_certainty)

        return ParsedPage(
            source_url=source_url,
            source_name=source_cfg.get("name", ""),
            source_quality=source_quality,
            parsed_at=datetime.now(timezone.utc).isoformat(),
            company=company_res,
            capex=capex_res,
            capacity=cap_res,
            location=loc_res,
            year=year_res,
            confidence_score=conf,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _extract_year(self, text: str) -> ExtractionResult:
        match = re.search(r"\b(20[2-9]\d)\b", text)
        if match:
            return ExtractionResult(
                value=int(match.group(1)),
                raw_match=match.group(0),
                certainty=1.0,
                method="regex_year",
            )
        return ExtractionResult(value=None, raw_match=None, certainty=0.0, method="not_found")

    def _extract_company(
        self, text: str, soup: BeautifulSoup | None
    ) -> ExtractionResult:
        # 1. HTML meta tags (most reliable — press releases)
        if soup:
            for meta in soup.find_all("meta"):
                if meta.get("name") in ("author",) or meta.get("property") == "og:site_name":
                    content = meta.get("content", "").strip()
                    if content:
                        return ExtractionResult(
                            value=content,
                            raw_match=content,
                            certainty=0.9,
                            method="html_meta",
                        )
            title = soup.find("title")
            if title:
                parts = [
                    p.strip()
                    for p in title.text.replace("–", "|").replace("—", "|").split("|")
                ]
                if len(parts) > 1:
                    company = parts[-1]
                    return ExtractionResult(
                        value=company,
                        raw_match=title.text,
                        certainty=0.7,
                        method="html_title",
                    )

        # 2. Text heuristic: capitalised words before investment verb (news)
        match = re.search(
            r"([A-Z][A-Za-z]+(?: [A-Z][A-Za-z]+)*)\s+"
            r"(?:investeert|bouwt|opent|kondigt aan|announces?|invests?|opens?)",
            text,
        )
        if match:
            return ExtractionResult(
                value=match.group(1),
                raw_match=match.group(0),
                certainty=0.6,
                method="regex_verb_preceding",
            )

        return ExtractionResult(value=None, raw_match=None, certainty=0.0, method="not_found")
