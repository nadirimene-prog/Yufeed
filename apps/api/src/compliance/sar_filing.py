"""
SAR/UAR Filing System
Suspicious Activity Report and Unusual Activity Report filing capabilities.

Supports:
- FinCEN (US)
- National FIUs (EU)
- goAML (International)
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session


def utc_now() -> datetime:
    """Return current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)

from src.models.transaction_models import Case, Alert, Transaction
from src.models.models import LegalDocument
from src.ai.regulatory_enrichment import RegulatoryEnrichmentService

logger = logging.getLogger(__name__)


class SARFilingSystem:
    """
    Suspicious Activity Report filing system.
    Prepares and files SARs with appropriate authorities.
    """

    def __init__(self, db: Session):
        self.db = db
        self.enrichment_service = RegulatoryEnrichmentService(db)

    def prepare_sar(
        self,
        case_id: str,
        institution_info: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Prepare SAR from case investigation.

        Returns complete SAR structure ready for filing.
        """
        # Get case with related data
        case = self.db.query(Case).filter(Case.case_id == case_id).first()
        if not case:
            raise ValueError(f"Case {case_id} not found")

        # Get related alerts
        alerts = []
        if case.related_alert_ids:
            alerts = self.db.query(Alert).filter(
                Alert.id.in_(case.related_alert_ids)
            ).all()

        # Get related transactions
        transactions = []
        if case.related_transaction_ids:
            transactions = self.db.query(Transaction).filter(
                Transaction.id.in_(case.related_transaction_ids)
            ).all()

        # Get regulations
        regulations = []
        if case.applicable_regulation_ids:
            regulations = self.db.query(LegalDocument).filter(
                LegalDocument.id.in_(case.applicable_regulation_ids)
            ).all()

        # Generate AI-powered narrative if primary alert exists
        narrative = None
        if alerts:
            try:
                primary_alert = alerts[0]  # Use first alert
                sar_draft = self.enrichment_service.generate_sar_draft(
                    primary_alert.id,
                    include_narrative=True
                )
                narrative = sar_draft.get('narrative')
            except Exception as e:
                logger.error(f"Error generating SAR narrative: {e}")
                narrative = self._generate_manual_narrative(case, alerts, transactions)
        else:
            narrative = self._generate_manual_narrative(case, alerts, transactions)

        # Build SAR structure
        sar = {
            "sar_id": f"SAR-{utc_now().strftime('%Y%m%d')}-{case.case_id}",
            "filing_date": utc_now().isoformat(),
            "case_reference": case.case_id,

            # Filing institution
            "filing_institution": institution_info or self._get_default_institution_info(),

            # Subject information
            "subject_information": self._get_subject_info(case, transactions),

            # Suspicious activity
            "suspicious_activity": {
                "narrative": narrative,
                "activity_type": self._determine_activity_type(case, alerts),
                "activity_dates": self._get_activity_dates(transactions),
                "total_amount": self._calculate_total_amount(transactions),
                "transaction_count": len(transactions),
                "alert_count": len(alerts)
            },

            # Regulatory basis (YUFEED INNOVATION)
            "regulatory_basis": {
                "cited_regulations": [
                    {
                        "celex": reg.celex,
                        "title": reg.title,
                        "relevance": "Compliance obligation"
                    }
                    for reg in regulations
                ],
                "violations": case.regulatory_violations or {},
                "regulatory_context": self._build_regulatory_context(regulations)
            },

            # Supporting documentation
            "supporting_documents": {
                "alerts": [
                    {
                        "alert_id": alert.alert_id,
                        "type": alert.alert_type,
                        "severity": alert.severity,
                        "created_at": alert.created_at.isoformat()
                    }
                    for alert in alerts
                ],
                "evidence": case.evidence or {},
                "investigation_summary": case.summary
            },

            # Case details
            "case_details": {
                "case_id": case.case_id,
                "opened_at": case.opened_at.isoformat(),
                "closed_at": case.closed_at.isoformat() if case.closed_at else None,
                "investigated_by": case.assigned_to,
                "outcome": case.outcome
            },

            # Metadata
            "metadata": {
                "prepared_by": "Yufeed Compliance Platform",
                "preparation_date": utc_now().isoformat(),
                "version": "1.0"
            }
        }

        return sar

    def file_sar(
        self,
        sar_data: Dict[str, Any],
        jurisdiction: str = "EU",
        dry_run: bool = True
    ) -> Dict[str, Any]:
        """
        File SAR with appropriate authority.

        jurisdiction: "US" (FinCEN), "EU" (National FIU), "INTL" (goAML)
        dry_run: If True, validates but doesn't actually submit
        """
        # Validate SAR data
        validation = self._validate_sar(sar_data)
        if not validation['valid']:
            raise ValueError(f"SAR validation failed: {validation['errors']}")

        if dry_run:
            logger.info(f"Dry run: Would file SAR {sar_data['sar_id']} to {jurisdiction}")
            return {
                "status": "dry_run",
                "sar_id": sar_data['sar_id'],
                "jurisdiction": jurisdiction,
                "validation": validation,
                "message": "SAR validated successfully. Set dry_run=False to actually file."
            }

        # File based on jurisdiction
        if jurisdiction == "US":
            return self._file_with_fincen(sar_data)
        elif jurisdiction == "EU":
            return self._file_with_fiu(sar_data)
        else:
            return self._file_with_goaml(sar_data)

    def _get_subject_info(
        self,
        case: Case,
        transactions: List[Transaction]
    ) -> Dict[str, Any]:
        """Extract subject information from case."""
        if case.subject_type == 'user' and case.subject_id:
            # Get user details from transactions
            user_txs = [tx for tx in transactions if tx.user_id == case.subject_id]

            return {
                "type": "individual",
                "identifier": case.subject_id,
                "transaction_count": len(user_txs),
                "total_amount": sum(tx.amount for tx in user_txs),
                "countries_involved": list(set(tx.country_code for tx in user_txs if tx.country_code)),
                "first_activity": min(tx.timestamp for tx in user_txs) if user_txs else None,
                "last_activity": max(tx.timestamp for tx in user_txs) if user_txs else None
            }

        return {
            "type": case.subject_type or "unknown",
            "identifier": case.subject_id or "N/A"
        }

    def _determine_activity_type(
        self,
        case: Case,
        alerts: List[Alert]
    ) -> str:
        """Determine primary suspicious activity type."""
        if not alerts:
            return "Unknown"

        # Most common alert type
        alert_types = [a.alert_type for a in alerts]
        return max(set(alert_types), key=alert_types.count)

    def _get_activity_dates(
        self,
        transactions: List[Transaction]
    ) -> Dict[str, str]:
        """Get date range of suspicious activity."""
        if not transactions:
            return {"start": None, "end": None}

        timestamps = [tx.timestamp for tx in transactions]
        return {
            "start": min(timestamps).isoformat(),
            "end": max(timestamps).isoformat()
        }

    def _calculate_total_amount(
        self,
        transactions: List[Transaction]
    ) -> Dict[str, float]:
        """Calculate total amounts by currency."""
        from collections import defaultdict

        amounts = defaultdict(float)
        for tx in transactions:
            amounts[tx.currency] += float(tx.amount)

        return dict(amounts)

    def _build_regulatory_context(
        self,
        regulations: List[LegalDocument]
    ) -> str:
        """Build regulatory context explanation."""
        if not regulations:
            return "No specific regulations cited."

        context = "This SAR is filed in accordance with:\n\n"
        for reg in regulations:
            context += f"- {reg.celex}: {reg.title}\n"

        context += "\nThese regulations mandate reporting of suspicious transactions and unusual activity patterns."

        return context

    def _generate_manual_narrative(
        self,
        case: Case,
        alerts: List[Alert],
        transactions: List[Transaction]
    ) -> str:
        """Generate manual narrative when AI is unavailable."""
        narrative = f"Suspicious Activity Report\n\n"
        narrative += f"Case: {case.case_id}\n"
        narrative += f"Summary: {case.summary or case.description}\n\n"

        if alerts:
            narrative += f"Alerts Generated: {len(alerts)}\n"
            narrative += "Alert Types:\n"
            for alert in alerts:
                narrative += f"- {alert.alert_type} ({alert.severity})\n"
            narrative += "\n"

        if transactions:
            total = sum(tx.amount for tx in transactions)
            narrative += f"Transactions: {len(transactions)} totaling {total}\n\n"

        narrative += "Investigation concluded this activity warrants regulatory reporting."

        return narrative

    def _validate_sar(self, sar_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate SAR data completeness."""
        errors = []
        required_fields = [
            'sar_id',
            'filing_date',
            'filing_institution',
            'subject_information',
            'suspicious_activity'
        ]

        for field in required_fields:
            if field not in sar_data or not sar_data[field]:
                errors.append(f"Missing required field: {field}")

        # Validate narrative
        if 'narrative' not in sar_data.get('suspicious_activity', {}):
            errors.append("Missing suspicious activity narrative")

        return {
            "valid": len(errors) == 0,
            "errors": errors
        }

    def _get_default_institution_info(self) -> Dict[str, Any]:
        """Get default institution information."""
        return {
            "name": "Yufeed Compliance Platform",
            "type": "Financial Institution",
            "country": "EU",
            "contact": "compliance@yufeed.io"
        }

    def _file_with_fincen(self, sar_data: Dict) -> Dict:
        """File SAR with FinCEN (US)."""
        logger.info(f"Filing SAR {sar_data['sar_id']} with FinCEN")

        # TODO: Implement FinCEN BSA E-Filing API integration
        # https://bsaefiling.fincen.treas.gov/

        return {
            "status": "filed",
            "jurisdiction": "US_FinCEN",
            "sar_id": sar_data['sar_id'],
            "filing_reference": f"FINCEN-{sar_data['sar_id']}",
            "filed_at": utc_now().isoformat(),
            "note": "FinCEN integration pending - SAR prepared for manual filing"
        }

    def _file_with_fiu(self, sar_data: Dict) -> Dict:
        """File SAR with National FIU (EU)."""
        logger.info(f"Filing SAR {sar_data['sar_id']} with National FIU")

        # TODO: Implement National FIU integration
        # Each EU country has its own FIU (e.g., TRACFIN in France, BaFin in Germany)

        return {
            "status": "filed",
            "jurisdiction": "EU_National_FIU",
            "sar_id": sar_data['sar_id'],
            "filing_reference": f"FIU-{sar_data['sar_id']}",
            "filed_at": utc_now().isoformat(),
            "note": "National FIU integration pending - SAR prepared for manual filing"
        }

    def _file_with_goaml(self, sar_data: Dict) -> Dict:
        """File SAR with goAML (International)."""
        logger.info(f"Filing SAR {sar_data['sar_id']} with goAML")

        # TODO: Implement goAML API integration
        # https://www.unodc.org/unodc/en/money-laundering/goaml.html

        return {
            "status": "filed",
            "jurisdiction": "goAML",
            "sar_id": sar_data['sar_id'],
            "filing_reference": f"GOAML-{sar_data['sar_id']}",
            "filed_at": utc_now().isoformat(),
            "note": "goAML integration pending - SAR prepared for manual filing"
        }


class UARFilingSystem:
    """
    Unusual Activity Report filing system.
    Similar to SAR but for activities that don't meet SAR threshold.
    """

    def __init__(self, db: Session):
        self.db = db
        self.sar_system = SARFilingSystem(db)

    def prepare_uar(
        self,
        alert_id: int,
        institution_info: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Prepare UAR from an alert.

        UARs are for unusual but not necessarily suspicious activity.
        """
        alert = self.db.query(Alert).filter(Alert.id == alert_id).first()
        if not alert:
            raise ValueError(f"Alert {alert_id} not found")

        # Get transaction if available
        transaction = None
        if alert.transaction_id:
            transaction = self.db.query(Transaction).filter(
                Transaction.id == alert.transaction_id
            ).first()

        uar = {
            "uar_id": f"UAR-{utc_now().strftime('%Y%m%d')}-{alert.alert_id}",
            "filing_date": utc_now().isoformat(),
            "alert_reference": alert.alert_id,

            "filing_institution": institution_info or self.sar_system._get_default_institution_info(),

            "unusual_activity": {
                "type": alert.alert_type,
                "severity": alert.severity,
                "description": alert.description,
                "risk_score": float(alert.risk_score) if alert.risk_score else None
            },

            "transaction_details": {
                "transaction_id": transaction.transaction_id if transaction else None,
                "amount": float(transaction.amount) if transaction else None,
                "currency": transaction.currency if transaction else None,
                "timestamp": transaction.timestamp.isoformat() if transaction else None
            } if transaction else {},

            "metadata": {
                "prepared_by": "Yufeed Compliance Platform",
                "preparation_date": utc_now().isoformat()
            }
        }

        return uar

    def file_uar(
        self,
        uar_data: Dict[str, Any],
        jurisdiction: str = "EU"
    ) -> Dict[str, Any]:
        """File UAR with appropriate authority."""
        logger.info(f"Filing UAR {uar_data['uar_id']} to {jurisdiction}")

        # UAR filing is typically internal or to supervisory authority
        return {
            "status": "filed",
            "jurisdiction": jurisdiction,
            "uar_id": uar_data['uar_id'],
            "filed_at": utc_now().isoformat(),
            "note": "UAR filed internally for record keeping"
        }
