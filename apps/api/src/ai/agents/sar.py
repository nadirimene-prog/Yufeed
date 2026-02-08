"""
SAR (Suspicious Activity Report) Filing Agent

Generates SAR narratives and prepares filings for EU FIUs and goAML.
This agent handles the full SAR lifecycle from draft generation to filing.

Features:
- AI-generated narratives using Claude
- EU FIU XML format generation
- goAML format support
- Multi-jurisdiction compliance
- Amendment workflow support
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone


def utc_now() -> datetime:
    """Return current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


from enum import Enum
from typing import Any, Dict, List, Optional
import xml.etree.ElementTree as ET
from xml.dom import minidom

from .base import BaseAgent, AgentContext, AgentResult, AgentRegistry, AgentType

logger = logging.getLogger(__name__)


class SARStatus(str, Enum):
    """SAR filing status."""

    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    FILED = "filed"
    ACKNOWLEDGED = "acknowledged"
    REJECTED = "rejected"
    AMENDED = "amended"


class FilingJurisdiction(str, Enum):
    """Supported filing jurisdictions."""

    EU_GENERIC = "eu_generic"  # Generic EU FIU format
    FRANCE_TRACFIN = "france_tracfin"
    GERMANY_FIU = "germany_fiu"
    NETHERLANDS_FIU = "netherlands_fiu"
    GOAML = "goaml"  # UN goAML standard


class SuspiciousActivityType(str, Enum):
    """Types of suspicious activities for SAR classification."""

    MONEY_LAUNDERING = "money_laundering"
    TERRORIST_FINANCING = "terrorist_financing"
    FRAUD = "fraud"
    TAX_EVASION = "tax_evasion"
    SANCTIONS_VIOLATION = "sanctions_violation"
    CORRUPTION = "corruption"
    HUMAN_TRAFFICKING = "human_trafficking"
    DRUG_TRAFFICKING = "drug_trafficking"
    OTHER = "other"


@dataclass
class SubjectInfo:
    """Information about a SAR subject (person or entity)."""

    subject_type: str  # "individual" or "entity"
    name: str
    aliases: List[str] = field(default_factory=list)

    # For individuals
    date_of_birth: Optional[str] = None
    place_of_birth: Optional[str] = None
    nationality: Optional[str] = None
    id_type: Optional[str] = None
    id_number: Optional[str] = None

    # For entities
    registration_number: Optional[str] = None
    registration_country: Optional[str] = None

    # Common
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    occupation: Optional[str] = None

    # Relationship to activity
    role: str = "subject"  # subject, beneficiary, conductor

    def to_dict(self) -> Dict[str, Any]:
        return {
            "subject_type": self.subject_type,
            "name": self.name,
            "aliases": self.aliases,
            "date_of_birth": self.date_of_birth,
            "place_of_birth": self.place_of_birth,
            "nationality": self.nationality,
            "id_type": self.id_type,
            "id_number": self.id_number,
            "registration_number": self.registration_number,
            "registration_country": self.registration_country,
            "address": self.address,
            "phone": self.phone,
            "email": self.email,
            "occupation": self.occupation,
            "role": self.role,
        }


@dataclass
class SARDraft:
    """A SAR draft ready for review or filing."""

    sar_id: str
    case_id: str
    status: SARStatus

    # Core narrative
    narrative: str
    executive_summary: str

    # Classification
    activity_types: List[SuspiciousActivityType]
    primary_activity: SuspiciousActivityType

    # Subjects
    subjects: List[SubjectInfo]

    # Financial details
    total_amount: float
    currency: str
    transaction_count: int
    date_range_start: str
    date_range_end: str

    # Indicators
    red_flags: List[str]
    regulatory_citations: List[str]

    # Filing info
    jurisdiction: FilingJurisdiction
    reporting_entity: str
    filing_date: Optional[str] = None
    acknowledgment_number: Optional[str] = None

    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: str = "ai_agent"
    reviewed_by: Optional[str] = None
    review_notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sar_id": self.sar_id,
            "case_id": self.case_id,
            "status": self.status.value,
            "narrative": self.narrative,
            "executive_summary": self.executive_summary,
            "activity_types": [at.value for at in self.activity_types],
            "primary_activity": self.primary_activity.value,
            "subjects": [s.to_dict() for s in self.subjects],
            "total_amount": self.total_amount,
            "currency": self.currency,
            "transaction_count": self.transaction_count,
            "date_range_start": self.date_range_start,
            "date_range_end": self.date_range_end,
            "red_flags": self.red_flags,
            "regulatory_citations": self.regulatory_citations,
            "jurisdiction": self.jurisdiction.value,
            "reporting_entity": self.reporting_entity,
            "filing_date": self.filing_date,
            "acknowledgment_number": self.acknowledgment_number,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
            "reviewed_by": self.reviewed_by,
            "review_notes": self.review_notes,
        }


