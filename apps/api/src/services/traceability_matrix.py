"""Regulatory traceability matrix service.

Builds and reports the full chain:
Regulation -> Obligation -> Policy -> InternalRule -> MonitoringRule
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from src.models.compliance_workflow import (
    InternalRule,
    InternalRuleMapping,
    ObligationPolicyMapping,
    PolicyDocument,
    RegulatoryObligation,
    TenantObligationApplicability,
)
from src.models.models import LegalDocument
from src.models.transaction_models import MonitoringRule
from src.utils.time import utc_now

APPLICABLE_STATUSES = {"applicable", "partially_applicable"}


class TraceabilityMatrixService:
    """Build traceability chains and coverage snapshots for one tenant."""

    def __init__(self, db: Session):
        self.db = db

    def get_full_chain(
        self,
        tenant_id: str,
        obligation_id: Optional[str] = None,
        regulation_doc_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        obligations = self._fetch_applicable_obligations(
            tenant_id=tenant_id,
            obligation_id=obligation_id,
            regulation_doc_id=regulation_doc_id,
        )

        items: List[Dict[str, Any]] = []
        for obligation in obligations:
            regulation = (
                self.db.query(LegalDocument).filter(LegalDocument.id == obligation.doc_id).first()
            )

            policies = self._policies_for_obligation(obligation=obligation, tenant_id=tenant_id)
            internal_rules = self._internal_rules_for_obligation(
                obligation_id=obligation.id, tenant_id=tenant_id
            )
            mappings, monitoring_rules = self._monitoring_for_internal_rules(
                internal_rules=internal_rules,
                tenant_id=tenant_id,
            )

            items.append(
                {
                    "regulation": (
                        {
                            "id": regulation.id,
                            "celex": regulation.celex,
                            "title": regulation.title,
                        }
                        if regulation
                        else None
                    ),
                    "obligation": {
                        "id": obligation.id,
                        "obligation_id": obligation.obligation_id,
                        "article_ref": obligation.article_ref,
                        "status": obligation.status,
                    },
                    "policies": [
                        {
                            "id": policy.id,
                            "policy_id": policy.policy_id,
                            "name": policy.name,
                            "tenant_id": policy.tenant_id,
                            "is_master": bool(policy.is_master),
                            "status": policy.status,
                        }
                        for policy in policies
                    ],
                    "internal_rules": [
                        {
                            "id": rule.id,
                            "internal_rule_id": rule.internal_rule_id,
                            "name": rule.name,
                            "tenant_id": rule.tenant_id,
                            "status": rule.status,
                        }
                        for rule in internal_rules
                    ],
                    "monitoring_mappings": [
                        {
                            "id": mapping.id,
                            "internal_rule_id": mapping.internal_rule_id,
                            "monitoring_rule_id": mapping.monitoring_rule_id,
                            "tenant_id": mapping.tenant_id,
                            "mapping_type": mapping.mapping_type,
                        }
                        for mapping in mappings
                    ],
                    "monitoring_rules": [
                        {
                            "id": rule.id,
                            "rule_id": rule.rule_id,
                            "name": rule.name,
                            "severity": rule.severity,
                            "enabled": bool(rule.enabled),
                            "tenant_id": rule.tenant_id,
                        }
                        for rule in monitoring_rules
                    ],
                    "coverage": {
                        "has_policy": len(policies) > 0,
                        "has_internal_rule": len(internal_rules) > 0,
                        "has_monitoring_rule": len(monitoring_rules) > 0,
                    },
                }
            )

        return {
            "tenant_id": tenant_id,
            "generated_at": utc_now().isoformat(),
            "total_obligations": len(items),
            "items": items,
        }

    def get_coverage_report(self, tenant_id: str) -> Dict[str, Any]:
        chain = self.get_full_chain(tenant_id=tenant_id)
        return self.build_coverage_from_chain(chain)

    def find_gaps(self, tenant_id: str) -> Dict[str, Any]:
        chain = self.get_full_chain(tenant_id=tenant_id)
        items = chain["items"]

        obligations_without_policy: List[Dict[str, Any]] = []
        obligations_without_internal_rule: List[Dict[str, Any]] = []
        obligations_without_monitoring_rule: List[Dict[str, Any]] = []
        internal_rules_without_monitoring: List[Dict[str, Any]] = []

        policy_seen: Dict[int, Dict[str, Any]] = {}
        policy_has_internal_rule: Dict[int, bool] = {}

        for item in items:
            obligation_payload = item["obligation"]
            policies = item["policies"]
            internal_rules = item["internal_rules"]
            monitoring_rules = item["monitoring_rules"]

            if not policies:
                obligations_without_policy.append(obligation_payload)
            if not internal_rules:
                obligations_without_internal_rule.append(obligation_payload)
            if not monitoring_rules:
                obligations_without_monitoring_rule.append(obligation_payload)

            for policy in policies:
                policy_seen[policy["id"]] = policy
                policy_has_internal_rule.setdefault(policy["id"], False)
                if internal_rules:
                    policy_has_internal_rule[policy["id"]] = True

            mapped_internal_rule_ids = {
                mapping["internal_rule_id"]
                for mapping in item["monitoring_mappings"]
                if mapping.get("monitoring_rule_id") is not None
            }
            for internal_rule in internal_rules:
                if internal_rule["id"] not in mapped_internal_rule_ids:
                    internal_rules_without_monitoring.append(internal_rule)

        dedup_internal = self._deduplicate_by_id(internal_rules_without_monitoring)
        policies_without_internal_rule = [
            policy
            for policy_id, policy in policy_seen.items()
            if not policy_has_internal_rule.get(policy_id, False)
        ]

        return {
            "tenant_id": tenant_id,
            "generated_at": utc_now().isoformat(),
            "summary": {
                "obligations_without_policy": len(obligations_without_policy),
                "obligations_without_internal_rule": len(obligations_without_internal_rule),
                "obligations_without_monitoring_rule": len(obligations_without_monitoring_rule),
                "internal_rules_without_monitoring": len(dedup_internal),
                "policies_without_internal_rule": len(policies_without_internal_rule),
            },
            "gaps": {
                "obligations_without_policy": obligations_without_policy,
                "obligations_without_internal_rule": obligations_without_internal_rule,
                "obligations_without_monitoring_rule": obligations_without_monitoring_rule,
                "internal_rules_without_monitoring": dedup_internal,
                "policies_without_internal_rule": policies_without_internal_rule,
            },
        }

    def get_regulation_coverage(self, tenant_id: str, doc_id: int) -> Dict[str, Any]:
        chain = self.get_full_chain(tenant_id=tenant_id, regulation_doc_id=doc_id)
        coverage = self.build_coverage_from_chain(chain)

        regulation = self.db.query(LegalDocument).filter(LegalDocument.id == doc_id).first()
        return {
            "tenant_id": tenant_id,
            "regulation": (
                {
                    "id": regulation.id,
                    "celex": regulation.celex,
                    "title": regulation.title,
                }
                if regulation
                else {"id": doc_id}
            ),
            "coverage": coverage,
            "items": chain["items"],
        }

    def build_coverage_from_chain(self, chain: Dict[str, Any]) -> Dict[str, Any]:
        items = chain["items"]
        total = max(len(items), 1)

        obligations_with_policy = sum(1 for item in items if item["coverage"]["has_policy"])
        obligations_with_internal_rule = sum(
            1 for item in items if item["coverage"]["has_internal_rule"]
        )
        obligations_with_monitoring_rule = sum(
            1 for item in items if item["coverage"]["has_monitoring_rule"]
        )

        return {
            "tenant_id": chain["tenant_id"],
            "generated_at": chain["generated_at"],
            "total_obligations": len(items),
            "levels": {
                "policy": {
                    "covered": obligations_with_policy,
                    "coverage_pct": round(obligations_with_policy / total * 100, 2),
                },
                "internal_rule": {
                    "covered": obligations_with_internal_rule,
                    "coverage_pct": round(obligations_with_internal_rule / total * 100, 2),
                },
                "monitoring_rule": {
                    "covered": obligations_with_monitoring_rule,
                    "coverage_pct": round(obligations_with_monitoring_rule / total * 100, 2),
                },
            },
        }

    def _fetch_applicable_obligations(
        self,
        *,
        tenant_id: str,
        obligation_id: Optional[str],
        regulation_doc_id: Optional[int],
    ) -> List[RegulatoryObligation]:
        query = self.db.query(RegulatoryObligation).outerjoin(
            TenantObligationApplicability,
            and_(
                TenantObligationApplicability.obligation_id == RegulatoryObligation.id,
                TenantObligationApplicability.tenant_id == tenant_id,
            ),
        )
        query = query.filter(
            or_(
                TenantObligationApplicability.id.is_(None),
                TenantObligationApplicability.applicability.in_(APPLICABLE_STATUSES),
            )
        )

        if regulation_doc_id is not None:
            query = query.filter(RegulatoryObligation.doc_id == regulation_doc_id)

        if obligation_id:
            if str(obligation_id).isdigit():
                query = query.filter(
                    or_(
                        RegulatoryObligation.id == int(obligation_id),
                        RegulatoryObligation.obligation_id == str(obligation_id),
                    )
                )
            else:
                query = query.filter(RegulatoryObligation.obligation_id == str(obligation_id))

        return (
            query.order_by(RegulatoryObligation.doc_id.asc(), RegulatoryObligation.id.asc())
            .distinct()
            .all()
        )

    def _policies_for_obligation(
        self, *, obligation: RegulatoryObligation, tenant_id: str
    ) -> List[PolicyDocument]:
        policies_by_id: Dict[int, PolicyDocument] = {}

        if obligation.linked_policy_id:
            linked = (
                self.db.query(PolicyDocument)
                .filter(PolicyDocument.id == obligation.linked_policy_id)
                .first()
            )
            if linked and self._policy_visible_to_tenant(linked, tenant_id):
                policies_by_id[linked.id] = linked

        mapped = (
            self.db.query(PolicyDocument)
            .join(ObligationPolicyMapping, ObligationPolicyMapping.policy_id == PolicyDocument.id)
            .filter(ObligationPolicyMapping.obligation_id == obligation.id)
            .all()
        )
        for policy in mapped:
            if self._policy_visible_to_tenant(policy, tenant_id):
                policies_by_id[policy.id] = policy

        return list(policies_by_id.values())

    def _internal_rules_for_obligation(
        self, *, obligation_id: int, tenant_id: str
    ) -> List[InternalRule]:
        return (
            self.db.query(InternalRule)
            .filter(
                InternalRule.obligation_id == obligation_id,
                or_(
                    InternalRule.tenant_id == tenant_id,
                    InternalRule.tenant_id.is_(None),
                ),
            )
            .order_by(InternalRule.id.asc())
            .all()
        )

    def _monitoring_for_internal_rules(
        self,
        *,
        internal_rules: List[InternalRule],
        tenant_id: str,
    ) -> Tuple[List[InternalRuleMapping], List[MonitoringRule]]:
        if not internal_rules:
            return [], []

        internal_rule_ids = [rule.id for rule in internal_rules]
        mappings = (
            self.db.query(InternalRuleMapping)
            .filter(
                InternalRuleMapping.internal_rule_id.in_(internal_rule_ids),
                or_(
                    InternalRuleMapping.tenant_id == tenant_id,
                    InternalRuleMapping.tenant_id.is_(None),
                ),
            )
            .order_by(InternalRuleMapping.id.asc())
            .all()
        )

        monitoring_rule_ids = sorted(
            {
                mapping.monitoring_rule_id
                for mapping in mappings
                if mapping.monitoring_rule_id is not None
            }
        )
        if not monitoring_rule_ids:
            return mappings, []

        rules = (
            self.db.query(MonitoringRule)
            .filter(
                MonitoringRule.id.in_(monitoring_rule_ids),
                MonitoringRule.tenant_id == tenant_id,
            )
            .all()
        )
        rules_by_id = {rule.id: rule for rule in rules}
        valid_rules = [
            rules_by_id[rule_id] for rule_id in monitoring_rule_ids if rule_id in rules_by_id
        ]
        return mappings, valid_rules

    @staticmethod
    def _policy_visible_to_tenant(policy: PolicyDocument, tenant_id: str) -> bool:
        return policy.tenant_id in (None, tenant_id)

    @staticmethod
    def _deduplicate_by_id(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        deduplicated: Dict[Any, Dict[str, Any]] = {}
        for item in items:
            item_id = item.get("id")
            if item_id is not None:
                deduplicated[item_id] = item
        return list(deduplicated.values())
