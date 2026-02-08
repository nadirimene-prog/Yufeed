"""
Seed a minimal audit/event/decision trail for local verification.
"""

from datetime import datetime
import uuid

from src.database import SessionLocal
from src.audit.recorders import record_event, record_decision
from src.audit.models import AuditLog


def main() -> None:
    db = SessionLocal()
    try:
        event = record_event(
            db,
            event_type="txn_fiat",
            entity_type="transaction",
            entity_id=f"TX-{uuid.uuid4().hex[:8].upper()}",
            payload={
                "user_id": "user_demo",
                "amount": 2500.0,
                "currency": "EUR",
                "transaction_type": "sepa_transfer",
            },
            source="seed",
        )
        db.flush()
        decision = record_decision(
            db,
            decision="alert",
            event_id=event.event_id,
            reason_codes=["RULE-001"],
            rule_version="1",
            model_version="baseline",
            evidence={"note": "Seeded decision for smoke test"},
            metadata={"seeded_at": datetime.utcnow().isoformat()},
        )

        audit_log = AuditLog(
            audit_id=uuid.uuid4().hex,
            actor_id="system",
            actor_email=None,
            actor_role="system",
            actor_type="system",
            action="seed",
            method="script",
            path="scripts/seed_audit_demo.py",
            entity_type="decision",
            entity_id=decision.decision_id,
            status_code=200,
            changes={"event_id": event.event_id},
            metadata_json={"purpose": "local verification"},
        )
        db.add(audit_log)
        db.commit()

        print("Seeded event:", event.event_id)
        print("Seeded decision:", decision.decision_id)
        print("Seeded audit log:", audit_log.audit_id)
    finally:
        db.close()


if __name__ == "__main__":
    main()
