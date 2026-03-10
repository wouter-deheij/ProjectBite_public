"""Unit tests for the pipeline helpers."""

import json
from pathlib import Path

from scripts.factory_investment_scraper import write_interim, deduplicate
from src.models.investment_record import InvestmentRecord
from src.parsing.record_parser import RecordParser

_parser = RecordParser()
_CFG = {"name": "test", "source_quality": 0.8}


def _make_page(text: str):
    return _parser.parse(text, "https://example.com/test", _CFG)


class TestWriteInterim:
    def test_creates_ndjson_file(self, tmp_path: Path):
        pages = [
            _make_page("Shell investeert € 500 miljoen in Rotterdam. 2025."),
            _make_page("No useful data here."),
        ]
        write_interim(pages, tmp_path)
        files = list(tmp_path.glob("*.ndjson"))
        assert len(files) == 1

    def test_ndjson_line_count(self, tmp_path: Path):
        pages = [_make_page(f"Shell bouwt fabriek in Rotterdam in 202{i}.") for i in range(3)]
        write_interim(pages, tmp_path)
        ndjson = next(tmp_path.glob("*.ndjson"))
        lines = [l for l in ndjson.read_text().splitlines() if l]
        assert len(lines) == 3

    def test_each_line_is_valid_json_with_required_keys(self, tmp_path: Path):
        pages = [_make_page("Shell investeert € 1 miljard in Amsterdam. 2026.")]
        write_interim(pages, tmp_path)
        ndjson = next(tmp_path.glob("*.ndjson"))
        for line in ndjson.read_text().splitlines():
            obj = json.loads(line)
            assert "source_url" in obj
            assert "confidence_score" in obj
            assert "fields" in obj

    def test_empty_pages_writes_nothing(self, tmp_path: Path):
        write_interim([], tmp_path)
        assert list(tmp_path.glob("*.ndjson")) == []


class TestDeduplicate:
    def _record(self, company: str, year: int, score: float) -> InvestmentRecord:
        return InvestmentRecord(
            company=company,
            location="Rotterdam",
            country="NL",
            year=year,
            source_url="https://example.com",
            confidence_score=score,
        )

    def test_keeps_highest_confidence(self):
        records = [
            self._record("Shell", 2025, 0.6),
            self._record("Shell", 2025, 0.9),
        ]
        result = deduplicate(records)
        assert len(result) == 1
        assert result[0].confidence_score == 0.9

    def test_different_years_kept_separately(self):
        records = [
            self._record("Shell", 2025, 0.8),
            self._record("Shell", 2026, 0.8),
        ]
        assert len(deduplicate(records)) == 2
