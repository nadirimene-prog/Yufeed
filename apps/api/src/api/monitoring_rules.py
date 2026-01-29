"""
Monitoring Rules Management API
Create, update, and manage transaction monitoring rules.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime, timezone


def utc_now() -> datetime:
    """Return current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)
import uuid

from src.database import get_db
from src.auth.dependencies import require_any_role, CurrentUser
from src.models.transaction_models import MonitoringRule, Alert, RuleVersion
from src.audit.models import AuditLog
from src.models.models import LegalDocument
from src.tenancy.queries import get_tenant_filtered_query, set_tenant_on_create, ensure_tenant_match, require_tenant
from src.schemas.transaction_schemas import (
    MonitoringRuleCreate,
    MonitoringRuleUpdate,
    MonitoringRuleResponse,
    RuleVersionCreate,
    RuleVersionResponse,
    RuleSimulationRequest,
    RuleSimulationResponse,
    RuleBacktestRequest,
    RuleBacktestResponse,
    RuleBacktestSample,
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
        name=rule.name,
        description=rule.description,
        category=rule.category,
        severity=rule.severity,
        conditions=rule.conditions,
        thresholds=rule.thresholds,
        regulatory_source_id=rule.regulatory_source_id,
        regulation_article=rule.regulation_article,
        regulatory_requirement=rule.regulatory_requirement,
        enabled=rule.enabled,
    )

    # Phase 4C: Set tenant context on new rule
    set_tenant_on_create(db_rule)

    db.add(db_rule)
    db.commit()
    db.refresh(db_rule)

    version = RuleVersion(
        rule_id=db_rule.id,
        version_number=db_rule.version,
        status="approved",
        name=db_rule.name,
        description=db_rule.description,
        category=db_rule.category,
        severity=db_rule.severity,
        priority=db_rule.priority,
        conditions=db_rule.conditions,
        thresholds=db_rule.thresholds,
        enabled=db_rule.enabled,
        created_by=db_rule.created_by,
        approved_by=db_rule.created_by,
        approved_at=utc_now(),
    )
    db.add(version)
    db.commit()

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
    # Phase 4C: Tenant-filtered query
    query = get_tenant_filtered_query(MonitoringRule, db)

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
    db: Session = Depends(get_db),
    tenant_id: str = Depends(require_tenant)
):
    """Get a single rule by ID."""
    # Phase 4C: Tenant-filtered query
    rule = get_tenant_filtered_query(MonitoringRule, db).filter(
        MonitoringRule.rule_id == rule_id
    ).first()

    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    # Phase 4C: Ensure tenant match
    ensure_tenant_match(rule, tenant_id)

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
    raise HTTPException(
        status_code=403,
        detail="Direct edits are disabled. Submit a rule version for approval."
    )


@router.delete("/{rule_id}")
def delete_rule(
    rule_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(require_tenant)
):
    """
    Delete a monitoring rule.

    This permanently removes the rule. Consider disabling instead.
    """
    # Phase 4C: Tenant-filtered query
    rule = get_tenant_filtered_query(MonitoringRule, db).filter(
        MonitoringRule.rule_id == rule_id
    ).first()

    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    # Phase 4C: Ensure tenant match
    ensure_tenant_match(rule, tenant_id)

    db.delete(rule)
    db.commit()

    return {"status": "deleted", "rule_id": rule_id}


# ============================================================================
# RULE OPERATIONS
# ============================================================================

@router.post("/{rule_id}/enable")
def enable_rule(
    rule_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(require_tenant)
):
    """Enable a monitoring rule."""
    # Phase 4C: Tenant-filtered query
    rule = get_tenant_filtered_query(MonitoringRule, db).filter(
        MonitoringRule.rule_id == rule_id
    ).first()

    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    # Phase 4C: Ensure tenant match
    ensure_tenant_match(rule, tenant_id)

    rule.enabled = True
    rule.updated_at = utc_now()
    db.commit()

    return {"status": "enabled", "rule_id": rule_id}


@router.post("/{rule_id}/disable")
def disable_rule(
    rule_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(require_tenant)
):
    """Disable a monitoring rule."""
    # Phase 4C: Tenant-filtered query
    rule = get_tenant_filtered_query(MonitoringRule, db).filter(
        MonitoringRule.rule_id == rule_id
    ).first()

    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    # Phase 4C: Ensure tenant match
    ensure_tenant_match(rule, tenant_id)

    rule.enabled = False
    rule.updated_at = utc_now()
    db.commit()

    return {"status": "disabled", "rule_id": rule_id}