@AgentRegistry.register("sar_agent")
class SARAgent(BaseAgent):
    """
    SAR Filing Agent for generating and managing Suspicious Activity Reports.

    This agent:
    1. Analyzes case data to generate SAR narratives
    2. Extracts subject information
    3. Identifies suspicious activity patterns
    4. Maps findings to SAR form fields
    5. Generates jurisdiction-specific filing formats
    """

    SAR_NARRATIVE_PROMPT = """You are an expert AML/CFT SAR Filing Agent specializing in EU regulations.

Your task is to generate a comprehensive Suspicious Activity Report (SAR) narrative based on the case data provided.

## EU Regulatory Context
- AMLD 5 (Directive 2018/843): Enhanced reporting requirements
- AMLD 6 (Directive 2018/1673): Criminal offenses and penalties
- EBA Guidelines on AML/CFT: Reporting obligations
- National FIU requirements may vary

## Case Information
{case_data}

## Investigation Summary (if available)
{investigation_summary}

## Transaction Details
{transaction_details}

## Instructions

Generate a SAR filing package with the following components:

1. **Executive Summary** (2-3 sentences)
   - Brief description of suspicious activity
   - Key subjects involved
   - Total amounts and timeframe

2. **Detailed Narrative** (comprehensive)
   Structure the narrative as follows:
   - **Introduction**: Who is involved, relationship to reporting entity
   - **Account/Transaction History**: Relevant background
   - **Suspicious Activity Description**: What happened, when, how
   - **Pattern Analysis**: Why this is suspicious
   - **Red Flags Identified**: Specific AML indicators
   - **Additional Information**: Any other relevant details

3. **Activity Classification**
   - Primary suspicious activity type
   - Secondary activity types if applicable

4. **Subject Information**
   - Extract all subjects (individuals and entities)
   - Include their roles (subject, beneficiary, conductor)

5. **Red Flags**
   - List specific red flags observed
   - Reference relevant regulations

## Response Format (JSON)
{{
    "executive_summary": "Brief 2-3 sentence summary",
    "narrative": "Full detailed narrative (500-1000 words)",
    "primary_activity": "money_laundering|terrorist_financing|fraud|tax_evasion|sanctions_violation|corruption|human_trafficking|drug_trafficking|other",
    "secondary_activities": ["list of other activity types"],
    "subjects": [
        {{
            "subject_type": "individual|entity",
            "name": "Full name",
            "role": "subject|beneficiary|conductor",
            "date_of_birth": "YYYY-MM-DD or null",
            "nationality": "Country or null",
            "id_type": "passport|national_id|etc or null",
            "id_number": "ID number or null",
            "address": "Address or null",
            "occupation": "Occupation or null"
        }}
    ],
    "red_flags": ["List of specific red flags"],
    "regulatory_citations": ["Relevant EU regulations and articles"],
    "confidence": "high|medium|low",
    "filing_urgency": "immediate|urgent|routine",
    "additional_investigation_needed": true|false,
    "notes_for_reviewer": "Any notes for human reviewer"
}}

Important:
- Be factual and objective - avoid speculation
- Use precise regulatory terminology
- Include specific transaction amounts and dates
- Maintain subject privacy where appropriate
- Flag any information gaps
"""

    @property
    def agent_type(self) -> AgentType:
        return AgentType.SAR

    @property
    def system_prompt(self) -> str:
        return self.SAR_NARRATIVE_PROMPT

    def __init__(self):
        super().__init__()
        self.agent_id = "sar_agent"
        self.name = "SAR Filing Agent"
        self.description = "Generates SAR narratives and prepares regulatory filings"

    async def process(self, context: AgentContext) -> AgentResult:
        """
        Generate a SAR draft from case data.

        Expected context.input_data:
        - case_id: The case identifier
        - case_data: Full case information
        - investigation_summary: Optional investigation results
        - transactions: List of suspicious transactions
        - jurisdiction: Target filing jurisdiction
        """
        logger.info(f"SAR Agent processing case: {context.input_data.get('case_id')}")

        try:
            # Extract inputs
            case_id = context.input_data.get("case_id", "unknown")
            case_data = context.input_data.get("case_data", {})
            investigation_summary = context.input_data.get("investigation_summary", "Not available")
            transactions = context.input_data.get("transactions", [])
            jurisdiction = context.input_data.get("jurisdiction", FilingJurisdiction.EU_GENERIC)

            # Format transaction details
            transaction_details = self._format_transactions(transactions)

            # Build the prompt
            prompt = self.SAR_NARRATIVE_PROMPT.format(
                case_data=self._format_case_data(case_data),
                investigation_summary=(
                    investigation_summary
                    if isinstance(investigation_summary, str)
                    else str(investigation_summary)
                ),
                transaction_details=transaction_details,
            )

            # Call Claude for narrative generation
            response = await self.call_claude(prompt, context)

            # Parse and validate response
            sar_draft = self._build_sar_draft(
                case_id=case_id,
                response=response,
                transactions=transactions,
                jurisdiction=jurisdiction,
                case_data=case_data,
            )

            # Calculate confidence
            confidence = self.calculate_confidence(response)

            return AgentResult(
                agent_id=self.agent_id,
                success=True,
                result=sar_draft.to_dict(),
                confidence=confidence,
                reasoning=f"Generated SAR narrative for case {case_id}",
                metadata={
                    "activity_type": sar_draft.primary_activity.value,
                    "subject_count": len(sar_draft.subjects),
                    "red_flag_count": len(sar_draft.red_flags),
                    "filing_urgency": response.get("filing_urgency", "routine"),
                },
            )

        except Exception as e:
            logger.error(f"SAR Agent error: {e}")
            return AgentResult(
                agent_id=self.agent_id,
                success=False,
                result=None,
                confidence=0.0,
                reasoning=f"SAR generation failed: {str(e)}",
                error=str(e),
            )

    def _format_case_data(self, case_data: Dict[str, Any]) -> str:
        """Format case data for the prompt."""
        if not case_data:
            return "No case data available"

        lines = []
        lines.append(f"Case ID: {case_data.get('id', 'Unknown')}")
        lines.append(f"Case Type: {case_data.get('type', 'Unknown')}")
        lines.append(f"Status: {case_data.get('status', 'Unknown')}")
        lines.append(f"Priority: {case_data.get('priority', 'Unknown')}")
        lines.append(f"Created: {case_data.get('created_at', 'Unknown')}")

        if case_data.get("description"):
            lines.append(f"\nDescription: {case_data['description']}")

        if case_data.get("customer"):
            customer = case_data["customer"]
            lines.append(f"\nCustomer: {customer.get('name', 'Unknown')}")
            lines.append(f"Customer ID: {customer.get('id', 'Unknown')}")
            lines.append(f"Risk Rating: {customer.get('risk_rating', 'Unknown')}")

        if case_data.get("alerts"):
            lines.append(f"\nRelated Alerts: {len(case_data['alerts'])}")

        return "\n".join(lines)

    def _format_transactions(self, transactions: List[Dict[str, Any]]) -> str:
        """Format transactions for the prompt."""
        if not transactions:
            return "No transaction details available"

        lines = [f"Total Transactions: {len(transactions)}\n"]

        # Calculate totals
        total_amount = sum(t.get("amount", 0) for t in transactions)
        currencies = set(t.get("currency", "EUR") for t in transactions)

        lines.append(f"Total Amount: {total_amount:,.2f} {'/'.join(currencies)}")

        # Date range
        dates = [
            t.get("timestamp") or t.get("date")
            for t in transactions
            if t.get("timestamp") or t.get("date")
        ]
        if dates:
            lines.append(f"Date Range: {min(dates)} to {max(dates)}")

        lines.append("\nTransaction Summary:")

        # Show first 10 transactions in detail
        for i, txn in enumerate(transactions[:10]):
            lines.append(f"\n  Transaction {i+1}:")
            lines.append(f"    Amount: {txn.get('amount', 0):,.2f} {txn.get('currency', 'EUR')}")
            lines.append(f"    Type: {txn.get('type', 'Unknown')}")
            lines.append(f"    Date: {txn.get('timestamp') or txn.get('date', 'Unknown')}")

            if txn.get("sender"):
                lines.append(f"    Sender: {txn['sender']}")
            if txn.get("receiver") or txn.get("recipient"):
                lines.append(f"    Receiver: {txn.get('receiver') or txn.get('recipient')}")
            if txn.get("country"):
                lines.append(f"    Country: {txn['country']}")
            if txn.get("risk_score"):
                lines.append(f"    Risk Score: {txn['risk_score']}")

        if len(transactions) > 10:
            lines.append(f"\n  ... and {len(transactions) - 10} more transactions")

        return "\n".join(lines)

    def _build_sar_draft(
        self,
        case_id: str,
        response: Dict[str, Any],
        transactions: List[Dict[str, Any]],
        jurisdiction: FilingJurisdiction,
        case_data: Dict[str, Any],
    ) -> SARDraft:
        """Build a SARDraft from Claude's response."""

        # Parse activity types
        primary_activity = self._parse_activity_type(response.get("primary_activity", "other"))
        secondary_activities = [
            self._parse_activity_type(at) for at in response.get("secondary_activities", [])
        ]
        all_activities = [primary_activity] + secondary_activities

        # Parse subjects
        subjects = [
            SubjectInfo(
                subject_type=s.get("subject_type", "individual"),
                name=s.get("name", "Unknown"),
                aliases=s.get("aliases", []),
                date_of_birth=s.get("date_of_birth"),
                place_of_birth=s.get("place_of_birth"),
                nationality=s.get("nationality"),
                id_type=s.get("id_type"),
                id_number=s.get("id_number"),
                registration_number=s.get("registration_number"),
                registration_country=s.get("registration_country"),
                address=s.get("address"),
                phone=s.get("phone"),
                email=s.get("email"),
                occupation=s.get("occupation"),
                role=s.get("role", "subject"),
            )
            for s in response.get("subjects", [])
        ]

        # Calculate financial totals
        total_amount = sum(t.get("amount", 0) for t in transactions)
        currency = transactions[0].get("currency", "EUR") if transactions else "EUR"

        # Date range
        dates = [
            t.get("timestamp") or t.get("date")
            for t in transactions
            if t.get("timestamp") or t.get("date")
        ]
        date_range_start = min(dates) if dates else utc_now().strftime("%Y-%m-%d")
        date_range_end = max(dates) if dates else utc_now().strftime("%Y-%m-%d")

        return SARDraft(
            sar_id=f"SAR-{case_id}-{utc_now().strftime('%Y%m%d%H%M%S')}",
            case_id=case_id,
            status=SARStatus.DRAFT,
            narrative=response.get("narrative", ""),
            executive_summary=response.get("executive_summary", ""),
            activity_types=all_activities,
            primary_activity=primary_activity,
            subjects=subjects,
            total_amount=total_amount,
            currency=currency,
            transaction_count=len(transactions),
            date_range_start=str(date_range_start),
            date_range_end=str(date_range_end),
            red_flags=response.get("red_flags", []),
            regulatory_citations=response.get("regulatory_citations", []),
            jurisdiction=(
                jurisdiction
                if isinstance(jurisdiction, FilingJurisdiction)
                else FilingJurisdiction(jurisdiction)
            ),
            reporting_entity=case_data.get("reporting_entity", "Yufeed Financial Institution"),
        )

    def _parse_activity_type(self, activity: str) -> SuspiciousActivityType:
        """Parse activity type string to enum."""
        activity_map = {
            "money_laundering": SuspiciousActivityType.MONEY_LAUNDERING,
            "terrorist_financing": SuspiciousActivityType.TERRORIST_FINANCING,
            "fraud": SuspiciousActivityType.FRAUD,
            "tax_evasion": SuspiciousActivityType.TAX_EVASION,
            "sanctions_violation": SuspiciousActivityType.SANCTIONS_VIOLATION,
            "corruption": SuspiciousActivityType.CORRUPTION,
            "human_trafficking": SuspiciousActivityType.HUMAN_TRAFFICKING,
            "drug_trafficking": SuspiciousActivityType.DRUG_TRAFFICKING,
        }
        return activity_map.get(activity.lower(), SuspiciousActivityType.OTHER)

    async def generate_goaml_xml(self, sar_draft: SARDraft) -> str:
        """
        Generate goAML XML format for the SAR.

        goAML is the UN standard for FIU reporting.
        """
        root = ET.Element("goAMLReport")
        root.set("version", "4.0")

        # Report header
        header = ET.SubElement(root, "reportHeader")
        ET.SubElement(header, "reportCode").text = sar_draft.sar_id
        ET.SubElement(header, "reportDate").text = utc_now().strftime("%Y-%m-%d")
        ET.SubElement(header, "reportingEntity").text = sar_draft.reporting_entity
        ET.SubElement(header, "reportReason").text = sar_draft.primary_activity.value

        # Subjects
        subjects_elem = ET.SubElement(root, "subjects")
        for subject in sar_draft.subjects:
            subject_elem = ET.SubElement(subjects_elem, "subject")
            ET.SubElement(subject_elem, "subjectType").text = subject.subject_type
            ET.SubElement(subject_elem, "name").text = subject.name
            ET.SubElement(subject_elem, "role").text = subject.role

            if subject.date_of_birth:
                ET.SubElement(subject_elem, "dateOfBirth").text = subject.date_of_birth
            if subject.nationality:
                ET.SubElement(subject_elem, "nationality").text = subject.nationality
            if subject.id_number:
                id_elem = ET.SubElement(subject_elem, "identification")
                ET.SubElement(id_elem, "idType").text = subject.id_type or "unknown"
                ET.SubElement(id_elem, "idNumber").text = subject.id_number

        # Transaction summary
        transactions = ET.SubElement(root, "transactions")
        ET.SubElement(transactions, "totalAmount").text = str(sar_draft.total_amount)
        ET.SubElement(transactions, "currency").text = sar_draft.currency
        ET.SubElement(transactions, "transactionCount").text = str(sar_draft.transaction_count)
        ET.SubElement(transactions, "dateFrom").text = sar_draft.date_range_start
        ET.SubElement(transactions, "dateTo").text = sar_draft.date_range_end

        # Narrative
        narrative = ET.SubElement(root, "narrative")
        ET.SubElement(narrative, "summary").text = sar_draft.executive_summary
        ET.SubElement(narrative, "details").text = sar_draft.narrative

        # Red flags
        indicators = ET.SubElement(root, "indicators")
        for flag in sar_draft.red_flags:
            ET.SubElement(indicators, "indicator").text = flag

        # Format with pretty print
        xml_str = ET.tostring(root, encoding="unicode")
        dom = minidom.parseString(xml_str)
        return dom.toprettyxml(indent="  ")

    async def generate_eu_fiu_format(self, sar_draft: SARDraft) -> Dict[str, Any]:
        """
        Generate generic EU FIU format.

        This is a JSON format that can be adapted to specific EU member state requirements.
        """
        return {
            "filing": {
                "type": "SAR",
                "version": "EU-FIU-1.0",
                "report_id": sar_draft.sar_id,
                "reporting_date": utc_now().isoformat(),
                "reporting_entity": {
                    "name": sar_draft.reporting_entity,
                    "type": "financial_institution",
                },
            },
            "suspicious_activity": {
                "type": sar_draft.primary_activity.value,
                "secondary_types": [at.value for at in sar_draft.activity_types[1:]],
                "date_from": sar_draft.date_range_start,
                "date_to": sar_draft.date_range_end,
                "total_amount": sar_draft.total_amount,
                "currency": sar_draft.currency,
            },
            "subjects": [s.to_dict() for s in sar_draft.subjects],
            "narrative": {
                "executive_summary": sar_draft.executive_summary,
                "detailed_description": sar_draft.narrative,
            },
            "indicators": {
                "red_flags": sar_draft.red_flags,
                "regulatory_references": sar_draft.regulatory_citations,
            },
            "transactions": {
                "count": sar_draft.transaction_count,
                "total_value": sar_draft.total_amount,
                "currency": sar_draft.currency,
            },
            "case_reference": sar_draft.case_id,
            "status": sar_draft.status.value,
        }


