"""Unit tests for OJ act-by-act identifier mapping."""

import pytest

from src.ingestion.oj_mapping import extract_oj_act_identifier, extract_oj_series


@pytest.mark.unit
def test_extract_oj_act_identifier_from_direct() -> None:
    assert extract_oj_act_identifier("L_202302386") == "L_202302386"
    assert extract_oj_act_identifier("OJ:C_202300099") == "C_202300099"


@pytest.mark.unit
def test_extract_oj_act_identifier_from_jol_joc() -> None:
    assert extract_oj_act_identifier("JOL_2023_2386") == "L_202302386"
    assert extract_oj_act_identifier("oj:JOC_2023_99") == "C_202300099"
    assert extract_oj_act_identifier("JOC_2023_00005") == "C_202300005"


@pytest.mark.unit
def test_extract_oj_act_identifier_none() -> None:
    assert extract_oj_act_identifier("OJ L") is None
    assert extract_oj_act_identifier(None) is None


@pytest.mark.unit
def test_extract_oj_series() -> None:
    assert extract_oj_series("JOL_2023_2386") == "L"
    assert extract_oj_series("oj:JOC_2023_99") == "C"
    assert extract_oj_series("OJ L") == "L"
    assert extract_oj_series("OJ C") == "C"
    assert extract_oj_series("CI_202300001") == "CI"
    assert extract_oj_series(None) is None
