"""
Compliance Gap Analyzer Service

Identifies obligations not covered by policies and calculates coverage metrics.
Provides actionable recommendations for closing compliance gaps.
"""

import logging
import re
import json
from datetime import datetime, timezone
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, text

from src.models.compliance_workflow import (
    RegulatoryObligation,
    PolicyDocument,
    PolicyTemplate,
    ObligationPolicyMapping,
    TenantObligationApplicability,
)
from src.models.models import LegalDocument

logger = logging.getLogger(__name__)


class CoverageStatus(str, Enum):
    """Coverage status of an obligation."""

    COVERED = "covered"
    PARTIAL = "partial"
    UNCOVERED = "uncovered"
    PENDING_REVIEW = "pending_review"


class GapSeverity(str, Enum):
    """Severity of a compliance gap."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ObligationCategory(str, Enum):
    """Categories for auto-classifying obligations."""

    KYC_KYB = "kyc_kyb"
    AML_MONITORING = "aml_monitoring"
    REPORTING = "reporting"
    RISK_ASSESSMENT = "risk_assessment"
    SANCTIONS = "sanctions"
    RECORD_KEEPING = "record_keeping"
    TRAINING = "training"
    GOVERNANCE = "governance"
    CUSTOMER_COMMUNICATION = "customer_communication"
    TECHNOLOGY = "technology"
    THIRD_PARTY = "third_party"
    OTHER = "other"


@dataclass
class CoverageMetric:
    """Coverage metric for a category or overall."""

    category: str
    total: int
    covered: int
    partial: int
    uncovered: int
    coverage_percentage: float
    trend: str = "stable"  # "up", "down", "stable"


@dataclass
class GapResult:
    """Represents a single compliance gap."""

    obligation_id: int
    obligation_text: str
    celex: str
    document_title: str
    article_ref: Optional[str]
    gap_type: str
    severity: GapSeverity
    category: ObligationCategory
    description: str
    suggested_template_id: Optional[str]
    suggested_template_name: Optional[str]
    ai_recommendation: Optional[str]
    effective_date: Optional[datetime]
    days_until_effective: Optional[int]


@dataclass
class GapAnalysisReport:
    """Complete gap analysis report."""

    overall_coverage: float
    total_obligations: int
    covered_count: int
    partial_count: int
    uncovered_count: int
    metrics: List[CoverageMetric]
    gaps: List[GapResult]
    recommendations: List[Dict]
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class GapAnalyzer:
    """
    Analyzes compliance gaps between obligations and policies.

    Features:
    - Calculate coverage metrics by category
    - Identify uncovered obligations
    - Suggest policy templates
    - Prioritize gaps by severity and deadline
    """

    # Keywords for auto-categorization
    CATEGORY_KEYWORDS = {
        ObligationCategory.KYC_KYB: [
            "customer due diligence",
            "cdd",
            "know your customer",
            "kyc",
            "know your business",
            "kyb",
            "identity verification",
            "onboarding",
            "customer identification",
            "beneficial owner",
            "ubo",
        ],
        ObligationCategory.AML_MONITORING: [
            "transaction monitoring",
            "suspicious activity",
            "suspicious transaction",
            "ongoing monitoring",
            "behavioral monitoring",
            "risk monitoring",
        ],
        ObligationCategory.REPORTING: [
            "suspicious transaction report",
            "str",
            "suspicious activity report",
            "sar",
            "currency transaction report",
            "ctr",
            "regulatory reporting",
            "report to authorities",
            "filing",
        ],
        ObligationCategory.RISK_ASSESSMENT: [
            "risk assessment",
            "risk rating",
            "risk evaluation",
            "business risk assessment",
            "enterprise risk",
        ],
        ObligationCategory.SANCTIONS: [
            "sanctions",
            "screening",
            "pep",
            "politically exposed person",
            "adverse media",
            "watchlist",
            "ofac",
            "eu list",
        ],
        ObligationCategory.RECORD_KEEPING: [
            "record keeping",
            "data retention",
            "document retention",
            "audit trail",
            "records management",
            "data storage",
        ],
        ObligationCategory.TRAINING: [
            "training",
            "staff training",
            "employee training",
            "compliance training",
            "awareness program",
        ],
        ObligationCategory.GOVERNANCE: [
            "governance",
            "mlro",
            "compliance officer",
            "senior management",
            "board",
            "internal control",
            "audit function",
        ],
        ObligationCategory.CUSTOMER_COMMUNICATION: [
            "customer communication",
            "notification to customer",
            "transparency",
            "disclosure",
            "privacy notice",
        ],
        ObligationCategory.TECHNOLOGY: [
            "technology",
            "system",
            "software",
            "it infrastructure",
            "automated",
            "algorithm",
            "digital",
        ],
        ObligationCategory.THIRD_PARTY: [
            "third party",
            "vendor",
            "outsourcing",
            "service provider",
            "agent",
            "distributor",
            "correspondent",
        ],
    }

    # Template suggestions by category
    TEMPLATE_SUGGESTIONS = {
        ObligationCategory.KYC_KYB: ["customer-due-diligence-policy", "kyc-kyb-procedures"],
        ObligationCategory.AML_MONITORING: [
            "aml-cft-policy-master",
            "transaction-monitoring-policy",
        ],
        ObligationCategory.REPORTING: [
            "suspicious-transaction-reporting",
            "regulatory-reporting-policy",
        ],
        ObligationCategory.SANCTIONS: [
            "sanctions-screening-policy",
            "pep-identification-monitoring",
        ],
        ObligationCategory.RECORD_KEEPING: ["record-keeping-policy"],
        ObligationCategory.TRAINING: ["staff-training-policy"],
        ObligationCategory.GOVERNANCE: ["compliance-governance-policy"],
        ObligationCategory.RISK_ASSESSMENT: ["risk-assessment-policy"],
    }

    def __init__(self, db: Session):
        self.db = db

    def auto_categorize_obligation(self, obligation_text: str) -> ObligationCategory:
        """
        Auto-categorize an obligation based on keyword matching.

        Args:
            obligation_text: The text of the obligation

        Returns:
            The most likely category
        """
        text_lower = obligation_text.lower()
        category_scores = defaultdict(int)

        for category, keywords in self.CATEGORY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    category_scores[category] += 1

        if category_scores:
            return max(category_scores.items(), key=lambda x: x[1])[0]

        return ObligationCategory.OTHER

    def calculate_severity(
        self,
        obligation: RegulatoryObligation,
        category: ObligationCategory,
        *,
        document_risk_level: Optional[str] = None,
    ) -> GapSeverity:
        """
        Calculate gap severity based on multiple factors.

        Factors:
        - Days until effective date
        - Risk level of obligation
        - Category criticality
        """
        severity_score = 0

        # Factor 1: Time until effective date
        if obligation.effective_date:
            days_until = (obligation.effective_date - datetime.now(timezone.utc)).days
            if days_until < 0:
                severity_score += 100  # Already in effect
            elif days_until < 7:
                severity_score += 80
            elif days_until < 30:
                severity_score += 60
            elif days_until < 90:
                severity_score += 40
            else:
                severity_score += 20
        else:
            severity_score += 50  # Unknown deadline = medium priority

        # Factor 2: Risk level from joined document row (avoid per-obligation lookup).
        if document_risk_level:
            risk_scores = {"critical": 50, "high": 40, "medium": 25, "low": 10}
            severity_score += risk_scores.get(document_risk_level.lower(), 20)

        # Factor 3: Category criticality
        critical_categories = [
            ObligationCategory.REPORTING,
            ObligationCategory.AML_MONITORING,
            ObligationCategory.SANCTIONS,
        ]
        if category in critical_categories:
            severity_score += 30

        # Map score to severity
        if severity_score >= 150:
            return GapSeverity.CRITICAL
        elif severity_score >= 100:
            return GapSeverity.HIGH
        elif severity_score >= 60:
            return GapSeverity.MEDIUM
        elif severity_score >= 30:
            return GapSeverity.LOW
        else:
            return GapSeverity.INFO

    def analyze_coverage(
        self,
        scope_filter: Optional[List[str]] = None,
        doc_id: Optional[int] = None,
        tenant_id: Optional[str] = None,
    ) -> GapAnalysisReport:
        """
        Run complete gap analysis.

        Returns comprehensive report with metrics and gaps.
        """
        logger.info("Starting gap analysis...")

        # 1. Get all obligations
        query = self.db.query(
            RegulatoryObligation, LegalDocument.celex, LegalDocument.title, LegalDocument.risk_level
        ).join(LegalDocument, RegulatoryObligation.doc_id == LegalDocument.id)

        if doc_id:
            query = query.filter(RegulatoryObligation.doc_id == doc_id)

        if scope_filter:
            # Filter by scope tags
            conditions = []
            for scope in scope_filter:
                conditions.append(LegalDocument.scope_tags.contains([scope]))
            query = query.filter(or_(*conditions))

        obligations = query.all()

        if tenant_id and obligations:
            obligation_ids = [row[0].id for row in obligations]
            applicability_rows = (
                self.db.query(TenantObligationApplicability)
                .filter(
                    TenantObligationApplicability.tenant_id == tenant_id,
                    TenantObligationApplicability.obligation_id.in_(obligation_ids),
                )
                .all()
            )
            applicability_by_obligation = {row.obligation_id: row for row in applicability_rows}
            allowed = {"applicable", "partially_applicable"}
            obligations = [
                row
                for row in obligations
                if (
                    applicability_by_obligation.get(row[0].id) is None
                    or applicability_by_obligation[row[0].id].applicability in allowed
                )
            ]

        # 2. Get all policy mappings
        mapping_query = self.db.query(
            ObligationPolicyMapping.obligation_id,
            ObligationPolicyMapping.policy_id,
            ObligationPolicyMapping.mapping_confidence,
        )
        if tenant_id:
            mapping_query = mapping_query.join(
                PolicyDocument,
                PolicyDocument.id == ObligationPolicyMapping.policy_id,
            ).filter(or_(PolicyDocument.tenant_id.is_(None), PolicyDocument.tenant_id == tenant_id))
        mappings = mapping_query.all()

        mapped_obligation_ids = {m[0] for m in mappings}
        linked_policy_ids = {
            row[0].linked_policy_id for row in obligations if row[0].linked_policy_id
        }
        policy_tenant_by_id = {}
        if linked_policy_ids:
            for policy in (
                self.db.query(PolicyDocument).filter(PolicyDocument.id.in_(linked_policy_ids)).all()
            ):
                policy_tenant_by_id[policy.id] = policy.tenant_id

        # 3. Calculate metrics by category
        category_stats = defaultdict(
            lambda: {"total": 0, "covered": 0, "partial": 0, "uncovered": 0}
        )

        gaps = []
        covered_count = 0
        partial_count = 0
        uncovered_count = 0

        suggested_template_ids = {
            template_id
            for template_ids in self.TEMPLATE_SUGGESTIONS.values()
            for template_id in template_ids
        }
        templates_by_id = {}
        if suggested_template_ids:
            templates = (
                self.db.query(PolicyTemplate)
                .filter(PolicyTemplate.template_id.in_(list(suggested_template_ids)))
                .all()
            )
            templates_by_id = {template.template_id: template for template in templates}

        for obl_row in obligations:
            obligation = obl_row[0]
            celex = obl_row[1]
            doc_title = obl_row[2]
            doc_risk_level = obl_row[3]

            # Auto-categorize if no persisted category attribute is present.
            raw_category = getattr(obligation, "category", None)
            if raw_category:
                try:
                    category = ObligationCategory(raw_category)
                except ValueError:
                    category = self.auto_categorize_obligation(obligation.obligation_text)
            else:
                category = self.auto_categorize_obligation(obligation.obligation_text)

            # Determine coverage status
            is_mapped = obligation.id in mapped_obligation_ids
            has_linked_policy = obligation.linked_policy_id is not None
            if has_linked_policy and tenant_id:
                linked_policy_tenant = policy_tenant_by_id.get(obligation.linked_policy_id)
                has_linked_policy = linked_policy_tenant in (None, tenant_id)

            if is_mapped or has_linked_policy:
                covered_count += 1
                category_stats[category]["covered"] += 1
            else:
                uncovered_count += 1
                category_stats[category]["uncovered"] += 1

                # Calculate severity
                severity = self.calculate_severity(
                    obligation,
                    category,
                    document_risk_level=doc_risk_level,
                )

                # Calculate days until effective
                days_until = None
                if obligation.effective_date:
                    days_until = (obligation.effective_date - datetime.now(timezone.utc)).days

                # Get suggested template
                suggested_templates = self.TEMPLATE_SUGGESTIONS.get(category, [])
                suggested_template_id = suggested_templates[0] if suggested_templates else None
                suggested_template_name = None

                if suggested_template_id:
                    template = templates_by_id.get(suggested_template_id)
                    if template:
                        suggested_template_name = template.name

                # Create gap result
                gap = GapResult(
                    obligation_id=obligation.id,
                    obligation_text=(
                        obligation.obligation_text[:200] + "..."
                        if len(obligation.obligation_text) > 200
                        else obligation.obligation_text
                    ),
                    celex=celex,
                    document_title=doc_title,
                    article_ref=obligation.article_ref,
                    gap_type="uncovered_obligation",
                    severity=severity,
                    category=category,
                    description=f"Obligation from {celex} Art. {obligation.article_ref or 'N/A'} is not covered by any policy",
                    suggested_template_id=suggested_template_id,
                    suggested_template_name=suggested_template_name,
                    ai_recommendation=None,  # Would call AI service here
                    effective_date=obligation.effective_date,
                    days_until_effective=days_until,
                )
                gaps.append(gap)

            category_stats[category]["total"] += 1

        # 4. Build metrics
        metrics = []
        for category, stats in category_stats.items():
            total = stats["total"]
            covered = stats["covered"]
            partial = stats["partial"]
            uncovered = stats["uncovered"]

            coverage_pct = (covered / total * 100) if total > 0 else 0

            metrics.append(
                CoverageMetric(
                    category=category.value,
                    total=total,
                    covered=covered,
                    partial=partial,
                    uncovered=uncovered,
                    coverage_percentage=round(coverage_pct, 1),
                )
            )

        # Sort by coverage percentage (ascending - worst first)
        metrics.sort(key=lambda x: x.coverage_percentage)

        # Sort gaps by severity
        severity_order = {
            GapSeverity.CRITICAL: 0,
            GapSeverity.HIGH: 1,
            GapSeverity.MEDIUM: 2,
            GapSeverity.LOW: 3,
            GapSeverity.INFO: 4,
        }
        gaps.sort(key=lambda x: (severity_order[x.severity], x.days_until_effective or 999))

        # 5. Generate recommendations
        recommendations = self._generate_recommendations(metrics, gaps)

        # 6. Calculate overall coverage
        total = len(obligations)
        overall_coverage = (covered_count / total * 100) if total > 0 else 0

        # 7. Store metrics
        self._store_metrics(metrics, overall_coverage)

        return GapAnalysisReport(
            overall_coverage=round(overall_coverage, 1),
            total_obligations=total,
            covered_count=covered_count,
            partial_count=partial_count,
            uncovered_count=uncovered_count,
            metrics=metrics,
            gaps=gaps,
            recommendations=recommendations,
        )

    def _generate_recommendations(
        self, metrics: List[CoverageMetric], gaps: List[GapResult]
    ) -> List[Dict]:
        """Generate actionable recommendations based on gaps."""
        recommendations = []

        # Find categories with worst coverage
        low_coverage = [m for m in metrics if m.coverage_percentage < 50]

        for metric in low_coverage[:3]:  # Top 3 problem areas
            category_gaps = [g for g in gaps if g.category.value == metric.category]
            critical_count = len(
                [g for g in category_gaps if g.severity in [GapSeverity.CRITICAL, GapSeverity.HIGH]]
            )

            recommendations.append(
                {
                    "priority": "high",
                    "category": metric.category,
                    "title": f"Address {metric.category} Coverage Gap",
                    "description": f"Only {metric.coverage_percentage}% of {metric.category} obligations are covered. {critical_count} critical gaps identified.",
                    "action": f"Create or update {metric.category} policies",
                    "estimated_effort": "2-3 days",
                    "obligations_count": metric.uncovered,
                }
            )

        # Add time-sensitive recommendations
        urgent_gaps = [g for g in gaps if g.days_until_effective and g.days_until_effective < 30]
        if urgent_gaps:
            recommendations.append(
                {
                    "priority": "critical",
                    "category": "time_sensitive",
                    "title": f"Address {len(urgent_gaps)} Urgent Deadlines",
                    "description": f"{len(urgent_gaps)} obligations become effective within 30 days without policy coverage.",
                    "action": "Immediately prioritize policy creation for upcoming deadlines",
                    "estimated_effort": "1 week",
                    "obligations_count": len(urgent_gaps),
                }
            )

        return recommendations

    def _store_metrics(self, metrics: List[CoverageMetric], overall_coverage: float):
        """Store calculated metrics in database."""
        try:
            # Store overall metric
            self.db.execute(
                text(
                    """
                INSERT INTO coverage_metrics
                (metric_type, category, total_count, covered_count, coverage_percentage, details_json)
                VALUES ('overall', 'all', :total, :covered, :percentage, :details)
            """
                ),
                {
                    "total": sum(m.total for m in metrics),
                    "covered": sum(m.covered for m in metrics),
                    "percentage": overall_coverage,
                    "details": json.dumps(
                        {
                            "by_category": [
                                {"cat": m.category, "pct": m.coverage_percentage} for m in metrics
                            ]
                        }
                    ),
                },
            )

            # Store category metrics
            for metric in metrics:
                self.db.execute(
                    text(
                        """
                    INSERT INTO coverage_metrics
                    (metric_type, category, total_count, covered_count, coverage_percentage)
                    VALUES ('category', :category, :total, :covered, :percentage)
                """
                    ),
                    {
                        "category": metric.category,
                        "total": metric.total,
                        "covered": metric.covered,
                        "percentage": metric.coverage_percentage,
                    },
                )

            self.db.commit()
        except Exception as e:
            logger.error(f"Failed to store metrics: {e}")

    def map_obligation_to_policy(
        self,
        obligation_id: int,
        policy_id: int,
        mapped_by: str = "manual",
        confidence: float = 1.0,
        notes: Optional[str] = None,
    ):
        """
        Create a mapping between an obligation and a policy.

        Args:
            obligation_id: The obligation ID
            policy_id: The policy ID
            mapped_by: Who/what created the mapping
            confidence: Confidence level (0-1)
            notes: Optional notes
        """
        try:
            mapping = (
                self.db.query(ObligationPolicyMapping)
                .filter(
                    ObligationPolicyMapping.obligation_id == obligation_id,
                    ObligationPolicyMapping.policy_id == policy_id,
                )
                .first()
            )
            if mapping is None:
                mapping = ObligationPolicyMapping(
                    obligation_id=obligation_id,
                    policy_id=policy_id,
                )
                self.db.add(mapping)

            mapping.mapped_by = mapped_by
            mapping.mapping_confidence = confidence
            mapping.notes = notes
            mapping.mapped_at = datetime.now(timezone.utc)

            obligation = (
                self.db.query(RegulatoryObligation)
                .filter(RegulatoryObligation.id == obligation_id)
                .first()
            )
            if obligation:
                obligation.linked_policy_id = policy_id
                obligation.updated_at = datetime.now(timezone.utc)

            self.db.commit()
            logger.info(f"Mapped obligation {obligation_id} to policy {policy_id}")

        except Exception as e:
            logger.error(f"Failed to map obligation to policy: {e}")
            self.db.rollback()
            raise

    def get_coverage_trend(self, days: int = 30) -> List[Dict]:
        """
        Get coverage trend over time.

        Returns daily coverage percentages for the specified period.
        """
        results = self.db.execute(
            text(
                """
            SELECT
                date(calculated_at) as date,
                AVG(coverage_percentage) as avg_coverage,
                COUNT(*) as data_points
            FROM coverage_metrics
            WHERE metric_type = 'overall'
            AND calculated_at > datetime('now', :days)
            GROUP BY date(calculated_at)
            ORDER BY date
        """
            ),
            {"days": f"-{days} days"},
        ).fetchall()

        return [
            {"date": row[0], "coverage_percentage": round(row[1], 1), "samples": row[2]}
            for row in results
        ]


# Global instance
def get_gap_analyzer(db: Session) -> GapAnalyzer:
    """Get gap analyzer instance."""
    return GapAnalyzer(db)
