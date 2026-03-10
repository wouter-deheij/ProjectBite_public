"""Unit tests for field extractors."""

import pytest

from src.parsing import capex, capacity, location


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
