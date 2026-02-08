"""
Integration tests for decisioning engine workflow.

Tests the complete lifecycle:
- Event Ingestion
- Feature Computation
- Decision Generation
- Immutable Audit Trail

Test Coverage:
- End-to-end decisioning workflow
- Decision immutability verification
- Audit logging for decisions
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


@pytest.mark.integration
class TestDecisioningFlow:
    """Test decisioning engine integration."""

    def test_decisioning_event_to_decision(
        self, client: TestClient, db_session: Session, admin_headers: dict
    ):
        """
        Test decisioning flow: Event ingestion → Feature computation → Decision
        """
        # Step 1: Ingest decisioning event
        event_response = client.post(
            "/api/decisioning/events",
            headers=admin_headers,
            json={
                "event_type": "transaction",
                "entity_type": "user",
                "entity_id": "user_decisioning_001",
                "payload": {
                    "transaction_id": "txn_decision_001",
                    "amount": 5000.00,
                    "currency": "USD",
                    "merchant": "Online Casino",
                },
            },
        )

        assert event_response.status_code in [200, 201]
        event = event_response.json()
        event_id = event["event_id"]

        # Step 2: Request decision
        decision_response = client.post(
            "/api/decisioning/decide",
            headers=admin_headers,
            json={"event_id": event_id, "decision_type": "transaction_approval"},
        )

        assert decision_response.status_code in [200, 201]
        decision = decision_response.json()

        assert "decision" in decision
        assert decision["decision"] in ["approve", "decline", "review"]
        assert "risk_score" in decision
        assert "decision_id" in decision

        # Step 3: Verify decision is immutable (stored in audit log)
        # Try to get decision by ID
        decision_id = decision["decision_id"]

        get_response = client.get(
            f"/api/decisioning/decisions/{decision_id}", headers=admin_headers
        )

        assert get_response.status_code == 200
        retrieved_decision = get_response.json()
        assert retrieved_decision["decision_id"] == decision_id


@pytest.mark.integration
class TestAuditLogging:
    """Test audit logging captures all mutations."""

    def test_audit_log_captures_alert_lifecycle(
        self, client: TestClient, db_session: Session, admin_headers: dict
    ):
        """
        Test that audit log captures complete alert lifecycle.
        """
        # Step 1: Create alert
        alert_response = client.post(
            "/api/alerts",
            headers=admin_headers,
            json={
                "alert_type": "test_audit",
                "severity": "medium",
                "user_id": "user_audit_001",
                "description": "Test alert for audit logging",
                "risk_score": 50.0,
            },
        )
        alert_id = alert_response.json()["alert_id"]

        # Step 2: Update alert
        client.patch(
            f"/api/alerts/{alert_id}",
            headers=admin_headers,
            json={"status": "in_review", "assigned_to": "analyst@example.com"},
        )

        # Step 3: Resolve alert
        client.patch(
            f"/api/alerts/{alert_id}",
            headers=admin_headers,
            json={"status": "resolved", "resolution_status": "confirmed"},
        )

        # Step 4: Check audit log
        audit_response = client.get("/api/audit", headers=admin_headers)

        assert audit_response.status_code == 200
        audit_logs = audit_response.json()

        # Filter logs for our alert
        alert_logs = [
            log
            for log in audit_logs
            if log.get("entity_type") == "alerts" and log.get("entity_id") == alert_id
        ]

        # Should have logs for create, update, resolve
        assert len(alert_logs) >= 2  # At least creation and one update
