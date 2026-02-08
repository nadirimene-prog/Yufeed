"""
Integration tests for compliance workflow.

Tests the complete lifecycle:
- Policy Upload
- Obligation Extraction (AI-powered)
- Obligation Review & Approval
- Internal Rule Creation from Obligations
- Rule Evaluation

Test Coverage:
- End-to-end compliance workflow
- Policy → Obligations → Rules chain
- Tenant isolation for compliance data
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


@pytest.mark.integration
class TestComplianceWorkflow:
    """Test complete compliance workflow from policy to rules."""

    def test_policy_to_obligation_to_rule_flow(
        self, client: TestClient, db_session: Session, auth_headers: dict
    ):
        """
        Test complete compliance workflow:
        Policy Upload → Obligation Extraction → Approval → Rule Creation
        """
        # Step 1: Upload policy document
        policy_response = client.post(
            "/api/compliance/policies",
            headers=auth_headers,
            json={
                "name": "BSA/AML Transaction Reporting Requirements",
                "category": "aml",
                "jurisdiction": "US",
                "content": """
                All transactions exceeding $10,000 must be reported to FinCEN within 15 days.
                Customer due diligence must be performed for all high-risk transactions.
                Suspicious activity reports must be filed within 30 days of detection.
                """,
                "effective_date": "2024-01-01",
                "source": "Bank Secrecy Act",
            },
        )

        assert policy_response.status_code == 201
        policy = policy_response.json()
        policy_id = policy["policy_id"]

        # Step 2: Extract obligations from policy (AI-powered)
        extract_response = client.post(
            f"/api/compliance/policies/{policy_id}/extract-obligations", headers=auth_headers
        )

        assert extract_response.status_code in [200, 201, 202]
        extraction_result = extract_response.json()

        # Wait for extraction to complete (if async)
        if "job_id" in extraction_result:
            # Poll for completion
            import time

            for _ in range(10):
                status_response = client.get(
                    f"/api/compliance/extraction-jobs/{extraction_result['job_id']}",
                    headers=auth_headers,
                )
                if status_response.json()["status"] == "completed":
                    break
                time.sleep(1)

        # Get extracted obligations
        obligations_response = client.get(
            f"/api/compliance/policies/{policy_id}/obligations", headers=auth_headers
        )

        assert obligations_response.status_code == 200
        obligations = obligations_response.json()

        # Should have extracted at least 2 obligations
        assert len(obligations) >= 2

        # Step 3: Review and approve first obligation
        obligation = obligations[0]
        obligation_id = obligation["obligation_id"]

        approve_response = client.post(
            f"/api/compliance/obligations/{obligation_id}/approve",
            headers=auth_headers,
            json={
                "reviewer_notes": "Approved for implementation",
                "implementation_priority": "high",
            },
        )

        assert approve_response.status_code == 200
        approved_obligation = approve_response.json()
        assert approved_obligation["status"] == "approved"

        # Step 4: Create internal monitoring rule from approved obligation
        rule_response = client.post(
            "/api/monitoring_rules",
            headers=auth_headers,
            json={
                "name": f"Rule: {obligation['obligation_text'][:50]}",
                "description": f"Automated rule created from obligation {obligation_id}",
                "obligation_id": obligation_id,
                "rule_type": "threshold",
                "conditions": [{"field": "amount", "operator": "greater_than", "value": 10000}],
                "actions": [
                    {
                        "action_type": "alert",
                        "severity": "high",
                        "notify": ["compliance@example.com"],
                    }
                ],
                "is_active": True,
            },
        )

        assert rule_response.status_code == 201
        rule = rule_response.json()
        assert rule["obligation_id"] == obligation_id
        assert rule["is_active"] is True

        # Step 5: Verify rule triggers on matching transaction
        test_txn_response = client.post(
            "/api/transactions",
            headers=auth_headers,
            json={
                "transaction_id": "txn_compliance_test_001",
                "user_id": "user_compliance_001",
                "amount": 15000.00,  # Exceeds $10,000 threshold
                "currency": "USD",
                "transaction_type": "deposit",
            },
        )

        assert test_txn_response.status_code == 201

        # Check if alert was created by rule
        alerts_response = client.get(
            "/api/alerts?user_id=user_compliance_001", headers=auth_headers
        )

        assert alerts_response.status_code == 200
        alerts = alerts_response.json()

        # Should have alert triggered by compliance rule
        compliance_alerts = [
            a
            for a in alerts
            if "compliance" in a.get("description", "").lower()
            or a.get("rule_id") == rule["rule_id"]
        ]
        assert len(compliance_alerts) >= 1


@pytest.mark.integration
class TestComplianceTenantIsolation:
    """Test tenant isolation for compliance data."""

    def test_policy_tenant_isolation(
        self, client: TestClient, db_session: Session, auth_headers: dict, tenant_factory
    ):
        """Test that policies are isolated by tenant."""
        from tests.factories import TenantFactory

        # Create two tenants
        tenant1 = TenantFactory(tenant_id="tenant_policy_1", sqlalchemy_session=db_session)
        tenant2 = TenantFactory(tenant_id="tenant_policy_2", sqlalchemy_session=db_session)
        db_session.commit()

        # Create policy for tenant1
        policy1_response = client.post(
            "/api/compliance/policies",
            headers={**auth_headers, "X-Tenant-ID": "tenant_policy_1"},
            json={
                "name": "Tenant 1 Policy",
                "category": "aml",
                "content": "Tenant 1 specific requirements",
                "jurisdiction": "US",
            },
        )
        assert policy1_response.status_code == 201
        policy1_id = policy1_response.json()["policy_id"]

        # Create policy for tenant2
        policy2_response = client.post(
            "/api/compliance/policies",
            headers={**auth_headers, "X-Tenant-ID": "tenant_policy_2"},
            json={
                "name": "Tenant 2 Policy",
                "category": "gdpr",
                "content": "Tenant 2 specific requirements",
                "jurisdiction": "EU",
            },
        )
        assert policy2_response.status_code == 201
        policy2_id = policy2_response.json()["policy_id"]

        # Tenant1 should only see their policy
        tenant1_policies = client.get(
            "/api/compliance/policies", headers={**auth_headers, "X-Tenant-ID": "tenant_policy_1"}
        )
        tenant1_policy_ids = [p["policy_id"] for p in tenant1_policies.json()]
        assert policy1_id in tenant1_policy_ids
        assert (
            policy2_id not in tenant1_policy_ids
        ), "Tenant 1 can see Tenant 2's policy - ISOLATION BREACH"

        # Tenant2 should only see their policy
        tenant2_policies = client.get(
            "/api/compliance/policies", headers={**auth_headers, "X-Tenant-ID": "tenant_policy_2"}
        )
        tenant2_policy_ids = [p["policy_id"] for p in tenant2_policies.json()]
        assert policy2_id in tenant2_policy_ids
        assert (
            policy1_id not in tenant2_policy_ids
        ), "Tenant 2 can see Tenant 1's policy - ISOLATION BREACH"
