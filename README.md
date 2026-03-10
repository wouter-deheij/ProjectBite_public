# Factory Investment Scraper

Collects publicly announced factory investments from press releases, government registers, and news sources. Outputs a structured CSV.

## Output schema

| Field | Type | Description |
|---|---|---|
| `company` | string | Investing company name |
| `location` | string | City or region |
| `country` | string | ISO 3166-1 alpha-2 (e.g. `NL`) |
| `year` | integer | Announced investment year |
| `capex` | float | CapEx in EUR millions (null if unknown) |
| `capacity` | string | Raw capacity string (null if unknown) |
| `source_url` | string | URL of the source page |
| `confidence_score` | float | 0.0–1.0 composite score |

## Setup

```bash
pip install -e ".[dev]"
```

## Run

```bash
# All sources
python -m scraper.pipeline

# Single source type
python -m scraper.pipeline --source press_releases

# Custom output path
python -m scraper.pipeline --output data/output/2024.csv
```

## Test

```bash
pytest
```

## Structure

```
scraper/
├── sources/        # One module per source type (press_releases, government, news)
├── extractors/     # Field extraction: capex, capacity, location
├── models.py       # InvestmentRecord dataclass
├── confidence.py   # Confidence scoring
└── pipeline.py     # Orchestration: fetch → extract → dedupe → CSV

config/
└── sources.yaml    # Seed URLs, rate limits, source quality per source

data/
├── raw/            # Cached HTML (gitignored)
└── output/         # Generated CSVs

tests/
├── test_extractors.py
└── fixtures/       # Sample HTML for unit tests
```

## Adding a new source

1. Add an entry to `config/sources.yaml` with a `type` matching an existing source module (or create a new one in `scraper/sources/`).
2. Set `source_quality` between 0.0 and 1.0 reflecting how reliable the source is.
3. Run the pipeline.
