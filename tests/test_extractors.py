"""Unit tests for field extractors."""

import pytest

from src.parsing import capex, capacity, location


class TestCapex:
    def test_dutch_miljard(self):
        value, certainty = capex.extract("Shell investeert € 1,2 miljard in nieuwe fabriek.")
        assert value == pytest.approx(1200.0)
        assert certainty == 1.0

    def test_dutch_miljoen(self):
        value, certainty = capex.extract("Investeringsbedrag: 500 miljoen euro.")
        assert value == pytest.approx(500.0)
        assert certainty == 1.0

    def test_english_billion(self):
        value, certainty = capex.extract("The company announced a $2.5 billion investment.")
        assert value == pytest.approx(2500.0)
        assert certainty == 1.0

    def test_english_million(self):
        value, certainty = capex.extract("EUR 300 million will be invested.")
        assert value == pytest.approx(300.0)
        assert certainty == 1.0

    def test_not_found(self):
        value, certainty = capex.extract("No financial figures here.")
        assert value is None
        assert certainty == 0.0


class TestCapacity:
    def test_ton_per_jaar(self):
        raw, certainty = capacity.extract("De fabriek heeft een capaciteit van 500.000 ton per jaar.")
        assert raw is not None
        assert certainty == 1.0

    def test_megawatt(self):
        raw, certainty = capacity.extract("The plant will produce 200 MW of green hydrogen.")
        assert raw is not None
        assert certainty == 1.0

    def test_not_found(self):
        raw, certainty = capacity.extract("No capacity mentioned.")
        assert raw is None
        assert certainty == 0.0


class TestLocation:
    def test_dutch_city(self):
        loc, country, certainty = location.extract("Shell bouwt een fabriek in Rotterdam.")
        assert loc == "Rotterdam"
        assert country == "NL"
        assert certainty > 0.5

    def test_explicit_country(self):
        loc, country, certainty = location.extract("Investering in Duitsland aangekondigd.")
        assert country == "DE"

    def test_not_found(self):
        loc, country, certainty = location.extract("No location mentioned anywhere.")
        assert loc is None
        assert certainty == 0.0
