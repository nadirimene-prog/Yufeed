import pytest

from src.ai import cost_tracker


@pytest.mark.unit
def test_normalize_model_for_pricing_aliases():
    assert (
        cost_tracker.normalize_model_for_pricing("anthropic", "claude-sonnet-4-20250514")
        == "claude-sonnet-4"
    )
    assert (
        cost_tracker.normalize_model_for_pricing("anthropic", "claude-3-haiku-20240307")
        == "claude-3-haiku"
    )
    assert cost_tracker.normalize_model_for_pricing("openai", "gpt-4o") == "gpt-4-turbo"


@pytest.mark.unit
def test_estimate_cost_uses_normalized_model_aliases():
    cost = cost_tracker.estimate_cost(
        provider="anthropic",
        model="claude-sonnet-4-20250514",
        prompt_tokens=1000,
        completion_tokens=500,
    )
    assert cost > 0
