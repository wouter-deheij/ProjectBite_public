"""Unit tests for field extractors."""

import pytest

from src.parsing import capex, capacity, location
from src.parsing.record_parser import RecordParser


class TestCapex:
    def test_dutch_miljard(self):
        result = capex.extract("Shell investeert € 1,2 miljard in nieuwe fabriek.")
        assert result.value == pytest.approx(1200.0)
        assert result.certainty == 1.0
        assert result.raw_match is not None
        assert "miljard" in result.raw_match.lower()
        assert result.method == "regex_nl_miljard"

    def test_dutch_miljoen(self):
        result = capex.extract("Investeringsbedrag: 500 miljoen euro.")
        assert result.value == pytest.approx(500.0)
        assert result.certainty == 1.0
        assert result.method == "regex_nl_miljoen"

    def test_english_billion(self):
        result = capex.extract("The company announced a $2.5 billion investment.")
        assert result.value == pytest.approx(2500.0)
        assert result.certainty == 1.0
        assert result.method == "regex_en_billion"

    def test_english_million(self):
        result = capex.extract("EUR 300 million will be invested.")
        assert result.value == pytest.approx(300.0)
        assert result.certainty == 1.0

    def test_not_found(self):
        result = capex.extract("No financial figures here.")
        assert result.value is None
        assert result.certainty == 0.0
        assert result.raw_match is None
        assert result.method == "not_found"


class TestCapacity:
    def test_ton_per_jaar(self):
        result = capacity.extract("De fabriek heeft een capaciteit van 500.000 ton per jaar.")
        assert result.value is not None
        assert result.certainty == 1.0
        assert result.raw_match is not None

    def test_megawatt(self):
        result = capacity.extract("The plant will produce 200 MW of green hydrogen.")
        assert result.value is not None
        assert result.certainty == 1.0

    def test_not_found(self):
        result = capacity.extract("No capacity mentioned.")
        assert result.value is None
        assert result.certainty == 0.0
        assert result.method == "not_found"


class TestLocation:
    def test_dutch_city(self):
        result = location.extract("Shell bouwt een fabriek in Rotterdam.")
        assert result.value == "Rotterdam"
        assert result.country == "NL"
        assert result.certainty > 0.5
        assert result.method == "city_lookup"

    def test_explicit_country(self):
        result = location.extract("Investering in Duitsland aangekondigd.")
        assert result.country == "DE"

    def test_not_found(self):
        result = location.extract("No location mentioned anywhere.")
        assert result.value is None
        assert result.certainty == 0.0
        assert result.method == "not_found"


class TestRecordParser:
    def setup_method(self):
        self.parser = RecordParser()
        self.cfg = {"name": "test", "source_quality": 0.8}

    def test_full_extraction(self):
        text = (
            "Shell investeert € 1,2 miljard in nieuwe fabriek in Rotterdam. "
            "De capaciteit bedraagt 200 MW. Oplevering in 2026."
        )
        page = self.parser.parse(text, "https://example.com/pr1", self.cfg)
        assert page.company.value == "Shell"
        assert page.capex.value == pytest.approx(1200.0)
        assert page.location.value == "Rotterdam"
        assert page.location.country == "NL"
        assert page.year.value == 2026
        assert page.confidence_score > 0.0

    def test_to_investment_record_returns_none_when_missing_required(self):
        text = "No location, no company, no year here."
        page = self.parser.parse(text, "https://example.com/empty", self.cfg)
        assert page.to_investment_record() is None

    def test_to_investment_record_success(self):
        text = "Shell investeert € 500 miljoen in Amsterdam. Oplevering 2025."
        page = self.parser.parse(text, "https://example.com/pr2", self.cfg)
        record = page.to_investment_record()
        assert record is not None
        assert record.company == "Shell"
        assert record.location == "Amsterdam"
        assert record.year == 2025

    def test_to_dict_contains_all_fields(self):
        text = "Shell bouwt fabriek in Rotterdam in 2027."
        page = self.parser.parse(text, "https://example.com/pr3", self.cfg)
        d = page.to_dict()
        assert "source_url" in d
        assert "confidence_score" in d
        assert set(d["fields"].keys()) == {"company", "capex", "capacity", "location", "year"}