@router.post("/{rule_id}/test")
def test_rule(
    rule_id: str,
    transaction_id: Optional[int] = None,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(require_tenant)
):
    """
    Test a rule against a transaction or sample data.

    Returns whether the rule would trigger and why.
    """
    from src.services.rules_engine import RulesEngine
    from src.models.transaction_models import Transaction

    # Phase 4C: Tenant-filtered query
    rule = get_tenant_filtered_query(MonitoringRule, db).filter(
        MonitoringRule.rule_id == rule_id
    ).first()

    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    # Phase 4C: Ensure tenant match
    ensure_tenant_match(rule, tenant_id)

    if transaction_id:
        # Phase 4C: Test against specific transaction (tenant-filtered)
        transaction = get_tenant_filtered_query(Transaction, db).filter(
            Transaction.id == transaction_id
        ).first()

        if not transaction:
            raise HTTPException(status_code=404, detail="Transaction not found")

        # Phase 4C: Ensure transaction belongs to same tenant
        ensure_tenant_match(transaction, tenant_id)

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
# RULE VERSIONING & APPROVALS
# ============================================================================

@router.get("/{rule_id}/versions", response_model=List[RuleVersionResponse])
def list_rule_versions(
    rule_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(require_tenant)
):
    # Phase 4C: Tenant-filtered query
    rule = get_tenant_filtered_query(MonitoringRule, db).filter(
        MonitoringRule.rule_id == rule_id
    ).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    # Phase 4C: Ensure tenant match
    ensure_tenant_match(rule, tenant_id)

    versions = db.query(RuleVersion).filter(
        RuleVersion.rule_id == rule.id
    ).order_by(RuleVersion.version_number.desc()).all()

    return versions


