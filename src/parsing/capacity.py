"""Extract production capacity strings from free text.

Capacity is kept as a raw string (e.g. "500.000 ton/jaar") because
units vary too much across industries to normalize reliably.
"""

from __future__ import annotations

import re

_PATTERNS = [
    # e.g. "500.000 ton per jaar", "1,2 GW", "200 MW", "50.000 m3/dag"
    r"([\d.,]+(?:\s*[\d.,]+)?)\s*(ton|tonne|mt|kt|gt|MW|GW|kWh|MWh|GWh|m3|m³|liter|l)\s*(?:per\s+(?:jaar|dag|uur|year|day)|/(?:jaar|dag|uur|year|day|j|d|h|yr))?",
    r"(?:capaciteit|capacity|output)\s+(?:van\s+)?([\d.,]+)\s*([\w/]+)",
]


def extract(text: str) -> tuple[str | None, float]:
    """Return (capacity_string, certainty).

    certainty is 1.0 for exact regex match, 0.0 if not found.
    """
    for pattern in _PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            raw = match.group(0).strip()
            return raw, 1.0

    return None, 0.0
