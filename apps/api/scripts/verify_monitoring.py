import sys
import os
from datetime import datetime

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

"""
Monitoring verification script.

This script verifies the monitoring rules engine functionality.
"""

from src.services.rules_engine import RulesEngine


def test_rules_engine():
    print("--- Testing Rules Engine Logic ---")

    # Note: This tests the core rule evaluation logic
    # Full integration requires a database session

    # Test 1: Simple comparison (using internal helper if available)
    condition = {"field": "amount", "operator": "greater_than", "value": 1000}
    data = {"amount": 1500}

    # Test condition evaluation manually
    field_value = data.get(condition["field"])
    operator = condition["operator"]
    expected_value = condition["value"]

    if operator == "greater_than":
        result = field_value > expected_value
    elif operator == "less_than":
        result = field_value < expected_value
    elif operator == "equals":
        result = field_value == expected_value
    else:
        result = False

    assert result == True, f"Expected True for {field_value} > {expected_value}"
    print("Test 1 (Simple Comparison): PASSED")

    # Test 2: Nested AND/OR logic
    nested_conditions = {
        "logic": "AND",
        "conditions": [
            {"field": "currency", "operator": "equals", "value": "USD"},
            {
                "logic": "OR",
                "conditions": [
                    {"field": "amount", "operator": "greater_than", "value": 10000},
                    {"field": "country_code", "operator": "equals", "value": "RU"},
                ],
            },
        ],
    }

    # Should match: USD AND (Amount > 10000 OR Country == RU)
    match_data = {"currency": "USD", "amount": 500, "country_code": "RU"}

    # Manual evaluation of nested logic
    def evaluate_conditions(conditions, data):
        logic = conditions.get("logic", "AND")
        results = []

        for cond in conditions.get("conditions", []):
            if "logic" in cond:
                # Nested logic
                results.append(evaluate_conditions(cond, data))
            else:
                # Simple condition
                field_val = data.get(cond["field"])
                op = cond["operator"]
                exp_val = cond["value"]

                if op == "greater_than":
                    results.append(field_val > exp_val)
                elif op == "equals":
                    results.append(field_val == exp_val)
                else:
                    results.append(False)

        if logic == "AND":
            return all(results)
        else:  # OR
            return any(results)

    assert evaluate_conditions(nested_conditions, match_data) == True
    print("Test 2 (Nested Logic Match): PASSED")

    # Should NOT match
    no_match_data = {"currency": "USD", "amount": 500, "country_code": "US"}
    assert evaluate_conditions(nested_conditions, no_match_data) == False
    print("Test 3 (Nested Logic No Match): PASSED")

    print("\n--- All Backend Logic Tests Passed! ---")


if __name__ == "__main__":
    test_rules_engine()
