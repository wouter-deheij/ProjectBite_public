from __future__ import annotations

from dataclasses import dataclass, field, fields
from typing import ClassVar


@dataclass
class InvestmentRecord:
    """Represents a single observed factory investment announcement."""

    # Required fields
    company: str
    location: str
    country: str          # ISO 3166-1 alpha-2 (e.g. "NL", "DE")
    year: int
    source_url: str
    confidence_score: float  # 0.0–1.0

    # Optional fields
    capex: float | None = None       # Always in EUR millions
    capacity: str | None = None      # Raw string, e.g. "500.000 ton/jaar"

    # Fields used for deduplication, not written to CSV
    DEDUP_KEYS: ClassVar[tuple[str, ...]] = ("company", "location", "year")

    # Fields written to CSV, in order
    CSV_FIELDS: ClassVar[tuple[str, ...]] = (
        "company",
        "location",
        "country",
        "year",
        "capex",
        "capacity",
        "source_url",
        "confidence_score",
    )

    def to_csv_row(self) -> dict[str, object]:
        return {f: getattr(self, f) for f in self.CSV_FIELDS}

    @property
    def dedup_key(self) -> tuple[str, ...]:
        return tuple(getattr(self, k) for k in self.DEDUP_KEYS)

    @property
    def filled_optional_count(self) -> int:
        optional = {"capex", "capacity"}
        return sum(1 for f in optional if getattr(self, f) is not None)

    @property
    def optional_count(self) -> int:
        return 2  # capex, capacity
