"""
Monitoring Rules Management API
Create, update, and manage transaction monitoring rules.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime
import uuid

from src.database import get_db
from src.models.transaction_models import MonitoringRule, Alert
from src.models.models import LegalDocument
from src.schemas.transaction_schemas import (
    MonitoringRuleCreate, MonitoringRuleUpdate, MonitoringRuleResponse
)
from src.services.rules_engine import RuleBuilder

router = APIRouter(prefix="/api/monitoring-rules", tags=["monitoring-rules"])


# ============================================================================
# RULE MANAGEMENT
# ============================================================================

@router.post("/", response_model=MonitoringRuleResponse, status_code=201)
def create_rule(
    rule: MonitoringRuleCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new monitoring rule.

    Supports custom rule logic with JSON-based DSL.
    """
    # Generate rule ID
    rule_id = f"RULE-{uuid.uuid4().hex[:8].upper()}"

    # Validate conditions
    if not rule.conditions or 'conditions' not in rule.conditions:
        raise HTTPException(
            status_code=400,
            detail="Rule must have valid conditions object with 'conditions' array"
        )

    # Create rule
    db_rule = MonitoringRule(
        rule_id=rule_id,
        **rule.dict()
    )

    db.add(db_rule)
    db.commit()
    db.refresh(db_rule)

    return db_rule


