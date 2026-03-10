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
pip install -r requirements.txt
```

## Run

```bash
# 1. Scrape all sources → data/processed/investments.csv
python scripts/factory_investment_scraper.py

# Scrape only one source type
python scripts/factory_investment_scraper.py --source press_releases

# 2. Clean raw output
python scripts/clean_factory_data.py

# 3. Export with filters
python scripts/export_csv.py --country NL --min-year 2022 --min-confidence 0.7
```

## Test

```bash
pytest
```

## Structure

```
scripts/
├── factory_investment_scraper.py   # Scrape → dedupe → CSV
├── clean_factory_data.py           # Validate and clean output
└── export_csv.py                   # Filter and export

src/
├── scraping/     # One module per source type (press_releases, government, news)
├── parsing/      # Field extraction: capex, capacity, location
├── models/       # InvestmentRecord dataclass
└── utils/        # Confidence scoring

config/
└── sources.yaml  # Seed URLs, rate limits, source quality per source

data/
├── raw/          # Cached HTML (gitignored)
└── processed/    # Generated CSVs

tests/
├── test_extractors.py
└── fixtures/     # Sample HTML for unit tests
```

## Adding a new source

1. Add an entry to `config/sources.yaml` with a `type` matching an existing source module (or create a new one in `src/scraping/`).
2. Set `source_quality` between 0.0 and 1.0 reflecting how reliable the source is.
3. Run `python scripts/factory_investment_scraper.py`.
