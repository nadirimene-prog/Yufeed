import operator
import re
import logging
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta
from decimal import Decimal

logger = logging.getLogger(__name__)

class RuleEngine:
    """
    Sardine-inspired Rule Engine for evaluating transaction monitoring rules.
    Supports nested logical conditions and aggregations.
    """
    
    OPERATORS = {
        "==": operator.eq,
        "!=": operator.ne,
        ">": operator.gt,
        "<": operator.lt,
        ">=": operator.ge,
        "<=": operator.le,
        "contains": lambda a, b: b in a if a else False,
        "in": lambda a, b: a in b if b else False,
        "matches": lambda a, b: bool(re.match(b, a)) if a and b else False,
    }

    @classmethod
    def evaluate_condition(cls, condition: Dict[str, Any], data: Dict[str, Any]) -> bool:
        """
        Evaluates a single condition or a nested logical group.
        Example condition: {"field": "amount", "operator": ">", "value": 1000}
        Example group: {"logic": "AND", "conditions": [...]}
        """
        if "logic" in condition:
            logic = condition["logic"].upper()
            sub_conditions = condition.get("conditions", [])
            
            if not sub_conditions:
                return True # Vacuously true
            
            results = [cls.evaluate_condition(c, data) for c in sub_conditions]
            
            if logic == "AND":
                return all(results)
            elif logic == "OR":
                return any(results)
            else:
                raise ValueError(f"Unsupported logic operator: {logic}")
        
        # Single condition evaluation
        field = condition.get("field")
        op_str = condition.get("operator")
        target_value = condition.get("value")
        
        if not field or not op_str:
            return False
        
        actual_value = data.get(field)
        
        # Type conversion for comparison
        if isinstance(target_value, (int, float)) and actual_value is not None:
            actual_value = float(actual_value)
            target_value = float(target_value)
        elif isinstance(actual_value, Decimal):
            actual_value = float(actual_value)
            target_value = float(target_value)
            
        op_func = cls.OPERATORS.get(op_str)
        if not op_func:
            raise ValueError(f"Unsupported operator: {op_str}")
            
        try:
            return op_func(actual_value, target_value)
        except Exception:
            return False

    @classmethod
    def match_rule(cls, rule_conditions: Dict[str, Any], transaction_data: Dict[str, Any]) -> bool:
        """
        Main entry point for rule matching.
        """
        try:
            return cls.evaluate_condition(rule_conditions, transaction_data)
        except Exception as e:
            logger.error(f"Rule evaluation error: {e}", exc_info=True)
            return False

# Example usage/test placeholder
if __name__ == "__main__":
    test_data = {
        "amount": 1500,
        "currency": "USD",
        "country_code": "US",
        "tx_type": "withdrawal"
    }
    
    test_rule = {
        "logic": "AND",
        "conditions": [
            {"field": "amount", "operator": ">", "value": 1000},
            {"logic": "OR", "conditions": [
                {"field": "country_code", "operator": "!=", "value": "US"},
                {"field": "tx_type", "operator": "==", "value": "withdrawal"}
            ]}
        ]
    }
    
    engine = RuleEngine()
    print(f"Match result: {engine.match_rule(test_rule, test_data)}") # Should be True
