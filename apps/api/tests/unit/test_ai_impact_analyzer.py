import pytest

from src.ai.impact_analyzer import ImpactAnalyzer


@pytest.mark.unit
def test_impact_analyzer_fallback_and_prompt():
    analyzer = ImpactAnalyzer()
    analyzer.client = None

    doc = {
        "celex": "CELEX-IMPACT",
        "title": "AML Regulation",
        "type": "regulation",
        "compliance_domain": "aml",
        "risk_level": "high",
    }

    prompt = analyzer._build_impact_prompt(doc)
    assert "AML Regulation" in prompt
    assert "CELEX-IMPACT" in prompt

    analysis = analyzer.analyze_impact(doc)
    assert analysis["overall_impact_level"] == "high"
    assert analysis["affected_areas"]
    assert analysis["resource_estimates"]["requires_process_changes"] is True


@pytest.mark.unit
def test_impact_analyzer_parse_response_and_fallback_structure():
    analyzer = ImpactAnalyzer()

    response_text = """
    ```json
    {
      "overall_impact_level": "low",
      "executive_summary": "Short summary",
      "affected_areas": ["onboarding"],
      "key_changes": ["Change A"],
      "action_items": [],
      "gaps": [],
      "resource_estimates": {"total_hours": 5, "total_cost_eur": 1000}
    }
    ```
    """

    parsed = analyzer._parse_impact_response(response_text)
    assert parsed["overall_impact_level"] == "low"
    assert parsed["affected_areas"] == ["onboarding"]

    fallback = analyzer._fallback_analysis_structure()
    assert fallback["overall_impact_level"] == "medium"
    assert "resource_estimates" in fallback
