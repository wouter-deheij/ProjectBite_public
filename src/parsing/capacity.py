"""Extract production capacity strings from free text.

Capacity is kept as a raw string (e.g. "500.000 ton/jaar") because
units vary too much across industries to normalize reliably.
"""

from __future__ import annotations

import re

from src.models.extraction_result import ExtractionResult

_PATTERNS = [
    # e.g. "500.000 ton per jaar", "1,2 GW", "200 MW", "50.000 m3/dag"
    (r"([\d.,]+(?:\s*[\d.,]+)?)\s*(ton|tonne|mt|kt|gt|MW|GW|kWh|MWh|GWh|m3|m³|liter|l)\s*(?:per\s+(?:jaar|dag|uur|year|day)|/(?:jaar|dag|uur|year|day|j|d|h|yr))?", "regex_unit"),
    (r"(?:capaciteit|capacity|output)\s+(?:van\s+)?([\d.,]+)\s*([\w/]+)", "regex_capacity_keyword"),
]


def extract(text: str) -> ExtractionResult:
    """Return an ExtractionResult with the raw capacity string as value."""
    for pattern, method in _PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            raw = match.group(0).strip()
            return ExtractionResult(
                value=raw,
                raw_match=raw,
                certainty=1.0,
                method=method,
            )

    return ExtractionResult(value=None, raw_match=None, certainty=0.0, method="not_found")
