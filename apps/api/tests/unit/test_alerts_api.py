"""
Unit tests for alerts API endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime

from tests.factories import TransactionFactory, AlertFactory


@pytest.mark.unit
class TestAlertCreation:
    """Test alert creation endpoint."""

    def test_create_alert_success(
        self, client: TestClient, db_session: Session, auth_headers: dict
    ):
        """Test successful alert creation."""
        # Create a transaction first
        transaction = TransactionFactory(sqlalchemy_session=db_session)
        db_session.commit()

        response = client.post(
            "/api/alerts",
            headers=auth_headers,
            json={
                "alert_type": "high_value_transaction",
                "severity": "high",
                "transaction_id": transaction.id,
                "user_id": transaction.user_id,
                "description": "Transaction exceeds threshold",
                "risk_score": 85.5,
                "matched_rules_data": [{"rule_id": "rule_001", "matched": True}],
                "evidence": {"pattern": "unusual_velocity"},
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["alert_type"] == "high_value_transaction"
        assert data["severity"] == "high"
        assert data["status"] == "pending"
        assert "alert_id" in data
        assert data["alert_id"].startswith("ALT-")

    def test_create_alert_without_transaction(self, client: TestClient, auth_headers: dict):
        """Test creating alert without associated transaction."""
        response = client.post(
            "/api/alerts",
            headers=auth_headers,
            json={
                "alert_type": "sanctions_match",
                "severity": "critical",
                "user_id": "user_123",
                "description": "User matched sanctions list",
                "risk_score": 95.0,
                "evidence": {"list": "OFAC"},
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["transaction_id"] is None

    def test_create_alert_invalid_transaction(self, client: TestClient, auth_headers: dict):
        """Test creating alert with invalid transaction ID fails."""
        response = client.post(
            "/api/alerts",
            headers=auth_headers,
            json={
                "alert_type": "high_value_transaction",
                "severity": "high",
                "transaction_id": 999999,  # Non-existent
                "user_id": "user_123",
                "description": "Test alert",
                "risk_score": 50.0,
            },
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_create_alert_missing_required_fields(self, client: TestClient, auth_headers: dict):
        """Test creating alert with missing required fields fails."""
        response = client.post(
            "/api/alerts",
            headers=auth_headers,
            json={
                "alert_type": "high_value_transaction"
                # Missing severity, user_id, etc.
            },
        )

        assert response.status_code == 422


@pytest.mark.unit
class TestAlertListing:
    """Test alert listing endpoint."""

    def test_list_alerts_empty(self, client: TestClient, auth_headers: dict):
        """Test listing alerts when none exist."""
        response = client.get("/api/alerts", headers=auth_headers)

        assert response.status_code == 200
        assert response.json() == []

    def test_list_alerts_with_data(
        self, client: TestClient, db_session: Session, auth_headers: dict
    ):
        """Test listing alerts with data."""
        # Create test alerts
        alerts = AlertFactory.create_batch(5, sqlalchemy_session=db_session)
        db_session.commit()

        response = client.get("/api/alerts", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5

    def test_list_alerts_pagination(
        self, client: TestClient, db_session: Session, auth_headers: dict
    ):
        """Test alert listing pagination."""
        # Create 25 test alerts
        AlertFactory.create_batch(25, sqlalchemy_session=db_session)
        db_session.commit()

        # Get first page
        response = client.get("/api/alerts?skip=0&limit=10", headers=auth_headers)
        assert response.status_code == 200
        assert len(response.json()) == 10

        # Get second page
        response = client.get("/api/alerts?skip=10&limit=10", headers=auth_headers)
        assert response.status_code == 200
        assert len(response.json()) == 10

        # Get third page
        response = client.get("/api/alerts?skip=20&limit=10", headers=auth_headers)
        assert response.status_code == 200
        assert len(response.json()) == 5

    def test_list_alerts_filter_by_status(
        self, client: TestClient, db_session: Session, auth_headers: dict
    ):
        """Test filtering alerts by status."""
        # Create alerts with different statuses
        AlertFactory(status="pending", sqlalchemy_session=db_session)
        AlertFactory(status="pending", sqlalchemy_session=db_session)
        AlertFactory(status="resolved", sqlalchemy_session=db_session)
        db_session.commit()

        response = client.get("/api/alerts?status=pending", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert all(alert["status"] == "pending" for alert in data)

    def test_list_alerts_filter_by_severity(
        self, client: TestClient, db_session: Session, auth_headers: dict
    ):
        """Test filtering alerts by severity."""
        # Create alerts with different severities
        AlertFactory(severity="high", sqlalchemy_session=db_session)
        AlertFactory(severity="high", sqlalchemy_session=db_session)
        AlertFactory(severity="low", sqlalchemy_session=db_session)
        db_session.commit()

        response = client.get("/api/alerts?severity=high", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert all(alert["severity"] == "high" for alert in data)

    def test_list_alerts_filter_by_user(
        self, client: TestClient, db_session: Session, auth_headers: dict
    ):
        """Test filtering alerts by user_id."""
        # Create alerts for different users
        AlertFactory(user_id="user_001", sqlalchemy_session=db_session)
        AlertFactory(user_id="user_001", sqlalchemy_session=db_session)
        AlertFactory(user_id="user_002", sqlalchemy_session=db_session)
        db_session.commit()

        response = client.get("/api/alerts?user_id=user_001", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert all(alert["user_id"] == "user_001" for alert in data)

    def test_list_alerts_multiple_filters(
        self, client: TestClient, db_session: Session, auth_headers: dict
    ):
        """Test filtering alerts with multiple criteria."""
        # Create test data
        AlertFactory(
            status="pending", severity="high", user_id="user_001", sqlalchemy_session=db_session
        )
        AlertFactory(
            status="pending", severity="low", user_id="user_001", sqlalchemy_session=db_session
        )
        AlertFactory(
            status="resolved", severity="high", user_id="user_001", sqlalchemy_session=db_session
        )
        db_session.commit()

        response = client.get(
            "/api/alerts?status=pending&severity=high&user_id=user_001", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1


@pytest.mark.unit
class TestAlertRetrieval:
    """Test single alert retrieval endpoint."""

    def test_get_alert_by_id(self, client: TestClient, db_session: Session, auth_headers: dict):
        """Test retrieving alert by ID."""
        alert = AlertFactory(sqlalchemy_session=db_session)
        db_session.commit()

        response = client.get(f"/api/alerts/{alert.alert_id}", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["alert_id"] == alert.alert_id
        assert data["alert_type"] == alert.alert_type

    def test_get_nonexistent_alert(self, client: TestClient, auth_headers: dict):
        """Test retrieving non-existent alert."""
        response = client.get("/api/alerts/ALT-NONEXISTENT", headers=auth_headers)

        assert response.status_code == 404


@pytest.mark.unit
class TestAlertUpdate:
    """Test alert update endpoints."""

    def test_assign_alert(self, client: TestClient, db_session: Session, auth_headers: dict):
        """Test assigning alert to analyst."""
        alert = AlertFactory(status="pending", assigned_to=None, sqlalchemy_session=db_session)
        db_session.commit()

        response = client.patch(
            f"/api/alerts/{alert.alert_id}",
            headers=auth_headers,
            json={"assigned_to": "analyst@example.com", "status": "in_review"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["assigned_to"] == "analyst@example.com"
        assert data["status"] == "in_review"

    def test_resolve_alert(self, client: TestClient, db_session: Session, auth_headers: dict):
        """Test resolving alert."""
        alert = AlertFactory(status="in_review", sqlalchemy_session=db_session)
        db_session.commit()

        response = client.patch(
            f"/api/alerts/{alert.alert_id}",
            headers=auth_headers,
            json={
                "status": "resolved",
                "resolution_status": "false_positive",
                "resolution_notes": "Legitimate transaction verified",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "resolved"
        assert data["resolution_status"] == "false_positive"

    def test_escalate_alert(self, client: TestClient, db_session: Session, auth_headers: dict):
        """Test escalating alert."""
        alert = AlertFactory(status="in_review", priority=3, sqlalchemy_session=db_session)
        db_session.commit()

        response = client.patch(
            f"/api/alerts/{alert.alert_id}",
            headers=auth_headers,
            json={"status": "escalated", "priority": 1},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "escalated"
        assert data["priority"] == 1


@pytest.mark.unit
class TestAlertStatistics:
    """Test alert statistics endpoint."""

    def test_get_alert_statistics(
        self, client: TestClient, db_session: Session, auth_headers: dict
    ):
        """Test retrieving alert statistics."""
        # Create alerts with various statuses
        AlertFactory(status="pending", severity="high", sqlalchemy_session=db_session)
        AlertFactory(status="pending", severity="medium", sqlalchemy_session=db_session)
        AlertFactory(status="resolved", severity="high", sqlalchemy_session=db_session)
        AlertFactory(status="escalated", severity="critical", sqlalchemy_session=db_session)
        db_session.commit()

        response = client.get("/api/alerts/statistics", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "total_alerts" in data
        assert "by_status" in data
        assert "by_severity" in data
        assert data["total_alerts"] == 4
