"""
Seed a minimal, UI-focused dataset for local UX/UI audits.

Creates:
- One tenant (`yufeed_dev`)
- Two users (admin + analyst) with tenant membership
- Minimal representative data: legal docs, monitoring rules, transactions, alerts, cases

Designed to be idempotent and safe to run multiple times.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import os
import random

from src.auth.jwt_handler import PasswordHandler
from src.database import SessionLocal
from src.models.models import LegalDocument
from src.models.tenant_models import Tenant, TenantUser
from src.models.transaction_models import Alert, Case, MonitoringRule, Transaction
from src.models.user import User


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class SeedConfig:
    tenant_id: str
    admin_email: str
    analyst_email: str
    password: str


def _get_config() -> SeedConfig:
    return SeedConfig(
        tenant_id=os.getenv("YUFEED_SEED_TENANT_ID", "yufeed_dev"),
        # NOTE: EmailStr validation rejects special-use TLDs like `.local`.
        # Use a real domain by default so /api/auth/login accepts the payload.
        admin_email=os.getenv("YUFEED_SEED_ADMIN_EMAIL", "admin@yufeed.eu").lower(),
        analyst_email=os.getenv("YUFEED_SEED_ANALYST_EMAIL", "analyst@yufeed.eu").lower(),
        password=os.getenv("YUFEED_SEED_PASSWORD", "YufeedDev123"),
    )


def ensure_tenant(db, tenant_id: str) -> Tenant:
    tenant = db.query(Tenant).filter(Tenant.tenant_id == tenant_id).first()
    if tenant:
        return tenant

    tenant = Tenant(
        tenant_id=tenant_id,
        name="Yufeed Dev Workspace",
        display_name="Yufeed Dev",
        tier="standard",
        is_active=True,
    )
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant


def ensure_user(db, *, email: str, full_name: str, password: str) -> User:
    user = db.query(User).filter(User.email == email).first()
    if user:
        return user

    user = User(
        email=email,
        hashed_password=PasswordHandler.hash_password(password),
        full_name=full_name,
        default_role="user",
        is_active=True,
        is_verified=True,
        is_superuser=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def ensure_membership(db, *, tenant: Tenant, user: User, role: str) -> None:
    # Tenant membership lookup during login supports both user.id and email.
    identifiers = {str(user.id), (user.email or "").lower()}
    for identifier in identifiers:
        if not identifier:
            continue
        existing = (
            db.query(TenantUser)
            .filter(
                TenantUser.tenant_id == tenant.id,
                TenantUser.user_id == identifier,
            )
            .first()
        )
        if existing:
            if existing.role != role or not existing.is_active:
                existing.role = role
                existing.is_active = True
                db.commit()
            continue

        db.add(TenantUser(tenant_id=tenant.id, user_id=identifier, role=role, is_active=True))
        db.commit()


def ensure_legal_docs(db) -> None:
    docs = [
        ("32024R1624", "Regulation (EU) 2024/1624 (AML Regulation)"),
        ("32023R1114", "Regulation (EU) 2023/1114 (MiCA)"),
        ("32015D2366", "Directive (EU) 2015/2366 (PSD2)"),
    ]
    now = utc_now()
    for celex, title in docs:
        exists = db.query(LegalDocument).filter(LegalDocument.celex == celex).first()
        if exists:
            continue
        db.add(
            LegalDocument(
                celex=celex,
                title=title,
                type="regulation",
                status="active",
                last_modified=now,
            )
        )
    db.commit()


def ensure_monitoring_rules(db, tenant_id: str) -> None:
    def ensure_rule(rule_id, name, category, severity, conditions, thresholds=None):
        existing = db.query(MonitoringRule).filter(MonitoringRule.rule_id == rule_id).first()
        if existing:
            return
        db.add(
            MonitoringRule(
                tenant_id=tenant_id,
                rule_id=rule_id,
                name=name,
                category=category,
                severity=severity,
                conditions=conditions,
                thresholds=thresholds,
                enabled=True,
                created_by="seed",
            )
        )
        db.commit()

    ensure_rule(
        "RULE-DEV-AMOUNT-10K",
        "Large Transaction > €10k",
        "amount_threshold",
        "medium",
        {
            "logic": "AND",
            "conditions": [
                {"field": "amount", "operator": "greater_than", "value": 10000},
                {"field": "currency", "operator": "equals", "value": "EUR"},
            ],
        },
    )
    ensure_rule(
        "RULE-DEV-SANC",
        "Sanctioned Jurisdiction",
        "sanctions",
        "critical",
        {
            "logic": "AND",
            "conditions": [
                {"field": "country_code", "operator": "in", "value": ["IR", "KP", "SY"]}
            ],
        },
    )
    ensure_rule(
        "RULE-DEV-VEL-10-24H",
        "High Frequency (10/24h)",
        "velocity",
        "high",
        {"logic": "AND", "conditions": []},
        {"transaction_count": 10, "time_window_hours": 24},
    )


def ensure_transactions(db, tenant_id: str, *, target_count: int = 20) -> list[Transaction]:
    countries = ["FR", "DE", "ES", "IT", "NL", "BE", "CH", "AT", "PL", "SE"]
    tx_types = ["deposit", "withdrawal", "transfer", "wire_transfer", "payment"]
    statuses = ["completed", "pending", "flagged", "blocked"]

    existing_count = (
        db.query(Transaction).filter(Transaction.transaction_id.like("TX-DEV-%")).count()
    )
    if existing_count < target_count:
        base = utc_now()
        for i in range(1, target_count + 1):
            tx_id = f"TX-DEV-{i:04d}"
            if db.query(Transaction).filter(Transaction.transaction_id == tx_id).first():
                continue

            amount = Decimal(str(random.choice([125, 980, 5100, 9800, 15250, 62000, 125000])))
            risk_score = Decimal(str(random.choice([12.5, 34.2, 58.7, 81.3, 92.6])))
            score_f = float(risk_score)
            risk_level = (
                "low"
                if score_f < 25
                else "medium" if score_f < 60 else "high" if score_f < 90 else "critical"
            )

            db.add(
                Transaction(
                    tenant_id=tenant_id,
                    transaction_id=tx_id,
                    user_id=f"USER{random.randint(1, 20):04d}",
                    amount=amount,
                    currency=random.choice(["EUR", "USD", "GBP"]),
                    transaction_type=random.choice(tx_types),
                    timestamp=base - timedelta(hours=random.randint(1, 96)),
                    status=random.choice(statuses),
                    country_code=random.choice(countries),
                    risk_score=risk_score,
                    risk_level=risk_level,
                )
            )
        db.commit()

    return (
        db.query(Transaction)
        .filter(Transaction.transaction_id.like("TX-DEV-%"))
        .order_by(Transaction.id.asc())
        .all()
    )


def ensure_alerts(db, tenant_id: str, txs: list[Transaction], *, target_count: int = 8) -> None:
    def ensure_alert(alert_id: str, **kwargs):
        existing = db.query(Alert).filter(Alert.alert_id == alert_id).first()
        if existing:
            return
        db.add(Alert(tenant_id=tenant_id, alert_id=alert_id, **kwargs))
        db.commit()

    existing_count = db.query(Alert).filter(Alert.alert_id.like("ALT-DEV-%")).count()
    if existing_count >= target_count or not txs:
        return

    # Include both 'under_review' and 'in_review' to surface any UI/status mapping issues during audits.
    statuses = [
        "pending",
        "under_review",
        "in_review",
        "escalated",
        "resolved",
        "false_positive",
        "auto_closed",
    ]
    severities = ["low", "medium", "high", "critical"]
    for i in range(1, target_count + 1):
        alert_id = f"ALT-DEV-{i:04d}"
        tx = txs[(i - 1) % len(txs)]
        ensure_alert(
            alert_id,
            alert_type=random.choice(["velocity", "structuring", "sanctions", "unusual_pattern"]),
            severity=random.choice(severities),
            user_id=tx.user_id,
            status=random.choice(statuses),
            priority=random.choice([1, 2, 3, 4, 5]),
            description="Seeded alert for UI review",
            transaction_id=tx.id if i % 2 == 0 else None,
            risk_score=tx.risk_score,
        )


def ensure_cases(db, tenant_id: str) -> None:
    existing_count = db.query(Case).filter(Case.case_id.like("CASE-DEV-%")).count()
    if existing_count >= 2:
        return

    def ensure_case(case_id: str, **kwargs):
        existing = db.query(Case).filter(Case.case_id == case_id).first()
        if existing:
            return
        db.add(Case(tenant_id=tenant_id, case_id=case_id, **kwargs))
        db.commit()

    ensure_case(
        "CASE-DEV-0001",
        case_type="investigation",
        subject_type="user",
        subject_id="USER0001",
        status="open",
        priority="high",
        title="Seeded investigation case",
        description="Seeded case for UI review",
        opened_at=utc_now(),
    )
    ensure_case(
        "CASE-DEV-0002",
        case_type="sar_preparation",
        subject_type="transaction",
        subject_id="TX-DEV-0002",
        status="in_progress",
        priority="medium",
        title="Seeded SAR prep case",
        description="Seeded case for UI review",
        opened_at=utc_now(),
    )


def main() -> int:
    cfg = _get_config()

    db = SessionLocal()
    try:
        tenant = ensure_tenant(db, cfg.tenant_id)

        admin = ensure_user(
            db, email=cfg.admin_email, full_name="Admin User", password=cfg.password
        )
        analyst = ensure_user(
            db, email=cfg.analyst_email, full_name="Analyst User", password=cfg.password
        )

        ensure_membership(db, tenant=tenant, user=admin, role="admin")
        ensure_membership(db, tenant=tenant, user=analyst, role="analyst")

        ensure_legal_docs(db)
        ensure_monitoring_rules(db, cfg.tenant_id)
        txs = ensure_transactions(db, cfg.tenant_id)
        ensure_alerts(db, cfg.tenant_id, txs)
        ensure_cases(db, cfg.tenant_id)

        print("✅ UI audit seed complete")
        print(f"Tenant:  {cfg.tenant_id}")
        print(f"Admin:   {cfg.admin_email} / {cfg.password}")
        print(f"Analyst: {cfg.analyst_email} / {cfg.password}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