@router.get("/versions", response_model=List[RuleVersionResponse])
def list_versions(
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(RuleVersion)
    if status:
        query = query.filter(RuleVersion.status == status)
    return query.order_by(RuleVersion.created_at.desc()).all()


@router.post("/{rule_id}/versions", response_model=RuleVersionResponse)
def create_rule_version(
    rule_id: str,
    request: RuleVersionCreate,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer", "auditor", "user"])),
    tenant_id: str = Depends(require_tenant)
):
    # Phase 4C: Tenant-filtered query
    rule = get_tenant_filtered_query(MonitoringRule, db).filter(
        MonitoringRule.rule_id == rule_id
    ).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    # Phase 4C: Ensure tenant match
    ensure_tenant_match(rule, tenant_id)

    next_version = rule.version + 1
    version = RuleVersion(
        rule_id=rule.id,
        version_number=next_version,
        status="pending",
        name=request.name or rule.name,
        description=request.description if request.description is not None else rule.description,
        category=request.category if request.category is not None else rule.category,
        severity=request.severity if request.severity is not None else rule.severity,
        priority=rule.priority,
        conditions=request.conditions if request.conditions is not None else rule.conditions,
        thresholds=request.thresholds if request.thresholds is not None else rule.thresholds,
        enabled=request.enabled if request.enabled is not None else rule.enabled,
        created_by=rule.created_by,
        notes=request.notes,
    )
    db.add(version)
    db.commit()
    db.refresh(version)

    audit_entry = AuditLog(
        audit_id=uuid.uuid4().hex,
        actor_id=_.user_id,
        actor_email=_.email,
        actor_role=_.role,
        actor_type="user",
        action="submit",
        method="POST",
        path=f"/api/monitoring-rules/{rule_id}/versions",
        entity_type="rule_version",
        entity_id=str(version.id),
        status_code=200,
        changes={"notes": request.notes, "version_number": version.version_number},
        metadata_json={"rule_id": rule_id},
    )
    db.add(audit_entry)
    db.commit()

    return version


@router.post("/versions/{version_id}/approve", response_model=RuleVersionResponse)
def approve_rule_version(
    version_id: int,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer"])),
    tenant_id: str = Depends(require_tenant)
):
    version = db.query(RuleVersion).filter(
        RuleVersion.id == version_id
    ).first()
    if not version:
        raise HTTPException(status_code=404, detail="Rule version not found")
    if version.status != "pending":
        raise HTTPException(status_code=400, detail="Rule version is not pending")

    # Phase 4C: Tenant-filtered query for the associated rule
    rule = get_tenant_filtered_query(MonitoringRule, db).filter(
        MonitoringRule.id == version.rule_id
    ).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    # Phase 4C: Ensure tenant match
    ensure_tenant_match(rule, tenant_id)

    rule.name = version.name
    rule.description = version.description
    rule.category = version.category
    rule.severity = version.severity
    rule.priority = version.priority
    rule.conditions = version.conditions
    rule.thresholds = version.thresholds
    rule.enabled = version.enabled
    rule.version = version.version_number
    rule.updated_at = utc_now()

    version.status = "approved"
    version.approved_at = utc_now()

    db.commit()
    db.refresh(version)

    audit_entry = AuditLog(
        audit_id=uuid.uuid4().hex,
        actor_id=_.user_id,
        actor_email=_.email,
        actor_role=_.role,
        actor_type="user",
        action="approve",
        method="POST",
        path=f"/api/monitoring-rules/versions/{version_id}/approve",
        entity_type="rule_version",
        entity_id=str(version.id),
        status_code=200,
        changes={"status": "approved", "version_number": version.version_number},
        metadata_json={"rule_id": rule.rule_id},
    )
    db.add(audit_entry)
    db.commit()

    return version


@router.post("/versions/{version_id}/reject", response_model=RuleVersionResponse)
def reject_rule_version(
    version_id: int,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer"]))
):
    version = db.query(RuleVersion).filter(
        RuleVersion.id == version_id
    ).first()
    if not version:
        raise HTTPException(status_code=404, detail="Rule version not found")
    if version.status != "pending":
        raise HTTPException(status_code=400, detail="Rule version is not pending")

    version.status = "rejected"
    version.approved_at = utc_now()
    db.commit()
    db.refresh(version)

    audit_entry = AuditLog(
        audit_id=uuid.uuid4().hex,
        actor_id=_.user_id,
        actor_email=_.email,
        actor_role=_.role,
        actor_type="user",
        action="reject",
        method="POST",
        path=f"/api/monitoring-rules/versions/{version_id}/reject",
        entity_type="rule_version",
        entity_id=str(version.id),
        status_code=200,
        changes={"status": "rejected", "version_number": version.version_number},
        metadata_json={"rule_id": rule.rule_id},
    )
    db.add(audit_entry)
    db.commit()

    return version


@router.post("/{rule_id}/simulate", response_model=RuleSimulationResponse)
def simulate_rule(
    rule_id: str,
    request: RuleSimulationRequest,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(require_tenant)
):
    """
    Simulate a rule against a payload or an existing transaction.

    Returns condition-level evaluation without creating alerts.
    """
    from src.services.rules_engine import RulesEngine
    from src.models.transaction_models import Transaction

    # Phase 4C: Tenant-filtered query
    rule = get_tenant_filtered_query(MonitoringRule, db).filter(
        MonitoringRule.rule_id == rule_id
    ).first()

    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    # Phase 4C: Ensure tenant match
    ensure_tenant_match(rule, tenant_id)

    engine = RulesEngine(db)

    if request.transaction_id is not None:
        # Phase 4C: Tenant-filtered transaction query
        transaction = get_tenant_filtered_query(Transaction, db).filter(
            Transaction.id == request.transaction_id
        ).first()

        if not transaction:
            raise HTTPException(status_code=404, detail="Transaction not found")

        # Phase 4C: Ensure transaction belongs to same tenant
        ensure_tenant_match(transaction, tenant_id)

        would_trigger, condition_results, logic = engine.evaluate_rule_details(transaction, rule)
        transaction_id = transaction.transaction_id
    else:
        would_trigger, condition_results, logic = engine.simulate_rule(rule, request.payload)
        transaction_id = None

    return RuleSimulationResponse(
        rule_id=rule_id,
        transaction_id=transaction_id,
        would_trigger=would_trigger,
        logic=logic,
        condition_results=condition_results,
        evaluated_at=utc_now()
    )


@router.post("/{rule_id}/backtest", response_model=RuleBacktestResponse)
def backtest_rule(
    rule_id: str,
    request: RuleBacktestRequest,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(require_tenant)
):
    """
    Backtest a rule across historical transactions.

    Returns summary stats and sample matched transactions.
    """
    from src.services.rules_engine import RulesEngine
    from src.models.transaction_models import Transaction

    # Phase 4C: Tenant-filtered query
    rule = get_tenant_filtered_query(MonitoringRule, db).filter(
        MonitoringRule.rule_id == rule_id
    ).first()

    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    # Phase 4C: Ensure tenant match
    ensure_tenant_match(rule, tenant_id)

    # Phase 4C: Tenant-filtered transaction query for backtest
    query = get_tenant_filtered_query(Transaction, db)
    if request.start_date:
        query = query.filter(Transaction.timestamp >= request.start_date)
    if request.end_date:
        query = query.filter(Transaction.timestamp <= request.end_date)

    transactions = query.order_by(Transaction.timestamp.desc()).limit(request.limit).all()

    engine = RulesEngine(db)

    matches = 0
    samples: List[RuleBacktestSample] = []

    for transaction in transactions:
        would_trigger = engine._evaluate_rule(transaction, rule)
        if would_trigger:
            matches += 1
            if len(samples) < request.sample_size:
                samples.append(RuleBacktestSample(
                    transaction_id=transaction.transaction_id,
                    amount=transaction.amount,
                    currency=transaction.currency,
                    transaction_type=transaction.transaction_type,
                    country_code=transaction.country_code,
                    timestamp=transaction.timestamp,
                    would_trigger=would_trigger
                ))

    total = len(transactions)
    match_rate = (matches / total * 100) if total > 0 else 0.0

    return RuleBacktestResponse(
        rule_id=rule_id,
        total_transactions=total,
        matches=matches,
        match_rate=round(match_rate, 2),
        evaluated_at=utc_now(),
        window={
            "start_date": request.start_date,
            "end_date": request.end_date
        },
        samples=samples
    )


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

    # Phase 4C: Set tenant context on new rule
    set_tenant_on_create(db_rule)

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

    # Phase 4C: Set tenant context on new rule
    set_tenant_on_create(db_rule)

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
    db: Session = Depends(get_db),
    tenant_id: str = Depends(require_tenant)
):
    """
    Get performance metrics for a rule.

    Includes:
    - Total alerts generated
    - True positive rate
    - False positive rate
    - Recent alerts
    """
    # Phase 4C: Tenant-filtered query
    rule = get_tenant_filtered_query(MonitoringRule, db).filter(
        MonitoringRule.rule_id == rule_id
    ).first()

    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    # Phase 4C: Ensure tenant match
    ensure_tenant_match(rule, tenant_id)

    # Phase 4C: Get alerts for this rule (tenant-filtered)
    alerts = get_tenant_filtered_query(Alert, db).filter(
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
    # Phase 4C: Use tenant-filtered queries for statistics
    total_rules = get_tenant_filtered_query(MonitoringRule, db).count() or 0

    enabled_rules = get_tenant_filtered_query(MonitoringRule, db).filter(
        MonitoringRule.enabled == True
    ).count() or 0

    # Phase 4C: Rules by category (tenant-filtered)
    category_results = get_tenant_filtered_query(MonitoringRule, db).with_entities(
        MonitoringRule.category,
        func.count(MonitoringRule.id).label('count')
    ).group_by(MonitoringRule.category).all()

    rules_by_category = {row.category or 'uncategorized': row.count for row in category_results}

    # Phase 4C: Rules by severity (tenant-filtered)
    severity_results = get_tenant_filtered_query(MonitoringRule, db).with_entities(
        MonitoringRule.severity,
        func.count(MonitoringRule.id).label('count')
    ).group_by(MonitoringRule.severity).all()

    rules_by_severity = {row.severity: row.count for row in severity_results}

    # Phase 4C: Rules with regulatory linkage (tenant-filtered)
    rules_with_regulations = get_tenant_filtered_query(MonitoringRule, db).filter(
        MonitoringRule.regulatory_source_id.isnot(None)
    ).count() or 0

    # Phase 4C: Total alerts generated (tenant-filtered)
    total_alerts = get_tenant_filtered_query(Alert, db).count() or 0

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
    # Phase 4C: Tenant-filtered queries
    if metric == "alert_count":
        rules = get_tenant_filtered_query(MonitoringRule, db).order_by(
            MonitoringRule.alert_count.desc()
        ).limit(limit).all()
    else:
        rules = get_tenant_filtered_query(MonitoringRule, db).filter(
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
    # Phase 4C: Tenant-filtered query
    rules = get_tenant_filtered_query(MonitoringRule, db).filter(
        MonitoringRule.rule_id.in_(rule_ids)
    ).all()

    for rule in rules:
        rule.enabled = True
        rule.updated_at = utc_now()

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
    # Phase 4C: Tenant-filtered query
    rules = get_tenant_filtered_query(MonitoringRule, db).filter(
        MonitoringRule.rule_id.in_(rule_ids)
    ).all()

    for rule in rules:
        rule.enabled = False
        rule.updated_at = utc_now()

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

    # Phase 4C: Tenant-filtered query
    rules = get_tenant_filtered_query(MonitoringRule, db).filter(
        MonitoringRule.rule_id.in_(rule_ids)
    ).all()

    for rule in rules:
        rule.severity = new_severity
        rule.updated_at = utc_now()

    db.commit()

    return {
        "status": "success",
        "updated_count": len(rules),
        "new_severity": new_severity
    }
