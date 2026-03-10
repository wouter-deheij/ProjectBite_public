from __future__ import annotations

from dataclasses import asdict, dataclass

from src.models.extraction_result import ExtractionResult, LocationExtractionResult
from src.models.investment_record import InvestmentRecord


@dataclass
class ParsedPage:
    """All extraction results for a single scraped page.

    This is the intermediate representation between raw HTML and the final
    InvestmentRecord. It preserves every extractor's raw_match and method,
    making low-confidence records fully debuggable.
    """

    source_url: str
    source_name: str
    source_quality: float
    parsed_at: str           # ISO 8601 timestamp

    company: ExtractionResult
    capex: ExtractionResult
    capacity: ExtractionResult
    location: LocationExtractionResult
    year: ExtractionResult

    confidence_score: float

    def to_investment_record(self) -> InvestmentRecord | None:
        """Return an InvestmentRecord if all required fields were extracted."""
        if not self.location.value or not self.company.value or not self.year.value:
            return None
        return InvestmentRecord(
            company=self.company.value,
            location=self.location.value,
            country=self.location.country,
            year=int(self.year.value),
            source_url=self.source_url,
            confidence_score=self.confidence_score,
            capex=self.capex.value,
            capacity=self.capacity.value,
        )

    def to_dict(self) -> dict:
        """Serialize to a JSON-compatible dict for the interim format."""
        return {
            "source_url": self.source_url,
            "source_name": self.source_name,
            "source_quality": self.source_quality,
            "parsed_at": self.parsed_at,
            "confidence_score": self.confidence_score,
            "fields": {
                "company":  _result_to_dict(self.company),
                "capex":    _result_to_dict(self.capex),
                "capacity": _result_to_dict(self.capacity),
                "location": _result_to_dict(self.location),
                "year":     _result_to_dict(self.year),
            },
        }


def _result_to_dict(result: ExtractionResult) -> dict:
    d = asdict(result)
    # Ensure value is JSON-serialisable (floats and strings are; None is fine)
    return d
