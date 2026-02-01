import pytest

from src.compliance import scope


@pytest.mark.unit
def test_scope_normalization_and_keywords():
    assert scope.normalize_scopes(None) == []
    assert scope.normalize_scopes("all") == []
    assert scope.normalize_scopes("psp,emi") == ["psp", "eme"]

    keywords = scope.scope_keywords(["psp", "eme"])
    assert "payment service" in keywords
    assert "electronic money" in keywords


@pytest.mark.unit
def test_scope_inference_and_haystack():
    tags = scope.infer_scope_tags("This mentions crypto and blockchain")
    assert "vasp" in tags

    tags = scope.infer_scope_tags({"a": "payment service"}, ["card"], None)
    assert "psp" in tags
