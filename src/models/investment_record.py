from __future__ import annotations

from dataclasses import dataclass
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
    capex: float | None = None           # Original reported amount, in millions
    currency: str | None = None          # ISO 4217 currency code, e.g. "USD", "EUR"
    capex_2025_eur: float | None = None  # Inflation-adjusted to 2025, in EUR millions
    capacity: float | None = None        # Production capacity (unit depends on source)
    facility_size_m2: float | None = None  # Facility floor area in m²

    # Fields used for deduplication, not written to CSV
    DEDUP_KEYS: ClassVar[tuple[str, ...]] = ("company", "location", "year")

    # Fields written to CSV, in order
    CSV_FIELDS: ClassVar[tuple[str, ...]] = (
        "company",
        "location",
        "country",
        "year",
        "capex",
        "currency",
        "capex_2025_eur",
        "capacity",
        "facility_size_m2",
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
        optional = {"capex", "capacity", "facility_size_m2", "capex_2025_eur"}
        return sum(1 for f in optional if getattr(self, f) is not None)

    @property
    def optional_count(self) -> int:
        return 4  # capex, capacity, facility_size_m2, capex_2025_eur
