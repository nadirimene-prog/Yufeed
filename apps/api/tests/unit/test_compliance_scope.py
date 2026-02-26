import pytest

from src.compliance import scope


@pytest.mark.unit
def test_scope_normalization_and_keywords():
    assert scope.normalize_scopes(None) == []
    assert scope.normalize_scopes("all") == []
    assert scope.normalize_scopes("psp,emi") == ["psp", "eme"]
    assert scope.normalize_scopes("psan,casp") == ["vasp"]

    keywords = scope.scope_keywords(["psp", "eme"])
    assert "payment service" in keywords
    assert "electronic money" in keywords


@pytest.mark.unit
def test_scope_inference_and_haystack():
    tags = scope.infer_scope_tags("This mentions crypto and blockchain")
    assert "vasp" in tags

    tags = scope.infer_scope_tags({"a": "payment service"}, ["card"], None)
    assert "psp" in tags


@pytest.mark.unit
def test_parse_scopes_surfaces_invalid_tokens():
    parsed = scope.parse_scopes("psp,aml,psan")
    assert parsed.scopes == ["psp", "vasp"]
    assert parsed.invalid_tokens == ["aml"]
    assert parsed.explicit_all is False


@pytest.mark.unit
def test_match_scope_filter_explicit_all_and_invalid_behavior():
    matched, parsed = scope.match_scope_filter("all", "anything")
    assert matched is True
    assert parsed.explicit_all is True

    matched, parsed = scope.match_scope_filter(
        "aml", "payment services", fail_closed_on_invalid=True
    )
    assert matched is False
    assert parsed.invalid_tokens == ["aml"]


@pytest.mark.unit
def test_normalize_scope_tags_drops_legacy_unknown_values():
    assert scope.normalize_scope_tags(["aml", "psan", "eme"]) == ["vasp", "eme"]
