"""Extract CapEx values from free text and normalize to EUR millions."""

from __future__ import annotations

import re

# Patterns: e.g. "€ 1,2 miljard", "EUR 500 million", "500 mln euro", "$2B"
_PATTERNS = [
    # Dutch: € 1,2 miljard / 500 miljoen euro
    (r"(?:€|EUR|euro)\s*([\d.,]+)\s*(mrd|miljard|mln|miljoen)", "nl"),
    (r"([\d.,]+)\s*(mrd|miljard|mln|miljoen)\s*(?:€|EUR|euro)", "nl"),
    # English: €1.2 billion / EUR 500 million / $2B
    (r"(?:€|EUR|\$|USD)\s*([\d.,]+)\s*(billion|bn|million|mln|B|M)\b", "en"),
    (r"([\d.,]+)\s*(billion|bn|million|mln|B|M)\s*(?:€|EUR|\$|USD)\b", "en"),
]

_NL_MULTIPLIERS = {
    "mrd": 1_000, "miljard": 1_000,
    "mln": 1, "miljoen": 1,
}
_EN_MULTIPLIERS = {
    "billion": 1_000, "bn": 1_000, "B": 1_000,
    "million": 1, "mln": 1, "M": 1,
}


def extract(text: str) -> tuple[float | None, float]:
    """Return (value_in_eur_millions, certainty).

    certainty is 1.0 for exact regex match, 0.0 if not found.
    """
    for pattern, lang in _PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            raw, unit = match.group(1), match.group(2).lower()
            value = _parse_number(raw)
            multipliers = _NL_MULTIPLIERS if lang == "nl" else _EN_MULTIPLIERS
            multiplier = multipliers.get(unit, 1)
            return round(value * multiplier, 2), 1.0

    return None, 0.0


def _parse_number(raw: str) -> float:
    # Handle both "1.200,50" (NL) and "1,200.50" (EN)
    raw = raw.strip()
    if "," in raw and "." in raw:
        if raw.index(",") < raw.index("."):
            raw = raw.replace(",", "")  # EN: 1,200.50
        else:
            raw = raw.replace(".", "").replace(",", ".")  # NL: 1.200,50
    elif "," in raw:
        raw = raw.replace(",", ".")  # NL decimal: 1,2
    return float(raw)
