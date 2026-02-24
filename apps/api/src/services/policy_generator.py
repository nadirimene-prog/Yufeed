"""
Smart Policy Generator Service

AI-powered policy generation from regulatory obligations.
Generates complete policy drafts with specific requirements.
"""

import json
import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Optional, Any

from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from src.models.compliance_workflow import (
    RegulatoryObligation,
    PolicyDocument,
    PolicyTemplate,
    PolicySection,
    ObligationPolicyMapping,
    InternalRule,
    InternalRuleMapping,
)
from src.models.models import LegalDocument
from src.models.transaction_models import MonitoringRule
from src.services.rules_engine import RuleBuilder
from src.tenancy.context import get_current_tenant
from src.config import settings

logger = logging.getLogger(__name__)


def _is_missing_sqlite_table_error(exc: Exception, *table_names: str) -> bool:
    message = str(exc).lower()
    if "sqlite" not in message or "no such table" not in message:
        return False
    return not table_names or any(table.lower() in message for table in table_names)


@dataclass
class PolicyGenerationRequest:
    """Request to generate a policy."""

    template_id: str
    obligation_ids: List[int]
    variable_values: Dict[str, Any]
    base_policy_id: Optional[int] = None
    created_by: str = ""


@dataclass
class GeneratedPolicySection:
    """A section of a generated policy."""

    section_order: int
    title: str
    content: str
    source_obligations: List[int] = field(default_factory=list)
    ai_confidence: float = 0.0


@dataclass
class GenerationResult:
    """Result of policy generation."""

    job_id: str
    status: str
    generated_content: str
    sections: List[GeneratedPolicySection]
    summary: str
    obligations_covered: List[int]
    variables_used: Dict[str, Any]
    ai_confidence: float
    word_count: int
    estimated_reading_time: int


