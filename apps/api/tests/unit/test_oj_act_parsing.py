"""Unit tests for Official Journal act-by-act parsing helpers."""
import pytest

from src.ingestion.cellar import CellarClient


@pytest.mark.unit
def test_extract_oj_identifier_from_uri() -> None:
    client = CellarClient(enable_cache=False)
    assert (
        client._extract_oj_identifier("http://publications.europa.eu/resource/oj/C_2023_00002")
        == "C_2023_00002"
    )
    assert client._extract_oj_identifier("oj:C_202300002") == "C_202300002"
    assert (
        client._extract_oj_identifier("http://publications.europa.eu/resource/oj/CI_2023_00002_SIG")
        == "CI_2023_00002_SIG"
    )
    assert client._extract_oj_identifier(None) is None


@pytest.mark.unit
def test_extract_oj_series() -> None:
    client = CellarClient(enable_cache=False)
    assert client._extract_oj_series("C_2023_00002") == "C"
    assert client._extract_oj_series("CI_2023_00002_SIG") == "CI"
    assert client._extract_oj_series("LI_2023_00002") == "LI"
    assert client._extract_oj_series("2023_00002") is None
    assert client._extract_oj_series(None) is None
