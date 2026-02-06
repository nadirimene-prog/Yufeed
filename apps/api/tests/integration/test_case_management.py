"""
Integration tests for case management workflow.

Tests the complete lifecycle:
- Multiple Alerts → Case Creation
- Case Assignment & Investigation
- Case Resolution (outcomes)
- Audit Trail

Test Coverage:
- End-to-end case workflow
- Multiple alerts linked to single case
- Case status transitions
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime


@pytest.mark.integration
class TestCaseCreationFlow:
    """Test case creation from alerts."""

    def test_create_case_from_alerts(self, client: TestClient, db_session: Session, auth_headers: dict):
        """
        Test creating investigation case from multiple alerts.
        """
        user_id = "user_case_001"

        # Step 1: Create multiple alerts for same user
        alert_ids = []

        for i in range(3):
            txn_response = client.post(
                "/api/transactions",
                headers=auth_headers,
                json={
                    "transaction_id": f"txn_case_{i}",
                    "user_id": user_id,
                    "amount": 15000.00 + (i * 1000),
                    "currency": "USD",
                    "transaction_type": "deposit",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            txn_id = txn_response.json()["id"]

            alert_response = client.post(
                "/api/alerts",
                headers=auth_headers,
                json={
                    "alert_type": "suspicious_activity",
                    "severity": "high",
                    "transaction_id": txn_id,
                    "user_id": user_id,
                    "description": f"Suspicious transaction {i}",
                    "risk_score": 80.0 + i
                }
            )
            alert_ids.append(alert_response.json()["id"])

        # Step 2: Create case from alerts
        case_response = client.post(
            "/api/cases",
            headers=auth_headers,
            json={
                "title": f"Investigation: Suspicious Activity - {user_id}",
                "description": "Multiple high-value deposits in short timeframe",
                "case_type": "investigation",
                "subject_type": "user",
                "subject_id": user_id,
                "priority": "high",
                "status": "open",
                "assigned_to": "investigator@example.com",
                "related_alert_ids": alert_ids
            }
        )

        assert case_response.status_code == 201
        case = case_response.json()

        assert case["subject_id"] == user_id
        assert case["priority"] == "high"
        assert case["status"] == "open"
        assert len(case["related_alert_ids"]) == 3

        # Step 3: Update case with findings
        case_id = case["case_id"]

        update_response = client.patch(
            f"/api/cases/{case_id}",
            headers=auth_headers,
            json={
                "status": "closed",
                "outcome": "sar_filed",
                "outcome_notes": "SAR filed with FinCEN. Case #12345"
            }
        )

        assert update_response.status_code == 200
        updated_case = update_response.json()
        assert updated_case["status"] == "closed"
        assert updated_case["outcome"] == "sar_filed"
