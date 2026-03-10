"""Inflation adjustment and currency conversion utilities.

CPI source: US Bureau of Labor Statistics, CPI-U annual averages.
EUR/USD rates: ECB annual average exchange rates.

Update these tables periodically for fresh runs.
"""

from __future__ import annotations

# US CPI-U annual averages (index, 1982-84=100)
# Source: BLS (https://www.bls.gov/cpi/)
_US_CPI: dict[int, float] = {
    2010: 218.056,
    2011: 224.939,
    2012: 229.594,
    2013: 232.957,
    2014: 236.736,
    2015: 237.017,
    2016: 240.007,
    2017: 245.120,
    2018: 251.107,
    2019: 255.657,
    2020: 258.811,
    2021: 270.970,
    2022: 292.655,
    2023: 304.702,
    2024: 313.686,
    2025: 319.0,    # preliminary estimate
}

# ECB annual average EUR/USD rates (1 EUR = x USD)
# Source: ECB Statistical Data Warehouse
_EUR_USD: dict[int, float] = {
    2010: 1.3257,
    2011: 1.3920,
    2012: 1.2848,
    2013: 1.3281,
    2014: 1.3285,
    2015: 1.1095,
    2016: 1.1069,
    2017: 1.1297,
    2018: 1.1810,
    2019: 1.1195,
    2020: 1.1422,
    2021: 1.1827,
    2022: 1.0530,
    2023: 1.0813,
    2024: 1.0815,
    2025: 1.07,     # approximate year-to-date average
}

# Capex plausibility range in millions (original currency)
CAPEX_MIN_M = 1.0      # below $1M is almost certainly a data error
CAPEX_MAX_M = 50_000.0  # above $50B is implausible for a single plant


def is_plausible_capex(value_m: float) -> bool:
    """Return True if the capex value (in millions) is within a realistic range."""
    return CAPEX_MIN_M <= value_m <= CAPEX_MAX_M


def to_2025_eur(
    value_m: float,
    source_year: int,
    source_currency: str = "USD",
) -> float | None:
    """Convert a capex amount to 2025 EUR millions.

    Args:
        value_m: Amount in millions, in source_currency.
        source_year: Year the amount was reported.
        source_currency: ISO 4217 code; currently supports "USD" and "EUR".

    Returns:
        Amount in EUR millions adjusted to 2025 price levels, or None if
        the required CPI/FX data is unavailable.
    """
    target_year = 2025

    if source_currency == "USD":
        cpi_base = _US_CPI.get(source_year)
        cpi_target = _US_CPI.get(target_year)
        if cpi_base is None or cpi_target is None:
            return None

        # Inflate to 2025 USD millions
        value_2025_usd = value_m * (cpi_target / cpi_base)

        # Convert to EUR using source-year EUR/USD rate so the result is
        # expressed in constant 2025 EUR purchasing power
        eur_usd = _EUR_USD.get(target_year)
        if eur_usd is None:
            return None
        return round(value_2025_usd / eur_usd, 2)

    if source_currency == "EUR":
        # Only apply inflation (no FX conversion needed)
        # Use ECB HICP or a proxy; for simplicity reuse US CPI trend
        cpi_base = _US_CPI.get(source_year)
        cpi_target = _US_CPI.get(target_year)
        if cpi_base is None or cpi_target is None:
            return None
        return round(value_m * (cpi_target / cpi_base), 2)

    return None  # unsupported currency


SQF_TO_M2 = 0.092903  # 1 sq ft = 0.092903 m²


def sqft_to_m2(sqft: float) -> float:
    """Convert square feet to square metres, rounded to the nearest integer."""
    return round(sqft * SQF_TO_M2)
