"""End-to-end integration tests for the full scraper pipeline.

HTTP calls are mocked so no real network access is needed.
The full path fetch → parse → interim NDJSON → deduplicate → CSV is exercised.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scripts.factory_investment_scraper import run

# ---------------------------------------------------------------------------
# Shared fake HTML fixtures
# ---------------------------------------------------------------------------

SEED_HTML = """
<html><body>
  <a href="/press/shell-rotterdam-2025">Shell Rotterdam investment</a>
  <a href="/press/basf-geleen-2026">BASF Geleen investment</a>
</body></html>
"""

ARTICLE_SHELL = """
<html>
<head>
  <title>Shell investeert in Rotterdam | Shell</title>
  <meta property="og:site_name" content="Shell" />
</head>
<body>
  Shell investeert € 1,2 miljard in een nieuwe fabriek in Rotterdam.
  De productiecapaciteit bedraagt 500 MW groene waterstof.
  De fabriek wordt opgeleverd in 2025.
</body>
</html>
"""

ARTICLE_BASF = """
<html>
<head>
  <title>BASF kondigt investering aan in Geleen | BASF</title>
  <meta property="og:site_name" content="BASF" />
</head>
<body>
  BASF kondigt aan EUR 800 miljoen te investeren in een fabriek in Geleen.
  Oplevering gepland voor 2026.
</body>
</html>
"""

ARTICLE_IRRELEVANT = """
<html><head><title>Company news</title></head>
<body>No investment figures here. Just a regular update.</body>
</html>
"""


def _fake_response(html: str) -> MagicMock:
    mock = MagicMock()
    mock.raise_for_status = MagicMock()
    mock.text = html
    return mock


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_config(source_type: str, seed_url: str) -> dict:
    return {
        "sources": [{
            "name": f"test_{source_type}",
            "type": source_type,
            "seed_urls": [seed_url],
            "rate_limit_rps": 100,  # minimise sleep delay in tests
            "source_quality": 1.0,
        }]
    }


# ---------------------------------------------------------------------------
# Press releases
# ---------------------------------------------------------------------------

class TestPressReleasesPipeline:
    SEED = "https://shell.com/press"

    def _get(self, url, **kwargs):
        if url == self.SEED:
            return _fake_response(SEED_HTML)
        if "shell-rotterdam" in url:
            return _fake_response(ARTICLE_SHELL)
        if "basf-geleen" in url:
            return _fake_response(ARTICLE_BASF)
        return _fake_response(ARTICLE_IRRELEVANT)

    def test_csv_contains_expected_records(self, tmp_path: Path):
        cfg = _make_config("press_releases", self.SEED)
        output = tmp_path / "out.csv"
        interim = tmp_path / "interim"

        with patch("httpx.get", side_effect=self._get), \
             patch("scripts.factory_investment_scraper.load_config", return_value=cfg):
            run(output=output, interim_dir=interim)

        rows = list(csv.DictReader(output.open()))
        companies = {r["company"] for r in rows}
        assert "Shell" in companies
        assert "BASF" in companies

    def test_interim_ndjson_written(self, tmp_path: Path):
        cfg = _make_config("press_releases", self.SEED)
        output = tmp_path / "out.csv"
        interim = tmp_path / "interim"

        with patch("httpx.get", side_effect=self._get), \
             patch("scripts.factory_investment_scraper.load_config", return_value=cfg):
            run(output=output, interim_dir=interim)

        files = list(interim.glob("*.ndjson"))
        assert len(files) == 1
        lines = [l for l in files[0].read_text().splitlines() if l]
        # Both articles parsed (even if confidence is low)
        assert len(lines) == 2

    def test_interim_lines_are_valid_json(self, tmp_path: Path):
        cfg = _make_config("press_releases", self.SEED)
        output = tmp_path / "out.csv"
        interim = tmp_path / "interim"

        with patch("httpx.get", side_effect=self._get), \
             patch("scripts.factory_investment_scraper.load_config", return_value=cfg):
            run(output=output, interim_dir=interim)

        ndjson = next((tmp_path / "interim").glob("*.ndjson"))
        for line in ndjson.read_text().splitlines():
            obj = json.loads(line)
            assert "fields" in obj
            assert "confidence_score" in obj

    def test_no_interim_flag_skips_write(self, tmp_path: Path):
        cfg = _make_config("press_releases", self.SEED)
        output = tmp_path / "out.csv"

        with patch("httpx.get", side_effect=self._get), \
             patch("scripts.factory_investment_scraper.load_config", return_value=cfg):
            run(output=output, interim_dir=None)

        assert not (tmp_path / "interim").exists()

    def test_year_and_capex_in_csv(self, tmp_path: Path):
        cfg = _make_config("press_releases", self.SEED)
        output = tmp_path / "out.csv"

        with patch("httpx.get", side_effect=self._get), \
             patch("scripts.factory_investment_scraper.load_config", return_value=cfg):
            run(output=output, interim_dir=None)

        rows = {r["company"]: r for r in csv.DictReader(output.open())}
        assert rows["Shell"]["year"] == "2025"
        assert float(rows["Shell"]["capex"]) == pytest.approx(1200.0)
        assert rows["Shell"]["country"] == "NL"

    def test_failed_fetch_does_not_crash_pipeline(self, tmp_path: Path):
        import httpx as _httpx

        def flaky_get(url, **kwargs):
            if url == self.SEED:
                return _fake_response(SEED_HTML)
            raise _httpx.ConnectError("timeout")

        cfg = _make_config("press_releases", self.SEED)
        output = tmp_path / "out.csv"

        with patch("httpx.get", side_effect=flaky_get), \
             patch("scripts.factory_investment_scraper.load_config", return_value=cfg):
            run(output=output, interim_dir=None)   # must not raise

        # CSV written but empty (header only)
        rows = list(csv.DictReader(output.open()))
        assert isinstance(rows, list)
