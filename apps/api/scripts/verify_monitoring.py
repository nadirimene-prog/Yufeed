import sys
import os
from datetime import datetime

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.services.rule_engine import RuleEngine


def test_rule_engine():
    print("--- Testing Rule Engine Logic ---")

    # Test 1: Simple comparison
    condition = {"field": "amount", "operator": ">", "value": 1000}
    data = {"amount": 1500}
    assert RuleEngine.evaluate_condition(condition, data) == True
    print("Test 1 (Simple Comparison): PASSED")

    # Test 2: Nested AND/OR
    nested_rule = {
        "logic": "AND",
        "conditions": [
            {"field": "currency", "operator": "==", "value": "USD"},
            {
                "logic": "OR",
                "conditions": [
                    {"field": "amount", "operator": ">", "value": 10000},
                    {"field": "country_code", "operator": "==", "value": "RU"},
                ],
            },
        ],
    }

    # Should match: USD AND (Amount > 10000 OR Country == RU)
    match_data = {"currency": "USD", "amount": 500, "country_code": "RU"}
    assert RuleEngine.match_rule(nested_rule, match_data) == True
    print("Test 2 (Nested Logic Match): PASSED")

    # Should NOT match
    no_match_data = {"currency": "USD", "amount": 500, "country_code": "US"}
    assert RuleEngine.match_rule(nested_rule, no_match_data) == False
    print("Test 3 (Nested Logic No Match): PASSED")

    print("\n--- All Backend Logic Tests Passed! ---")


if __name__ == "__main__":
    test_rule_engine()
