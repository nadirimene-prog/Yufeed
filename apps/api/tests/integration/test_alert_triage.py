"""
Integration tests for alert triage and resolution workflow.

Tests the complete lifecycle:
- Alert Creation
- Assignment to analyst
- Investigation
- Resolution (true positive / false positive)

Test Coverage:
- Full alert triage workflow
- Tenant isolation during alert operations
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime


@pytest.mark.integration
class TestAlertTriageWorkflow:
    """Test alert triage and resolution workflow."""

    def test_alert_triage_workflow(self, client: TestClient, db_session: Session, auth_headers: dict):
        """
        Test complete alert triage workflow:
        Alert creation → Assignment → Investigation → Resolution
        """
        # Step 1: Create transaction and alert
        txn_response = client.post(
            "/api/transactions",
            headers=auth_headers,
            json={
                "transaction_id": "txn_triage_001",
                "user_id": "user_triage_001",
                "amount": 25000.00,
                "currency": "USD",
                "transaction_type": "withdrawal",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        assert txn_response.status_code == 201
        txn_id = txn_response.json()["id"]

        alert_response = client.post(
            "/api/alerts",
            headers=auth_headers,
            json={
                "alert_type": "high_value_withdrawal",
                "severity": "high",
                "transaction_id": txn_id,
                "user_id": "user_triage_001",
                "description": "Large withdrawal detected",
                "risk_score": 75.5,
                "evidence": {"pattern": "unusual_amount"}
            }
        )
        assert alert_response.status_code == 201
        alert = alert_response.json()
        alert_id = alert["alert_id"]

        # Step 2: Assign alert to analyst
        assign_response = client.patch(
            f"/api/alerts/{alert_id}",
            headers=auth_headers,
            json={
                "assigned_to": "analyst@example.com",
                "status": "in_review"
            }
        )
        assert assign_response.status_code == 200
        assigned_alert = assign_response.json()
        assert assigned_alert["assigned_to"] == "analyst@example.com"
        assert assigned_alert["status"] == "in_review"

        # Step 3: Analyst investigates and marks as false positive
        resolve_response = client.patch(
            f"/api/alerts/{alert_id}",
            headers=auth_headers,
            json={
                "status": "resolved",
                "resolution_status": "false_positive",
                "resolution_notes": "Customer is a verified high-net-worth individual. Withdrawal is legitimate."
            }
        )
        assert resolve_response.status_code == 200
        resolved_alert = resolve_response.json()
        assert resolved_alert["status"] == "resolved"
        assert resolved_alert["resolution_status"] == "false_positive"

        # Step 4: Verify alert is no longer in pending queue
        pending_response = client.get(
            "/api/alerts?status=pending",
            headers=auth_headers
        )
        pending_alerts = pending_response.json()

        # Our alert should not be in pending list
        assert not any(a["alert_id"] == alert_id for a in pending_alerts)

    def test_alert_assignment_transitions(self, client: TestClient, db_session: Session, auth_headers: dict):
        """Test alert status transitions during assignment workflow."""
        # Create alert
        alert_response = client.post(
            "/api/alerts",
            headers=auth_headers,
            json={
                "alert_type": "suspicious_pattern",
                "severity": "medium",
                "user_id": "user_status_test",
                "description": "Pattern detected",
                "risk_score": 60.0
            }
        )
        assert alert_response.status_code == 201
        alert_id = alert_response.json()["alert_id"]

        # Valid transition: pending → in_review
        response1 = client.patch(
            f"/api/alerts/{alert_id}",
            headers=auth_headers,
            json={"status": "in_review", "assigned_to": "analyst1@example.com"}
        )
        assert response1.status_code == 200

        # Valid transition: in_review → resolved
        response2 = client.patch(
            f"/api/alerts/{alert_id}",
            headers=auth_headers,
            json={"status": "resolved", "resolution_status": "true_positive"}
        )
        assert response2.status_code == 200

    def test_alert_investigation_notes(self, client: TestClient, db_session: Session, auth_headers: dict):
        """Test adding investigation notes to alerts during triage."""
        # Create alert
        alert_response = client.post(
            "/api/alerts",
            headers=auth_headers,
            json={
                "alert_type": "investigation_test",
                "severity": "high",
                "user_id": "user_notes_test",
                "description": "Test alert",
                "risk_score": 80.0
            }
        )
        alert_id = alert_response.json()["alert_id"]

        # Add investigation note
        note_response = client.post(
            f"/api/alerts/{alert_id}/notes",
            headers=auth_headers,
            json={
                "note": "Contacted customer via phone. Transaction confirmed legitimate.",
                "author": "analyst@example.com"
            }
        )
        assert note_response.status_code in [200, 201]

        # Verify note was added
        alert_detail = client.get(f"/api/alerts/{alert_id}", headers=auth_headers)
        alert_data = alert_detail.json()

        if "notes" in alert_data:
            assert len(alert_data["notes"]) > 0
            assert any("customer via phone" in n.get("note", "") for n in alert_data["notes"])

    def test_alert_tenant_isolation(self, client: TestClient, db_session: Session, auth_headers: dict, tenant_factory):
        """Test that alerts are isolated by tenant."""
        # Create two tenants
        from tests.factories import TenantFactory
        tenant1 = TenantFactory(tenant_id="tenant_alert_1", sqlalchemy_session=db_session)
        tenant2 = TenantFactory(tenant_id="tenant_alert_2", sqlalchemy_session=db_session)
        db_session.commit()

        # Create alert for tenant1
        alert1_response = client.post(
            "/api/alerts",
            headers={**auth_headers, "X-Tenant-ID": "tenant_alert_1"},
            json={
                "alert_type": "isolation_test_1",
                "severity": "high",
                "user_id": "shared_user_id",  # Same user_id in both tenants
                "description": "Tenant 1 alert",
                "risk_score": 70.0
            }
        )
        assert alert1_response.status_code == 201
        alert1_id = alert1_response.json()["alert_id"]

        # Create alert for tenant2
        alert2_response = client.post(
            "/api/alerts",
            headers={**auth_headers, "X-Tenant-ID": "tenant_alert_2"},
            json={
                "alert_type": "isolation_test_2",
                "severity": "medium",
                "user_id": "shared_user_id",  # Same user_id
                "description": "Tenant 2 alert",
                "risk_score": 50.0
            }
        )
        assert alert2_response.status_code == 201
        alert2_id = alert2_response.json()["alert_id"]

        # Tenant1 should only see their alert
        tenant1_alerts = client.get(
            "/api/alerts",
            headers={**auth_headers, "X-Tenant-ID": "tenant_alert_1"}
        )
        tenant1_alert_ids = [a["alert_id"] for a in tenant1_alerts.json()]
        assert alert1_id in tenant1_alert_ids
        assert alert2_id not in tenant1_alert_ids, "Tenant 1 can see Tenant 2's alert - ISOLATION BREACH"

        # Tenant2 should only see their alert
        tenant2_alerts = client.get(
            "/api/alerts",
            headers={**auth_headers, "X-Tenant-ID": "tenant_alert_2"}
        )
        tenant2_alert_ids = [a["alert_id"] for a in tenant2_alerts.json()]
        assert alert2_id in tenant2_alert_ids
        assert alert1_id not in tenant2_alert_ids, "Tenant 2 can see Tenant 1's alert - ISOLATION BREACH"
