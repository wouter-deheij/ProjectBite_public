"""Extract location and country from free text.

Returns a LocationExtractionResult with:
  value:   city or region string (or None)
  country: ISO 3166-1 alpha-2 code (or "XX" if unknown)
Uses a hardcoded lookup for common Dutch/English city names,
with a regex fallback for explicit country mentions.
"""

from __future__ import annotations

import re

import pycountry  # noqa: F401  (kept for future country resolution)

from src.models.extraction_result import LocationExtractionResult

# Common city → country mappings as a fast fallback
_CITY_COUNTRY: dict[str, str] = {
    "amsterdam": "NL", "rotterdam": "NL", "eindhoven": "NL", "groningen": "NL",
    "den haag": "NL", "utrecht": "NL", "tilburg": "NL", "terneuzen": "NL",
    "antwerpen": "BE", "gent": "BE", "brussel": "BE", "luik": "BE",
    "hamburg": "DE", "berlin": "DE", "münchen": "DE", "munich": "DE",
    "frankfurt": "DE", "cologne": "DE", "köln": "DE",
    "paris": "FR", "lyon": "FR", "marseille": "FR",
    "london": "GB", "manchester": "GB", "glasgow": "GB",
    "warsaw": "PL", "wroclaw": "PL", "gdansk": "PL",
}

# Patterns for explicit country mentions
_COUNTRY_PATTERN = re.compile(
    r"\b(Nederland|Netherlands|Germany|Duitsland|Belgium|Belgi[eë]|France|Frankrijk|"
    r"United Kingdom|Verenigd Koninkrijk|Poland|Polen|Spain|Spanje|Italy|Itali[eë])\b",
    re.IGNORECASE,
)

_COUNTRY_NAME_TO_ISO2: dict[str, str] = {
    "nederland": "NL", "netherlands": "NL",
    "germany": "DE", "duitsland": "DE",
    "belgium": "BE", "belgië": "BE", "belgie": "BE",
    "france": "FR", "frankrijk": "FR",
    "united kingdom": "GB", "verenigd koninkrijk": "GB",
    "poland": "PL", "polen": "PL",
    "spain": "ES", "spanje": "ES",
    "italy": "IT", "italië": "IT", "italie": "IT",
}


def extract(text: str) -> LocationExtractionResult:
    """Return a LocationExtractionResult with value=city and country=ISO2."""
    # 1. Try to find an explicit country mention
    country_iso2 = "XX"
    country_certainty = 0.0
    country_match = _COUNTRY_PATTERN.search(text)
    if country_match:
        country_iso2 = _COUNTRY_NAME_TO_ISO2.get(country_match.group(1).lower(), "XX")
        country_certainty = 1.0

    # 2. Try to find a city name
    text_lower = text.lower()
    for city, iso2 in _CITY_COUNTRY.items():
        if re.search(r"\b" + re.escape(city) + r"\b", text_lower):
            if country_iso2 == "XX":
                country_iso2 = iso2
                country_certainty = 0.8
            return LocationExtractionResult(
                value=city.title(),
                raw_match=city,
                certainty=(1.0 + country_certainty) / 2,
                method="city_lookup",
                country=country_iso2,
            )

    # 3. Fallback: look for "in <Word>" after investment keywords
    loc_match = re.search(
        r"(?:fabriek|plant|factory|facility|vestiging)\s+in\s+([A-Z][a-zA-Zé\-]+(?:\s[A-Z][a-zA-Zé\-]+)?)",
        text,
    )
    if loc_match:
        if country_iso2 == "XX":
            country_certainty = 0.3
        return LocationExtractionResult(
            value=loc_match.group(1),
            raw_match=loc_match.group(0),
            certainty=(0.7 + country_certainty) / 2,
            method="facility_keyword",
            country=country_iso2,
        )

    return LocationExtractionResult(
        value=None, raw_match=None, certainty=0.0, method="not_found", country=country_iso2
    )
