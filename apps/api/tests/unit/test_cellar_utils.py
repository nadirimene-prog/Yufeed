import pytest

from src.ingestion.cellar import CellarClient


@pytest.mark.unit
def test_cellar_helpers():
    assert CellarClient._validate_celex("32016R0679") is True
    assert CellarClient._validate_celex("bad") is False

    assert CellarClient._sanitize_celex("32016R0679") == "32016R0679"
    assert CellarClient._sanitize_celex("32016R-0679") == "32016R0679"

    assert CellarClient._sanitize_query_term("AI Act!!!") == "ai act"

    identifier = CellarClient._extract_oj_identifier("http://example.com/oj/L_2023_001")
    assert identifier == "L_2023_001"

    series = CellarClient._extract_oj_series("L_2023_001")
    assert series == "L"