class PolicyGenerator:
    """
    AI-powered policy generator.

    Generates complete policy documents from:
    - Selected obligations
    - Policy template structure
    - Organization-specific variables

    Features:
    - Template-based generation
    - Obligation-specific content
    - Variable substitution
    - AI content generation
    - Version control
    """

    def __init__(self, db: Session):
        self.db = db
        self.client = None
        if settings.ANTHROPIC_API_KEY:
            try:
                from anthropic import AsyncAnthropic

                self.client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
            except ImportError:
                logger.warning("anthropic not installed, AI generation disabled")

    async def generate_policy(self, request: PolicyGenerationRequest) -> GenerationResult:
        """
        Generate a complete policy from obligations.

        Args:
            request: Generation request with template, obligations, and variables

        Returns:
            GenerationResult with complete policy content
        """
        # 1. Create generation job
        job_id = str(uuid.uuid4())
        self._create_job(job_id, request)

        try:
            # 2. Load template and obligations
            template = self._load_template(request.template_id)
            obligations = self._load_obligations(request.obligation_ids)
            sections = self._load_section_templates(request.template_id)
            variables = self._merge_variables(request.template_id, request.variable_values)

            # 3. Update job status
            self._update_job_status(job_id, "generating")

            # 4. Generate each section
            generated_sections = []
            for section in sections:
                generated = await self._generate_section(
                    section=section, obligations=obligations, variables=variables, template=template
                )
                generated_sections.append(generated)

            # 5. Combine into full policy
            full_content = self._combine_sections(generated_sections, template, variables)

            # 6. Generate summary
            summary = await self._generate_summary(full_content, obligations)

            # 7. Calculate metrics
            word_count = len(full_content.split())
            reading_time = word_count // 200  # ~200 words per minute
            avg_confidence = (
                sum(s.ai_confidence for s in generated_sections) / len(generated_sections)
                if generated_sections
                else 0
            )

            # 8. Save result
            result = GenerationResult(
                job_id=job_id,
                status="completed",
                generated_content=full_content,
                sections=generated_sections,
                summary=summary,
                obligations_covered=[o.id for o in obligations],
                variables_used=variables,
                ai_confidence=avg_confidence,
                word_count=word_count,
                estimated_reading_time=reading_time,
            )

            self._save_generation_result(job_id, result)
            self._update_job_status(job_id, "completed")

            return result

        except Exception as e:
            logger.error(f"Policy generation failed: {e}")
            self._update_job_status(job_id, "failed", error=str(e))
            raise

    def _create_job(self, job_id: str, request: PolicyGenerationRequest):
        """Create a generation job record."""
        self.db.execute(
            text(
                """
            INSERT INTO policy_generation_jobs
            (job_id, template_id, base_policy_id, status, obligations_json, created_by)
            VALUES (:job_id, :template_id, :base_id, 'pending', :obligations, :created_by)
        """
            ),
            {
                "job_id": job_id,
                "template_id": request.template_id,
                "base_id": request.base_policy_id,
                "obligations": json.dumps(request.obligation_ids),
                "created_by": request.created_by,
            },
        )
        self.db.commit()

    def _update_job_status(self, job_id: str, status: str, error: Optional[str] = None):
        """Update job status."""
        if status == "generating":
            self.db.execute(
                text(
                    """
                UPDATE policy_generation_jobs
                SET status = :status, started_at = CURRENT_TIMESTAMP
                WHERE job_id = :job_id
            """
                ),
                {"job_id": job_id, "status": status},
            )
        elif status == "completed":
            self.db.execute(
                text(
                    """
                UPDATE policy_generation_jobs
                SET status = :status, completed_at = CURRENT_TIMESTAMP
                WHERE job_id = :job_id
            """
                ),
                {"job_id": job_id, "status": status},
            )
        elif status == "failed":
            self.db.execute(
                text(
                    """
                UPDATE policy_generation_jobs
                SET status = :status, error_message = :error, completed_at = CURRENT_TIMESTAMP
                WHERE job_id = :job_id
            """
                ),
                {"job_id": job_id, "status": status, "error": error},
            )
        self.db.commit()

    def _load_template(self, template_id: str) -> PolicyTemplate:
        """Load policy template."""
        template = (
            self.db.query(PolicyTemplate).filter(PolicyTemplate.template_id == template_id).first()
        )

        if not template:
            raise ValueError(f"Template {template_id} not found")

        return template

    def _load_obligations(self, obligation_ids: List[int]) -> List[RegulatoryObligation]:
        """Load obligations with document info."""
        obligations = (
            self.db.query(RegulatoryObligation, LegalDocument.celex, LegalDocument.title)
            .join(LegalDocument, RegulatoryObligation.doc_id == LegalDocument.id)
            .filter(RegulatoryObligation.id.in_(obligation_ids))
            .all()
        )

        # Enrich obligations with doc info
        result = []
        for obl, celex, title in obligations:
            obl._celex = celex
            obl._doc_title = title
            result.append(obl)

        return result

    def _load_section_templates(self, template_id: str) -> List[Dict]:
        """Load section templates for a policy template."""
        sections = self.db.execute(
            text(
                """
            SELECT
                section_name, section_order, title_template,
                content_template, ai_instructions, is_required, depends_on_obligations
            FROM policy_section_templates
            WHERE template_id = :template_id
            ORDER BY section_order
        """
            ),
            {"template_id": template_id},
        ).fetchall()

        return [
            {
                "name": s[0],
                "order": s[1],
                "title_template": s[2],
                "content_template": s[3],
                "ai_instructions": s[4],
                "required": s[5],
                "depends_on_obligations": s[6],
            }
            for s in sections
        ]

    def _merge_variables(self, template_id: str, provided_values: Dict[str, Any]) -> Dict[str, Any]:
        """Merge provided variables with template defaults."""
        # Load template variables
        try:
            template_vars = self.db.execute(
                text(
                    """
                SELECT variable_name, variable_type, default_value, is_required
                FROM policy_template_variables
                WHERE template_id = :template_id
            """
                ),
                {"template_id": template_id},
            ).fetchall()
        except OperationalError as exc:
            if _is_missing_sqlite_table_error(exc, "policy_template_variables"):
                return dict(provided_values or {})
            raise

        variables = {}
        for var_name, var_type, default, required in template_vars:
            if var_name in provided_values:
                variables[var_name] = provided_values[var_name]
            elif default:
                variables[var_name] = default
            elif required:
                variables[var_name] = f"[{var_name.upper()}]"

        return variables

    async def _generate_section(
        self,
        section: Dict,
        obligations: List[RegulatoryObligation],
        variables: Dict[str, Any],
        template: PolicyTemplate,
    ) -> GeneratedPolicySection:
        """Generate content for a policy section."""

        # Build section title
        title = section["title_template"]
        for var_name, var_value in variables.items():
            title = title.replace(f"{{{var_name}}}", str(var_value))

        # If section depends on obligations, generate AI content
        if section.get("depends_on_obligations") and obligations:
            content = await self._generate_ai_section(
                section=section, obligations=obligations, variables=variables
            )
            confidence = 0.85  # Placeholder for AI confidence
        else:
            # Use template content with variable substitution
            content = section.get("content_template", "")
            for var_name, var_value in variables.items():
                content = content.replace(f"{{{var_name}}}", str(var_value))
            confidence = 1.0  # Template content is certain

        return GeneratedPolicySection(
            section_order=section["order"],
            title=section["name"],
            content=content,
            source_obligations=(
                [o.id for o in obligations] if section.get("depends_on_obligations") else []
            ),
            ai_confidence=confidence,
        )

    async def _generate_ai_section(
        self, section: Dict, obligations: List[RegulatoryObligation], variables: Dict[str, Any]
    ) -> str:
        """Generate section content using AI."""

        if not self.client:
            # Fallback: Generate from obligations manually
            return self._generate_from_obligations(section, obligations)

        # Build prompt
        prompt = self._build_generation_prompt(section, obligations, variables)

        try:
            response = await self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=2000,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}],
            )

            return response.content[0].text

        except Exception as e:
            logger.error(f"AI generation failed: {e}")
            return self._generate_from_obligations(section, obligations)

    def _build_generation_prompt(
        self, section: Dict, obligations: List[RegulatoryObligation], variables: Dict[str, Any]
    ) -> str:
        """Build AI prompt for section generation."""

        # Build obligations text
        obligations_text = "\n\n".join(
            [
                f"Obligation {i+1}:\n"
                f"- Document: {o._doc_title} ({o._celex})\n"
                f"- Article: {o.article_ref or 'N/A'}\n"
                f"- Text: {o.obligation_text[:500]}{'...' if len(o.obligation_text) > 500 else ''}"
                for i, o in enumerate(obligations)
            ]
        )

        prompt = f"""You are a compliance policy writer. Generate the following policy section based on regulatory obligations.

Section: {section['name']}
Instructions: {section['ai_instructions']}

Institution: {variables.get('institution_name', '[Institution]')}
Jurisdiction: {variables.get('jurisdiction', '[Jurisdiction]')}
MLRO: {variables.get('mlro_name', '[MLRO]')}

Regulatory Obligations to Address:
{obligations_text}

Requirements:
1. Write professional policy language
2. Be specific and actionable
3. Reference specific regulations where applicable
4. Include clear procedures
5. Use numbered sections for clarity
6. Length: 300-800 words

Generate the policy section content only, without the title:"""

        return prompt

    def _generate_from_obligations(
        self, section: Dict, obligations: List[RegulatoryObligation]
    ) -> str:
        """Fallback: Generate section from obligations without AI."""

        content_parts = []

        if section.get("depends_on_obligations"):
            content_parts.append(f"### {section['name']}\n\n")
            content_parts.append(
                "This section addresses the following regulatory requirements:\n\n"
            )

            for i, obl in enumerate(obligations, 1):
                content_parts.append(f"{i}. **{obl._doc_title}** ({obl._celex})")
                if obl.article_ref:
                    content_parts.append(f", Article {obl.article_ref}")
                content_parts.append("\n")
                content_parts.append(
                    f"   - {obl.obligation_text[:300]}{'...' if len(obl.obligation_text) > 300 else ''}\n\n"
                )

            content_parts.append("\n### Implementation\n\n")
            content_parts.append("To comply with these obligations, the institution must:\n\n")
            content_parts.append("1. Implement appropriate procedures and controls\n")
            content_parts.append("2. Ensure staff are trained on these requirements\n")
            content_parts.append("3. Maintain adequate records\n")
            content_parts.append("4. Regularly review and update processes\n")
        else:
            content_parts.append(section.get("content_template", "TBD"))

        return "".join(content_parts)

    def _combine_sections(
        self,
        sections: List[GeneratedPolicySection],
        template: PolicyTemplate,
        variables: Dict[str, Any],
    ) -> str:
        """Combine sections into full policy document."""

        # Header
        header = f"""# {template.name}

**Institution:** {variables.get('institution_name', '[Institution Name]')}
**Version:** 1.0
**Effective Date:** {datetime.now(timezone.utc).strftime('%B %d, %Y')}
**Review Date:** {(datetime.now(timezone.utc).replace(year=datetime.now(timezone.utc).year + 1)).strftime('%B %d, %Y')}
**Approved By:** {variables.get('mlro_name', '[MLRO Name]')}

---

"""

        # Body
        body_parts = []
        for section in sorted(sections, key=lambda s: s.section_order):
            body_parts.append(f"## {section.title}\n\n")
            body_parts.append(section.content)
            body_parts.append("\n\n---\n\n")

        # Footer
        footer = f"""## Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | {datetime.now(timezone.utc).strftime('%Y-%m-%d')} | AI Policy Generator | Initial version |

**Related Documents:**
- Regulatory Basis: {template.regulatory_basis or 'See individual sections'}
- Owner: {template.owner or 'Compliance Team'}

*This policy was generated by the Yufeed AI Policy Generator*
"""

        return header + "".join(body_parts) + footer

    async def _generate_summary(self, content: str, obligations: List[RegulatoryObligation]) -> str:
        """Generate executive summary of the policy."""

        obl_summary = ", ".join([f"{o._doc_title} ({o._celex})" for o in obligations[:3]])
        if len(obligations) > 3:
            obl_summary += f" and {len(obligations) - 3} more"

        first_category = (
            getattr(obligations[0], "category", None) if obligations else None
        ) or "Compliance"

        summary = f"""This policy addresses {len(obligations)} regulatory obligations from {obl_summary}.

Key areas covered:
- {first_category} requirements
- Implementation procedures
- Roles and responsibilities
- Record keeping obligations

The policy is {len(content.split())} words and estimated reading time is {len(content.split()) // 200} minutes."""

        return summary

    def _save_generation_result(self, job_id: str, result: GenerationResult):
        """Save generation result to database."""
        self.db.execute(
            text(
                """
            UPDATE policy_generation_jobs
            SET generated_content = :content,
                generated_summary = :summary,
                ai_confidence = :confidence,
                ai_model = :model
            WHERE job_id = :job_id
        """
            ),
            {
                "job_id": job_id,
                "content": result.generated_content,
                "summary": result.summary,
                "confidence": result.ai_confidence,
                "model": "claude-3-haiku-20240307",
            },
        )

        # Save draft versions
        for section in result.sections:
            self.db.execute(
                text(
                    """
                INSERT INTO policy_draft_versions
                (generation_job_id, version_number, content, changes_summary, created_by)
                VALUES (:job_id, :section_order, :content, :summary, 'ai')
            """
                ),
                {
                    "job_id": job_id,
                    "section_order": section.section_order,
                    "content": f"## {section.title}\n\n{section.content}",
                    "summary": f"Section {section.section_order}: {section.title}",
                },
            )

        self.db.commit()

    def get_template_variables(self, template_id: str) -> List[Dict]:
        """Get all variables for a template."""
        try:
            variables = self.db.execute(
                text(
                    """
                SELECT
                    variable_name, variable_type, description,
                    default_value, is_required, placeholder, example_value
                FROM policy_template_variables
                WHERE template_id = :template_id
                ORDER BY variable_name
            """
                ),
                {"template_id": template_id},
            ).fetchall()
        except OperationalError as exc:
            if _is_missing_sqlite_table_error(exc, "policy_template_variables"):
                return []
            raise

        return [
            {
                "name": v[0],
                "type": v[1],
                "description": v[2],
                "default": v[3],
                "required": bool(v[4]),
                "placeholder": v[5],
                "example": v[6],
            }
            for v in variables
        ]

    def get_generation_status(self, job_id: str) -> Optional[Dict]:
        """Get status of a generation job."""
        job = self.db.execute(
            text(
                """
            SELECT
                job_id, template_id, status, generated_summary,
                ai_confidence, created_at, started_at, completed_at,
                error_message
            FROM policy_generation_jobs
            WHERE job_id = :job_id
        """
            ),
            {"job_id": job_id},
        ).fetchone()

        if not job:
            return None

        return {
            "job_id": job[0],
            "template_id": job[1],
            "status": job[2],
            "summary": job[3],
            "ai_confidence": job[4],
            "created_at": job[5].isoformat() if job[5] else None,
            "started_at": job[6].isoformat() if job[6] else None,
            "completed_at": job[7].isoformat() if job[7] else None,
            "error": job[8],
        }

    def get_generation_result(self, job_id: str) -> Optional[GenerationResult]:
        """Get complete generation result."""
        job = self.db.execute(
            text(
                """
            SELECT
                generated_content, generated_summary, obligations_json,
                ai_confidence, ai_model
            FROM policy_generation_jobs
            WHERE job_id = :job_id AND status = 'completed'
        """
            ),
            {"job_id": job_id},
        ).fetchone()

        if not job:
            return None

        # Load sections
        sections = self.db.execute(
            text(
                """
            SELECT version_number, content
            FROM policy_draft_versions
            WHERE generation_job_id = :job_id
            ORDER BY version_number
        """
            ),
            {"job_id": job_id},
        ).fetchall()

        generated_sections = []
        for section in sections:
            # Parse title from content
            lines = section[1].split("\n")
            title = lines[0].replace("## ", "").strip() if lines else "Section"
            content = "\n".join(lines[2:]) if len(lines) > 2 else section[1]

            generated_sections.append(
                GeneratedPolicySection(section_order=section[0], title=title, content=content)
            )

        return GenerationResult(
            job_id=job_id,
            status="completed",
            generated_content=job[0],
            sections=generated_sections,
            summary=job[1],
            obligations_covered=json.loads(job[2]) if job[2] else [],
            variables_used={},
            ai_confidence=job[3] or 0,
            word_count=len(job[0].split()) if job[0] else 0,
            estimated_reading_time=len(job[0].split()) // 200 if job[0] else 0,
        )

    def approve_generation(
        self, job_id: str, reviewed_by: str, notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Approve a generated policy and create the actual policy document.

        Returns:
            Dict with created policy ID and monitoring rule suggestions
        """
        # Get generation result
        result = self.get_generation_result(job_id)
        if not result:
            raise ValueError(f"Generation job {job_id} not found or not completed")

        tenant_id = get_current_tenant() or "default"

        # Create policy document
        policy = PolicyDocument(
            policy_id=f"POL-{uuid.uuid4().hex[:10].upper()}",
            tenant_id=tenant_id,
            is_master=False,
            master_policy_id=None,
            name=f"AI Generated Policy - {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
            status="draft",
            content=result.generated_content,
            version="1.0",
            owner=reviewed_by,
            metadata_json={
                "is_ai_generated": True,
                "generation_job_id": job_id,
                "ai_confidence_score": result.ai_confidence,
                "reviewed_by": reviewed_by,
            },
        )

        self.db.add(policy)
        self.db.commit()
        self.db.refresh(policy)

        # Update generation job
        self.db.execute(
            text(
                """
            UPDATE policy_generation_jobs
            SET status = 'approved',
                reviewed_by = :reviewer,
                reviewed_at = CURRENT_TIMESTAMP,
                review_notes = :notes,
                final_policy_id = :policy_id
            WHERE job_id = :job_id
        """
            ),
            {"job_id": job_id, "reviewer": reviewed_by, "notes": notes, "policy_id": policy.id},
        )

        # Update obligations and create explicit obligation->policy mappings.
        for obl_id in result.obligations_covered:
            obligation = (
                self.db.query(RegulatoryObligation)
                .filter(RegulatoryObligation.id == obl_id)
                .first()
            )
            if obligation:
                obligation.linked_policy_id = policy.id

            mapping = (
                self.db.query(ObligationPolicyMapping)
                .filter(
                    ObligationPolicyMapping.obligation_id == obl_id,
                    ObligationPolicyMapping.policy_id == policy.id,
                )
                .first()
            )
            if not mapping:
                mapping = ObligationPolicyMapping(
                    obligation_id=obl_id,
                    policy_id=policy.id,
                )
                self.db.add(mapping)
            mapping.mapped_by = f"user:{reviewed_by}"
            mapping.mapping_confidence = 1.0
            mapping.notes = "Auto-mapped from approved policy generation"
            mapping.mapped_at = datetime.now(timezone.utc)

        self.db.commit()

        suggestions = self._suggest_monitoring_rules(
            policy=policy,
            obligation_ids=result.obligations_covered,
            reviewed_by=reviewed_by,
            tenant_id=tenant_id,
        )

        logger.info(f"Policy generation {job_id} approved, created policy {policy.id}")

        return {
            "policy_id": policy.id,
            "suggested_monitoring_rules": suggestions,
            "suggestion_count": len(suggestions),
        }

    def _suggest_monitoring_rules(
        self,
        *,
        policy: PolicyDocument,
        obligation_ids: List[int],
        reviewed_by: str,
        tenant_id: str,
    ) -> List[Dict[str, Any]]:
        suggestions: List[Dict[str, Any]] = []

        for obl_id in obligation_ids:
            obligation = (
                self.db.query(RegulatoryObligation)
                .filter(RegulatoryObligation.id == obl_id)
                .first()
            )
            if not obligation:
                continue

            internal_rule = (
                self.db.query(InternalRule)
                .filter(
                    InternalRule.obligation_id == obligation.id,
                    InternalRule.tenant_id == tenant_id,
                )
                .first()
            )
            internal_rule_created = False
            if not internal_rule:
                internal_rule = InternalRule(
                    internal_rule_id=f"IR-{uuid.uuid4().hex[:8].upper()}",
                    tenant_id=tenant_id,
                    obligation_id=obligation.id,
                    name=f"Control for {obligation.obligation_id}",
                    description=(
                        f"Auto-generated control suggestion from approved policy {policy.policy_id}"
                    ),
                    control_owner=reviewed_by,
                    status="draft",
                )
                self.db.add(internal_rule)
                self.db.flush()
                internal_rule_created = True

            existing_mapping = (
                self.db.query(InternalRuleMapping)
                .filter(
                    InternalRuleMapping.internal_rule_id == internal_rule.id,
                    InternalRuleMapping.tenant_id == tenant_id,
                    InternalRuleMapping.monitoring_rule_id.is_not(None),
                )
                .first()
            )
            if existing_mapping:
                monitoring_rule = (
                    self.db.query(MonitoringRule)
                    .filter(MonitoringRule.id == existing_mapping.monitoring_rule_id)
                    .first()
                )
                suggestions.append(
                    {
                        "obligation_id": obligation.id,
                        "obligation_key": obligation.obligation_id,
                        "internal_rule_id": internal_rule.id,
                        "internal_rule_key": internal_rule.internal_rule_id,
                        "internal_rule_created": internal_rule_created,
                        "status": "already_mapped",
                        "existing_monitoring_rule": (
                            {
                                "id": monitoring_rule.id,
                                "rule_id": monitoring_rule.rule_id,
                                "name": monitoring_rule.name,
                            }
                            if monitoring_rule
                            else None
                        ),
                        "suggested_monitoring_rule": None,
                    }
                )
                continue

            suggestion_payload = self._build_monitoring_rule_suggestion(obligation)
            suggestions.append(
                {
                    "obligation_id": obligation.id,
                    "obligation_key": obligation.obligation_id,
                    "internal_rule_id": internal_rule.id,
                    "internal_rule_key": internal_rule.internal_rule_id,
                    "internal_rule_created": internal_rule_created,
                    "status": "suggested",
                    "existing_monitoring_rule": None,
                    "suggested_monitoring_rule": suggestion_payload,
                }
            )

        self.db.commit()
        return suggestions

    def _build_monitoring_rule_suggestion(self, obligation: RegulatoryObligation) -> Dict[str, Any]:
        text_value = (obligation.obligation_text or "").lower()
        article = obligation.article_ref
        source_id = obligation.doc_id
        base_name = f"Auto rule for {obligation.obligation_id}"

        if any(
            keyword in text_value for keyword in ["sanction", "high-risk country", "jurisdiction"]
        ):
            return RuleBuilder.create_high_risk_country_rule(
                name=base_name,
                country_codes=["IR", "KP", "SY", "RU", "BY"],
                regulatory_source_id=source_id,
                regulation_article=article,
                severity="high",
            )

        threshold = self._extract_amount_threshold(obligation.obligation_text or "")
        if threshold is not None:
            return RuleBuilder.create_transaction_limit_rule(
                name=base_name,
                amount_limit=threshold,
                currency="EUR",
                regulatory_source_id=source_id,
                regulation_article=article,
                regulatory_requirement=obligation.obligation_text[:500],
                severity="medium",
            )

        return RuleBuilder.create_velocity_rule(
            name=base_name,
            max_transactions=10,
            time_window_hours=24,
            regulatory_source_id=source_id,
            severity="medium",
        )

    @staticmethod
    def _extract_amount_threshold(obligation_text: str) -> Optional[Decimal]:
        number_matches = re.findall(r"(\d[\d,\.\s]{2,})", obligation_text or "")
        for raw in number_matches:
            normalized = raw.replace(" ", "").replace(",", "")
            try:
                value = Decimal(normalized)
            except InvalidOperation:
                continue
            if value >= Decimal("1000"):
                return value
        return None


# Global instance
def get_policy_generator(db: Session) -> PolicyGenerator:
    """Get policy generator instance."""
    return PolicyGenerator(db)
