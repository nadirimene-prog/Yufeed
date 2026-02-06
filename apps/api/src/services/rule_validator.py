"""
Rule validation utilities.

Validates rule DSL structure at creation/version submission time to prevent
runtime coercion errors and invalid field/operator combinations.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import math
from typing import Any, Dict, List, Literal, Optional

import sqlalchemy as sa

from src.models.transaction_models import Transaction


FieldCategory = Literal["numeric", "string", "datetime", "boolean", "other"]


@dataclass(frozen=True)
class RuleValidationIssue:
    path: str
    message: str


class RuleValidator:
    """Validate rule DSL against known Transaction fields and operator semantics."""

    _OPERATOR_ALIASES: Dict[str, str] = {
        "==": "equals",
        "=": "equals",
        "!=": "not_equals",
        ">": "greater_than",
        ">=": "greater_than_or_equal",
        "<": "less_than",
        "<=": "less_than_or_equal",
    }

    _NUMERIC_OPERATORS = {
        "greater_than",
        "less_than",
        "greater_than_or_equal",
        "less_than_or_equal",
    }
    _STRING_OPERATORS = {"contains", "starts_with", "ends_with"}
    _SET_OPERATORS = {"in", "not_in"}
    _EQUALITY_OPERATORS = {"equals", "not_equals"}

    _ALLOWED_LOGIC = {"AND", "OR"}

    @classmethod
    def validate(cls, conditions: Any) -> List[RuleValidationIssue]:
        issues: List[RuleValidationIssue] = []

        if not isinstance(conditions, dict):
            return [RuleValidationIssue(path="conditions", message="Must be an object")]

        logic = (conditions.get("logic") or "AND").upper()
        if logic not in cls._ALLOWED_LOGIC:
            issues.append(RuleValidationIssue(path="conditions.logic", message="Must be AND or OR"))

        conds = conditions.get("conditions")
        if not isinstance(conds, list) or not conds:
            issues.append(
                RuleValidationIssue(
                    path="conditions.conditions",
                    message="Must be a non-empty array of conditions",
                )
            )
            return issues

        field_categories = cls._transaction_field_categories()

        for idx, cond in enumerate(conds):
            path_prefix = f"conditions.conditions[{idx}]"
            if not isinstance(cond, dict):
                issues.append(RuleValidationIssue(path=path_prefix, message="Must be an object"))
                continue

            field = cond.get("field")
            operator = cond.get("operator")
            has_value_key = "value" in cond
            value = cond.get("value") if has_value_key else None

            if not field or not isinstance(field, str):
                issues.append(RuleValidationIssue(path=f"{path_prefix}.field", message="Field is required"))
                continue

            if field not in field_categories:
                issues.append(
                    RuleValidationIssue(
                        path=f"{path_prefix}.field",
                        message=f"Unknown field '{field}' (must exist on Transaction)",
                    )
                )
                continue

            if not operator or not isinstance(operator, str):
                issues.append(
                    RuleValidationIssue(
                        path=f"{path_prefix}.operator",
                        message="Operator is required",
                    )
                )
                continue

            normalized_op = cls._OPERATOR_ALIASES.get(operator, operator)
            category = field_categories[field]

            # Enforce value presence for all current operators.
            if normalized_op not in cls._EQUALITY_OPERATORS and not has_value_key:
                issues.append(RuleValidationIssue(path=f"{path_prefix}.value", message="Value is required"))
                continue

            if normalized_op in cls._NUMERIC_OPERATORS:
                if category != "numeric":
                    issues.append(
                        RuleValidationIssue(
                            path=f"{path_prefix}.operator",
                            message=f"Operator '{operator}' requires numeric field",
                        )
                    )
                elif not cls._is_numeric(value):
                    issues.append(
                        RuleValidationIssue(
                            path=f"{path_prefix}.value",
                            message="Must be numeric",
                        )
                    )

            elif normalized_op in cls._STRING_OPERATORS:
                if category != "string":
                    issues.append(
                        RuleValidationIssue(
                            path=f"{path_prefix}.operator",
                            message=f"Operator '{operator}' requires string field",
                        )
                    )
                elif not isinstance(value, str):
                    issues.append(RuleValidationIssue(path=f"{path_prefix}.value", message="Must be a string"))

            elif normalized_op in cls._SET_OPERATORS:
                if not isinstance(value, list) or not value:
                    issues.append(
                        RuleValidationIssue(
                            path=f"{path_prefix}.value",
                            message="Must be a non-empty array",
                        )
                    )
                else:
                    element_issues = cls._validate_list_elements(value, category)
                    if element_issues:
                        issues.append(
                            RuleValidationIssue(
                                path=f"{path_prefix}.value",
                                message=element_issues,
                            )
                        )

            elif normalized_op in cls._EQUALITY_OPERATORS:
                if category == "numeric" and not cls._is_numeric(value):
                    issues.append(RuleValidationIssue(path=f"{path_prefix}.value", message="Must be numeric"))
                if category == "string" and not isinstance(value, str):
                    issues.append(RuleValidationIssue(path=f"{path_prefix}.value", message="Must be a string"))
            else:
                issues.append(
                    RuleValidationIssue(
                        path=f"{path_prefix}.operator",
                        message=f"Unknown operator '{operator}'",
                    )
                )

        return issues

    @classmethod
    def _transaction_field_categories(cls) -> Dict[str, FieldCategory]:
        categories: Dict[str, FieldCategory] = {}
        for column in Transaction.__table__.columns:  # type: ignore[attr-defined]
            categories[column.name] = cls._classify_column(column)
        return categories

    @staticmethod
    def _classify_column(column: sa.Column) -> FieldCategory:
        col_type = column.type
        # SQLAlchemy variants wrap types but preserve isinstance checks.
        if isinstance(col_type, (sa.Integer, sa.Numeric, sa.Float)):
            return "numeric"
        if isinstance(col_type, (sa.String, sa.Text)):
            return "string"
        if isinstance(col_type, sa.DateTime):
            return "datetime"
        if isinstance(col_type, sa.Boolean):
            return "boolean"
        return "other"

    @staticmethod
    def _is_numeric(value: Any) -> bool:
        if value is None:
            return False
        if isinstance(value, bool):
            return False
        if isinstance(value, (int, float, Decimal)):
            try:
                return math.isfinite(float(value))
            except Exception:
                return False
        if isinstance(value, str):
            try:
                return math.isfinite(float(value))
            except Exception:
                return False
        return False

    @classmethod
    def _validate_list_elements(cls, value: List[Any], category: FieldCategory) -> Optional[str]:
        if category == "numeric":
            if not all(cls._is_numeric(v) for v in value):
                return "All values must be numeric"
        elif category == "string":
            if not all(isinstance(v, str) for v in value):
                return "All values must be strings"
        return None

