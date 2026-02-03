import pytest
from datetime import datetime, timezone, timedelta

from src.models import models
from src.models.impact_assessment import ActionItem, ImpactAssessment


@pytest.mark.unit
class TestImpactAPI:
    def test_create_assessment_and_actions(self, client, db_session, monkeypatch, auth_headers):
        celex = "CELEX-IMPACT-1"
        doc = models.LegalDocument(
            celex=celex,
            title="Impact Regulation",
            publication_date=datetime(2024, 2, 1, tzinfo=timezone.utc),
            compliance_domain="aml",
            risk_level="high",
            implementation_deadline=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        db_session.add(doc)
        db_session.commit()

        analysis_payload = {
            "overall_impact_level": "high",
            "executive_summary": "summary",
            "affected_areas": ["onboarding"],
            "key_changes": ["change"],
            "action_items": [
                {
                    "title": "Update onboarding",
                    "description": "Do updates",
                    "business_area": "onboarding",
                    "priority": 1,
                    "estimated_hours": 12,
                    "complexity": "simple",
                }
            ],
            "gaps": [
                {
                    "category": "policy",
                    "current_state": "old",
                    "required_state": "new",
                    "gap_description": "gap",
                    "severity": "medium",
                    "business_area": "governance",
                    "remediation_approach": "update",
                    "estimated_cost": 1000,
                    "estimated_timeline_days": 30,
                }
            ],
            "resource_estimates": {
                "total_hours": 12,
                "total_cost_eur": 1000,
                "requires_system_changes": True,
                "requires_process_changes": False,
                "requires_policy_updates": True,
            },
        }

        from src.api import impact as impact_api

        def fake_analyze(self, doc_data):
            return analysis_payload

        monkeypatch.setattr(impact_api.ImpactAnalyzer, "analyze_impact", fake_analyze)

        resp = client.post(
            f"/api/impact/documents/{celex}/analyze",
            json={"force": False},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["overall_impact"] == "high"

        resp = client.get(
            f"/api/impact/documents/{celex}/assessment",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assessment = resp.json()
        assert assessment["overall_impact_level"] == "high"
        assert len(assessment["action_items"]) == 1

        resp = client.get(
            f"/api/impact/documents/{celex}/actions",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 1

        action = db_session.query(ActionItem).first()
        resp = client.put(
            f"/api/impact/actions/{action.id}",
            json={"status": "completed", "progress_percentage": 100, "notes": "done"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "completed"

        resp = client.get(
            "/api/impact/actions/all",
            params={"business_area": "onboarding"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

        resp = client.get("/api/impact/dashboard/stats", headers=auth_headers)
        assert resp.status_code == 200
        stats = resp.json()
        assert stats["total_assessments"] >= 1
        assert stats["total_action_items"] >= 1

    def test_get_impact_assessment_missing_document(self, client, auth_headers):
        resp = client.get(
            "/api/impact/documents/DOES-NOT-EXIST/assessment",
            headers=auth_headers,
        )
        assert resp.status_code == 404
