import pytest
from datetime import datetime, timezone, timedelta

from src.models import models
from src.models.impact_assessment import (
    ActionItem,
    ActionStatus,
    BusinessArea,
    ImpactAssessment,
    ImpactLevel,
)


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

    def test_get_all_action_items_pagination_compatibility(self, client, db_session, auth_headers):
        doc = models.LegalDocument(
            celex="CELEX-IMPACT-PAGE",
            title="Paged Impact Regulation",
            publication_date=datetime(2024, 2, 1, tzinfo=timezone.utc),
            compliance_domain="aml",
            risk_level="medium",
            implementation_deadline=datetime(2027, 1, 1, tzinfo=timezone.utc),
        )
        db_session.add(doc)
        db_session.commit()

        assessment = ImpactAssessment(
            doc_id=doc.id,
            overall_impact_level=ImpactLevel.HIGH,
            executive_summary="summary",
            affected_areas_json={"areas": ["onboarding"]},
            key_changes={"changes": ["change"]},
            estimated_effort_hours=24,
            estimated_cost=2000,
            requires_system_changes=True,
            requires_process_changes=False,
            requires_policy_updates=True,
            assessed_at=datetime.now(timezone.utc),
        )
        db_session.add(assessment)
        db_session.commit()

        actions = [
            ActionItem(
                assessment_id=assessment.id,
                title="Onboarding First",
                business_area=BusinessArea.ONBOARDING,
                priority=1,
                status=ActionStatus.NOT_STARTED,
                target_date=datetime.now(timezone.utc) + timedelta(days=1),
            ),
            ActionItem(
                assessment_id=assessment.id,
                title="Onboarding Second",
                business_area=BusinessArea.ONBOARDING,
                priority=2,
                status=ActionStatus.NOT_STARTED,
                target_date=datetime.now(timezone.utc) + timedelta(days=2),
            ),
            ActionItem(
                assessment_id=assessment.id,
                title="Governance Item",
                business_area=BusinessArea.GOVERNANCE,
                priority=3,
                status=ActionStatus.NOT_STARTED,
                target_date=datetime.now(timezone.utc) + timedelta(days=3),
            ),
        ]
        db_session.add_all(actions)
        db_session.commit()

        legacy_resp = client.get(
            "/api/impact/actions/all",
            params={"business_area": "onboarding"},
            headers=auth_headers,
        )
        assert legacy_resp.status_code == 200
        legacy_payload = legacy_resp.json()
        assert isinstance(legacy_payload, list)
        assert len(legacy_payload) == 2

        paged_resp = client.get(
            "/api/impact/actions/all",
            params={"business_area": "onboarding", "skip": 1, "limit": 1},
            headers=auth_headers,
        )
        assert paged_resp.status_code == 200
        paged_payload = paged_resp.json()
        assert paged_payload["total"] == 2
        assert paged_payload["skip"] == 1
        assert paged_payload["limit"] == 1
        assert len(paged_payload["items"]) == 1
        assert paged_payload["items"][0]["title"] == "Onboarding Second"
