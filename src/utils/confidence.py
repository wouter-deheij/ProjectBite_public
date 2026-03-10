"""
Confidence scoring for InvestmentRecord instances.

Score = weighted combination of:
  1. Completeness  – fraction of optional fields that are filled (0–1)
  2. Source quality – assigned per source type in sources.yaml (0–1)
  3. Extraction certainty – passed in by each extractor (0–1)
"""

from __future__ import annotations

from src.models.investment_record import InvestmentRecord

# Weight of each component (must sum to 1.0)
_W_COMPLETENESS = 0.3
_W_SOURCE = 0.4
_W_EXTRACTION = 0.3


def score(
    record: InvestmentRecord,
    source_quality: float,
    extraction_certainty: float,
) -> float:
    """Return a confidence score in [0.0, 1.0]."""
    completeness = (
        record.filled_optional_count / record.optional_count
        if record.optional_count
        else 1.0
    )

    raw = (
        _W_COMPLETENESS * completeness
        + _W_SOURCE * source_quality
        + _W_EXTRACTION * extraction_certainty
    )
    return round(min(max(raw, 0.0), 1.0), 3)