@router.get("/", response_model=List[MonitoringRuleResponse])
def list_rules(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    enabled: Optional[bool] = None,
    category: Optional[str] = None,
    severity: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    List monitoring rules with filtering.
    """
    query = db.query(MonitoringRule)

    if enabled is not None:
        query = query.filter(MonitoringRule.enabled == enabled)

    if category:
        query = query.filter(MonitoringRule.category == category)

    if severity:
        query = query.filter(MonitoringRule.severity == severity)

    # Order by alert count descending (most triggered first)
    query = query.order_by(MonitoringRule.alert_count.desc())

    rules = query.offset(skip).limit(limit).all()

    return rules


@router.get("/{rule_id}", response_model=MonitoringRuleResponse)
def get_rule(
    rule_id: str,
    db: Session = Depends(get_db)
):
    """Get a single rule by ID."""
    rule = db.query(MonitoringRule).filter(
        MonitoringRule.rule_id == rule_id
    ).first()

    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    return rule


@router.patch("/{rule_id}", response_model=MonitoringRuleResponse)
def update_rule(
    rule_id: str,
    update_data: MonitoringRuleUpdate,
    db: Session = Depends(get_db)
):
    """
    Update a monitoring rule.

    Can update conditions, thresholds, severity, and regulatory linkage.
    """
    rule = db.query(MonitoringRule).filter(
        MonitoringRule.rule_id == rule_id
    ).first()

    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    # Update fields
    update_dict = update_data.dict(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(rule, field, value)

    # Increment version if conditions changed
    if 'conditions' in update_dict or 'thresholds' in update_dict:
        rule.version += 1

    rule.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(rule)

    return rule


@router.delete("/{rule_id}")
def delete_rule(
    rule_id: str,
    db: Session = Depends(get_db)
):
    """
    Delete a monitoring rule.

    This permanently removes the rule. Consider disabling instead.
    """
    rule = db.query(MonitoringRule).filter(
        MonitoringRule.rule_id == rule_id
    ).first()

    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    db.delete(rule)
    db.commit()

    return {"status": "deleted", "rule_id": rule_id}


# ============================================================================
# RULE OPERATIONS
# ============================================================================

@router.post("/{rule_id}/enable")
def enable_rule(
    rule_id: str,
    db: Session = Depends(get_db)
):
    """Enable a monitoring rule."""
    rule = db.query(MonitoringRule).filter(
        MonitoringRule.rule_id == rule_id
    ).first()

    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    rule.enabled = True
    rule.updated_at = datetime.utcnow()
    db.commit()

    return {"status": "enabled", "rule_id": rule_id}


@router.post("/{rule_id}/disable")
def disable_rule(
    rule_id: str,
    db: Session = Depends(get_db)
):
    """Disable a monitoring rule."""
    rule = db.query(MonitoringRule).filter(
        MonitoringRule.rule_id == rule_id
    ).first()

    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    rule.enabled = False
    rule.updated_at = datetime.utcnow()
    db.commit()

    return {"status": "disabled", "rule_id": rule_id}


@router.post("/{rule_id}/test")
def test_rule(
    rule_id: str,
    transaction_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Test a rule against a transaction or sample data.

    Returns whether the rule would trigger and why.
    """
    from src.services.rules_engine import RulesEngine
    from src.models.transaction_models import Transaction

    rule = db.query(MonitoringRule).filter(
        MonitoringRule.rule_id == rule_id
    ).first()

    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    if transaction_id:
        # Test against specific transaction
        transaction = db.query(Transaction).filter(
            Transaction.id == transaction_id
        ).first()

        if not transaction:
            raise HTTPException(status_code=404, detail="Transaction not found")

        engine = RulesEngine(db)
        would_trigger = engine._evaluate_rule(transaction, rule)

        return {
            "rule_id": rule_id,
            "transaction_id": transaction.transaction_id,
            "would_trigger": would_trigger,
            "rule_conditions": rule.conditions
        }
    else:
        # Return rule structure for testing
        return {
            "rule_id": rule_id,
            "rule_structure": {
                "conditions": rule.conditions,
                "thresholds": rule.thresholds,
                "category": rule.category,
                "severity": rule.severity
            },
            "note": "Provide transaction_id parameter to test against actual transaction"
        }


# ============================================================================
# RULE TEMPLATES & BUILDERS
# ============================================================================

@router.post("/templates/amount-threshold", response_model=MonitoringRuleResponse)
def create_amount_threshold_rule(
    name: str,
    amount_limit: float,
    currency: str = "EUR",
    severity: str = "medium",
    regulatory_source_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Create a rule from amount threshold template.

    Quick way to create transaction amount monitoring rules.
    """
    rule_data = RuleBuilder.create_transaction_limit_rule(
        name=name,
        amount_limit=amount_limit,
        currency=currency,
        severity=severity,
        regulatory_source_id=regulatory_source_id
    )

    rule_id = f"RULE-AMT-{uuid.uuid4().hex[:8].upper()}"

    db_rule = MonitoringRule(
        rule_id=rule_id,
        **rule_data
    )

    db.add(db_rule)
    db.commit()
    db.refresh(db_rule)

    return db_rule


@router.post("/templates/high-risk-country", response_model=MonitoringRuleResponse)
def create_high_risk_country_rule(
    name: str,
    country_codes: List[str],
    severity: str = "high",
    regulatory_source_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Create a rule for high-risk jurisdiction monitoring.

    Example: Sanctions compliance, FATF grey list
    """
    rule_data = RuleBuilder.create_high_risk_country_rule(
        name=name,
        country_codes=country_codes,
        severity=severity,
        regulatory_source_id=regulatory_source_id
    )

    rule_id = f"RULE-GEO-{uuid.uuid4().hex[:8].upper()}"

    db_rule = MonitoringRule(
        rule_id=rule_id,
        **rule_data
    )

    db.add(db_rule)
    db.commit()
    db.refresh(db_rule)

    return db_rule


@router.post("/templates/velocity", response_model=MonitoringRuleResponse)
def create_velocity_rule(
    name: str,
    max_transactions: int,
    time_window_hours: int = 24,
    severity: str = "medium",
    regulatory_source_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Create a velocity rule for transaction frequency monitoring.
    """
    rule_data = RuleBuilder.create_velocity_rule(
        name=name,
        max_transactions=max_transactions,
        time_window_hours=time_window_hours,
        severity=severity,
        regulatory_source_id=regulatory_source_id
    )

    rule_id = f"RULE-VEL-{uuid.uuid4().hex[:8].upper()}"

    db_rule = MonitoringRule(
        rule_id=rule_id,
        **rule_data
    )

    db.add(db_rule)
    db.commit()
    db.refresh(db_rule)

    return db_rule


# ============================================================================
# RULE PERFORMANCE & ANALYTICS
# ============================================================================

@router.get("/{rule_id}/performance")
def get_rule_performance(
    rule_id: str,
    db: Session = Depends(get_db)
):
    """
    Get performance metrics for a rule.

    Includes:
    - Total alerts generated
    - True positive rate
    - False positive rate
    - Recent alerts
    """
    rule = db.query(MonitoringRule).filter(
        MonitoringRule.rule_id == rule_id
    ).first()

    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    # Get alerts for this rule
    alerts = db.query(Alert).filter(
        Alert.rule_id == rule_id
    ).all()

    # Calculate metrics
    total_alerts = len(alerts)
    false_positives = sum(1 for a in alerts if a.resolution_status == 'false_positive')
    confirmed = sum(1 for a in alerts if a.resolution_status == 'confirmed')
    resolved = sum(1 for a in alerts if a.status in ['resolved', 'false_positive'])

    fp_rate = (false_positives / total_alerts * 100) if total_alerts > 0 else 0
    tp_rate = (confirmed / total_alerts * 100) if total_alerts > 0 else 0

    return {
        "rule_id": rule_id,
        "rule_name": rule.name,
        "total_alerts": total_alerts,
        "alerts_resolved": resolved,
        "false_positives": false_positives,
        "confirmed_positives": confirmed,
        "false_positive_rate": round(fp_rate, 2),
        "true_positive_rate": round(tp_rate, 2),
        "enabled": rule.enabled,
        "last_triggered": max([a.created_at for a in alerts]) if alerts else None
    }


@router.get("/statistics/overview")
def get_rules_statistics(db: Session = Depends(get_db)):
    """
    Get overall monitoring rules statistics.
    """
    total_rules = db.query(func.count(MonitoringRule.id)).scalar() or 0

    enabled_rules = db.query(func.count(MonitoringRule.id)).filter(
        MonitoringRule.enabled == True
    ).scalar() or 0

    # Rules by category
    category_results = db.query(
        MonitoringRule.category,
        func.count(MonitoringRule.id).label('count')
    ).group_by(MonitoringRule.category).all()

    rules_by_category = {row.category or 'uncategorized': row.count for row in category_results}

    # Rules by severity
    severity_results = db.query(
        MonitoringRule.severity,
        func.count(MonitoringRule.id).label('count')
    ).group_by(MonitoringRule.severity).all()

    rules_by_severity = {row.severity: row.count for row in severity_results}

    # Rules with regulatory linkage
    rules_with_regulations = db.query(func.count(MonitoringRule.id)).filter(
        MonitoringRule.regulatory_source_id.isnot(None)
    ).scalar() or 0

    # Total alerts generated
    total_alerts = db.query(func.count(Alert.id)).scalar() or 0

    return {
        "total_rules": total_rules,
        "enabled_rules": enabled_rules,
        "disabled_rules": total_rules - enabled_rules,
        "rules_by_category": rules_by_category,
        "rules_by_severity": rules_by_severity,
        "rules_with_regulatory_linkage": rules_with_regulations,
        "regulatory_linkage_rate": (rules_with_regulations / total_rules * 100) if total_rules > 0 else 0,
        "total_alerts_generated": total_alerts
    }


@router.get("/performance/top-performers")
def get_top_performing_rules(
    limit: int = Query(10, ge=1, le=50),
    metric: str = Query("alert_count", regex="^(alert_count|true_positive_rate)$"),
    db: Session = Depends(get_db)
):
    """
    Get top-performing rules by alert count or accuracy.
    """
    if metric == "alert_count":
        rules = db.query(MonitoringRule).order_by(
            MonitoringRule.alert_count.desc()
        ).limit(limit).all()
    else:
        rules = db.query(MonitoringRule).filter(
            MonitoringRule.true_positive_rate.isnot(None)
        ).order_by(
            MonitoringRule.true_positive_rate.desc()
        ).limit(limit).all()

    return [
        {
            "rule_id": rule.rule_id,
            "name": rule.name,
            "category": rule.category,
            "alert_count": rule.alert_count,
            "true_positive_rate": float(rule.true_positive_rate) if rule.true_positive_rate else None,
            "enabled": rule.enabled
        }
        for rule in rules
    ]


# ============================================================================
# BULK OPERATIONS
# ============================================================================

@router.post("/bulk/enable")
def bulk_enable_rules(
    rule_ids: List[str],
    db: Session = Depends(get_db)
):
    """Enable multiple rules at once."""
    rules = db.query(MonitoringRule).filter(
        MonitoringRule.rule_id.in_(rule_ids)
    ).all()

    for rule in rules:
        rule.enabled = True
        rule.updated_at = datetime.utcnow()

    db.commit()

    return {
        "status": "success",
        "enabled_count": len(rules),
        "rule_ids": [r.rule_id for r in rules]
    }


@router.post("/bulk/disable")
def bulk_disable_rules(
    rule_ids: List[str],
    db: Session = Depends(get_db)
):
    """Disable multiple rules at once."""
    rules = db.query(MonitoringRule).filter(
        MonitoringRule.rule_id.in_(rule_ids)
    ).all()

    for rule in rules:
        rule.enabled = False
        rule.updated_at = datetime.utcnow()

    db.commit()

    return {
        "status": "success",
        "disabled_count": len(rules),
        "rule_ids": [r.rule_id for r in rules]
    }


@router.post("/bulk/update-severity")
def bulk_update_severity(
    rule_ids: List[str],
    new_severity: str,
    db: Session = Depends(get_db)
):
    """Update severity for multiple rules."""
    if new_severity not in ['low', 'medium', 'high', 'critical']:
        raise HTTPException(status_code=400, detail="Invalid severity level")

    rules = db.query(MonitoringRule).filter(
        MonitoringRule.rule_id.in_(rule_ids)
    ).all()

    for rule in rules:
        rule.severity = new_severity
        rule.updated_at = datetime.utcnow()

    db.commit()

    return {
        "status": "success",
        "updated_count": len(rules),
        "new_severity": new_severity
    }