class SARWorkflowManager:
    """
    Manages SAR workflow from draft to filing.

    Workflow stages:
    1. Draft generation (AI)
    2. Human review
    3. Approval
    4. Filing
    5. Acknowledgment tracking
    """

    def __init__(self):
        self.agent = SARAgent()
        self._drafts: Dict[str, SARDraft] = {}  # In-memory storage for demo

    async def generate_draft(
        self,
        case_id: str,
        case_data: Dict[str, Any],
        transactions: List[Dict[str, Any]],
        investigation_summary: Optional[str] = None,
        jurisdiction: FilingJurisdiction = FilingJurisdiction.EU_GENERIC,
    ) -> SARDraft:
        """Generate a new SAR draft."""
        context = AgentContext(
            request_id=f"sar-{case_id}",
            user_id="system",
            input_data={
                "case_id": case_id,
                "case_data": case_data,
                "transactions": transactions,
                "investigation_summary": investigation_summary,
                "jurisdiction": jurisdiction,
            },
        )

        result = await self.agent.process(context)

        if result.success:
            # Reconstruct SARDraft from result
            draft_data = result.result
            draft = SARDraft(
                sar_id=draft_data["sar_id"],
                case_id=draft_data["case_id"],
                status=SARStatus(draft_data["status"]),
                narrative=draft_data["narrative"],
                executive_summary=draft_data["executive_summary"],
                activity_types=[SuspiciousActivityType(at) for at in draft_data["activity_types"]],
                primary_activity=SuspiciousActivityType(draft_data["primary_activity"]),
                subjects=[SubjectInfo(**s) for s in draft_data["subjects"]],
                total_amount=draft_data["total_amount"],
                currency=draft_data["currency"],
                transaction_count=draft_data["transaction_count"],
                date_range_start=draft_data["date_range_start"],
                date_range_end=draft_data["date_range_end"],
                red_flags=draft_data["red_flags"],
                regulatory_citations=draft_data["regulatory_citations"],
                jurisdiction=FilingJurisdiction(draft_data["jurisdiction"]),
                reporting_entity=draft_data["reporting_entity"],
            )
            self._drafts[draft.sar_id] = draft
            return draft
        else:
            raise Exception(f"SAR generation failed: {result.error}")

    async def submit_for_review(self, sar_id: str) -> SARDraft:
        """Submit a draft for human review."""
        if sar_id not in self._drafts:
            raise ValueError(f"SAR {sar_id} not found")

        draft = self._drafts[sar_id]
        draft.status = SARStatus.PENDING_REVIEW
        return draft

    async def approve(self, sar_id: str, reviewer: str, notes: Optional[str] = None) -> SARDraft:
        """Approve a SAR for filing."""
        if sar_id not in self._drafts:
            raise ValueError(f"SAR {sar_id} not found")

        draft = self._drafts[sar_id]
        draft.status = SARStatus.APPROVED
        draft.reviewed_by = reviewer
        draft.review_notes = notes
        return draft

    async def file(self, sar_id: str) -> SARDraft:
        """File an approved SAR."""
        if sar_id not in self._drafts:
            raise ValueError(f"SAR {sar_id} not found")

        draft = self._drafts[sar_id]

        if draft.status != SARStatus.APPROVED:
            raise ValueError(f"SAR must be approved before filing. Current status: {draft.status}")

        # In production, this would submit to the actual FIU
        draft.status = SARStatus.FILED
        draft.filing_date = utc_now().isoformat()
        draft.acknowledgment_number = f"ACK-{utc_now().strftime('%Y%m%d%H%M%S')}"

        return draft

    async def get_filing_format(self, sar_id: str, format_type: str = "eu_fiu") -> Any:
        """Get the SAR in a specific filing format."""
        if sar_id not in self._drafts:
            raise ValueError(f"SAR {sar_id} not found")

        draft = self._drafts[sar_id]

        if format_type == "goaml":
            return await self.agent.generate_goaml_xml(draft)
        else:
            return await self.agent.generate_eu_fiu_format(draft)

    def get_draft(self, sar_id: str) -> Optional[SARDraft]:
        """Get a SAR draft by ID."""
        return self._drafts.get(sar_id)

    def list_drafts(
        self, status: Optional[SARStatus] = None, case_id: Optional[str] = None
    ) -> List[SARDraft]:
        """List SAR drafts with optional filters."""
        drafts = list(self._drafts.values())

        if status:
            drafts = [d for d in drafts if d.status == status]
        if case_id:
            drafts = [d for d in drafts if d.case_id == case_id]

        return sorted(drafts, key=lambda d: d.created_at, reverse=True)
