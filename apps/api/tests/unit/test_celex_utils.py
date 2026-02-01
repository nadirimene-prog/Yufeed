import pytest

from src.utils.celex_utils import (
    normalize_celex,
    parse_celex,
    generate_celex_variations,
    suggest_celex,
    is_valid_celex,
)


@pytest.mark.unit
def test_normalize_celex_variants():
    assert normalize_celex("GDPR") == "32016R0679"
    assert normalize_celex("2016/679") == "32016R0679"
    assert normalize_celex("Regulation 2016/679") == "32016R0679"
    assert normalize_celex("32016R679") == "32016R0679"
    assert normalize_celex("unknown") is None


@pytest.mark.unit
def test_parse_celex_and_variations():
    parsed = parse_celex("32016R0679")
    assert parsed["sector"] == "3"
    assert parsed["year"] == "2016"
    assert parsed["document_type"] == "R"
    assert parsed["number"] == "0679"

    variations = generate_celex_variations("32016R0679")
    assert "32016R0679" in variations
    assert "2016/679" in variations


@pytest.mark.unit
def test_suggest_and_validate_celex():
    suggestions = suggest_celex("gdpr")
    assert "32016R0679" in suggestions

    assert is_valid_celex("32016R0679") is True
    assert is_valid_celex("BAD") is False
