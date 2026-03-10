from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ExtractionResult:
    """Result of a single field extraction attempt.

    Attributes:
        value:     Parsed value (None if extraction failed).
        raw_match: The exact substring from the source text that was matched.
                   None if nothing was found.
        certainty: Confidence in [0.0, 1.0] that value is correct.
        method:    Name of the pattern or strategy that produced this result,
                   e.g. "regex_nl_miljard" or "not_found". Useful for debugging
                   low-confidence records.
    """

    value: float | str | None
    raw_match: str | None
    certainty: float
    method: str


@dataclass
class LocationExtractionResult(ExtractionResult):
    """ExtractionResult extended with a country code.

    value:   city or region string (or None)
    country: ISO 3166-1 alpha-2 code, e.g. "NL". "XX" if unknown.
    """

    country: str = "XX"
