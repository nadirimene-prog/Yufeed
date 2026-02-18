from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from sqlalchemy.orm import Session

from src.database import SessionLocal
from src.models.compliance_workflow import PolicyTemplate


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


POLICY_TEMPLATES: List[Dict[str, Any]] = [
    # AML/CFT Policies
    {
        "template_id": "aml-cft-policy-master",
        "name": "AML/CFT Policy (Master)",
        "category": "AML/CFT",
        "regulatory_basis": ["AMLD5 Art. 8", "MiCA Art. 68"],
        "owner": "MLRO",
    },
    {
        "template_id": "customer-due-diligence-policy",
        "name": "Customer Due Diligence (CDD) Policy",
        "category": "AML/CFT",
        "regulatory_basis": ["AMLD5 Art. 13-14"],
        "owner": "MLRO",
    },
    {
        "template_id": "enhanced-due-diligence-policy",
        "name": "Enhanced Due Diligence (EDD) Policy",
        "category": "AML/CFT",
        "regulatory_basis": ["AMLD5 Art. 18-24"],
        "owner": "MLRO",
    },
    {
        "template_id": "kyc-kyb-procedures",
        "name": "KYC/KYB Procedures",
        "category": "AML/CFT",
        "regulatory_basis": ["AMLD5 Art. 13"],
        "owner": "Head of Compliance",
    },
    {
        "template_id": "sanctions-screening-policy",
        "name": "Sanctions Screening Policy",
        "category": "AML/CFT",
        "regulatory_basis": ["EU Sanctions Regulations"],
        "owner": "Head of Compliance",
    },
    {
        "template_id": "pep-identification-monitoring",
        "name": "PEP Identification & Monitoring",
        "category": "AML/CFT",
        "regulatory_basis": ["AMLD5 Art. 20-23"],
        "owner": "MLRO",
    },
    {
        "template_id": "suspicious-transaction-reporting",
        "name": "Suspicious Transaction Reporting (STR)",
        "category": "AML/CFT",
        "regulatory_basis": ["AMLD5 Art. 33-34"],
        "owner": "MLRO",
    },
    {
        "template_id": "travel-rule-compliance",
        "name": "Travel Rule Compliance (crypto)",
        "category": "AML/CFT",
        "regulatory_basis": ["MiCA Art. 76", "TFR"],
        "owner": "MLRO",
    },
    {
        "template_id": "record-keeping-policy",
        "name": "Record Keeping Policy",
        "category": "AML/CFT",
        "regulatory_basis": ["AMLD5 Art. 40"],
        "owner": "Head of Compliance",
    },
    # EMI-Specific Policies
    {
        "template_id": "safeguarding-policy",
        "name": "Safeguarding Policy",
        "category": "EMI",
        "regulatory_basis": ["EMD2 Art. 7"],
        "owner": "CFO",
    },
    {
        "template_id": "e-money-issuance-redemption",
        "name": "E-money Issuance & Redemption Policy",
        "category": "EMI",
        "regulatory_basis": ["EMD2 Art. 11"],
        "owner": "COO",
    },
    {
        "template_id": "payment-services-policy",
        "name": "Payment Services Policy",
        "category": "EMI",
        "regulatory_basis": ["PSD2 Art. 4"],
        "owner": "COO",
    },
    {
        "template_id": "strong-customer-authentication",
        "name": "Strong Customer Authentication (SCA)",
        "category": "EMI",
        "regulatory_basis": ["PSD2 Art. 97", "RTS"],
        "owner": "CTO",
    },
    {
        "template_id": "fraud-prevention-policy",
        "name": "Fraud Prevention Policy",
        "category": "EMI",
        "regulatory_basis": ["PSD2 Art. 96"],
        "owner": "Head of Risk",
    },
    {
        "template_id": "complaint-handling-procedure",
        "name": "Complaint Handling Procedure",
        "category": "EMI",
        "regulatory_basis": ["PSD2 Art. 101"],
        "owner": "Head of Compliance",
    },
    {
        "template_id": "outsourcing-policy",
        "name": "Outsourcing Policy",
        "category": "EMI",
        "regulatory_basis": ["EBA Guidelines"],
        "owner": "COO",
    },
    {
        "template_id": "agent-distributor-management",
        "name": "Agent/Distributor Management",
        "category": "EMI",
        "regulatory_basis": ["EMD2 Art. 3"],
        "owner": "COO",
    },
    # CASP-Specific Policies
    {
        "template_id": "crypto-asset-service-policy",
        "name": "Crypto-Asset Service Policy",
        "category": "CASP",
        "regulatory_basis": ["MiCA Art. 59-64"],
        "owner": "COO",
    },
    {
        "template_id": "custody-safekeeping-policy",
        "name": "Custody & Safekeeping Policy",
        "category": "CASP",
        "regulatory_basis": ["MiCA Art. 70"],
        "owner": "Head of Operations",
    },
    {
        "template_id": "order-execution-policy",
        "name": "Order Execution Policy",
        "category": "CASP",
        "regulatory_basis": ["MiCA Art. 73"],
        "owner": "Head of Trading",
    },
    {
        "template_id": "conflicts-of-interest-policy",
        "name": "Conflicts of Interest Policy",
        "category": "CASP",
        "regulatory_basis": ["MiCA Art. 72"],
        "owner": "Head of Compliance",
    },
    {
        "template_id": "market-abuse-prevention",
        "name": "Market Abuse Prevention",
        "category": "CASP",
        "regulatory_basis": ["MiCA Art. 86-92"],
        "owner": "Head of Compliance",
    },
    {
        "template_id": "white-paper-policy",
        "name": "White Paper Policy (if issuing)",
        "category": "CASP",
        "regulatory_basis": ["MiCA Art. 4-14"],
        "owner": "Head of Legal",
    },
    {
        "template_id": "token-listing-delisting-policy",
        "name": "Token Listing/Delisting Policy",
        "category": "CASP",
        "regulatory_basis": ["MiCA Art. 76"],
        "owner": "Head of Compliance",
    },
    {
        "template_id": "wallet-management-policy",
        "name": "Wallet Management Policy",
        "category": "CASP",
        "regulatory_basis": ["MiCA Art. 70"],
        "owner": "CTO",
    },
    # Governance & Risk
    {
        "template_id": "risk-management-framework",
        "name": "Risk Management Framework",
        "category": "Governance",
        "regulatory_basis": ["MiCA Art. 67", "EBA Guidelines"],
        "owner": "CRO",
    },
    {
        "template_id": "internal-control-policy",
        "name": "Internal Control Policy",
        "category": "Governance",
        "regulatory_basis": ["EMD2", "MiCA"],
        "owner": "CFO",
    },
    {
        "template_id": "compliance-monitoring-policy",
        "name": "Compliance Monitoring Policy",
        "category": "Governance",
        "regulatory_basis": ["MiCA Art. 68"],
        "owner": "Head of Compliance",
    },
    {
        "template_id": "business-continuity-plan",
        "name": "Business Continuity Plan (BCP)",
        "category": "Governance",
        "regulatory_basis": ["DORA Art. 11"],
        "owner": "COO",
    },
    {
        "template_id": "ict-risk-management-policy",
        "name": "ICT Risk Management Policy",
        "category": "Governance",
        "regulatory_basis": ["DORA Art. 5-14"],
        "owner": "CTO",
    },
    {
        "template_id": "incident-management-policy",
        "name": "Incident Management Policy",
        "category": "Governance",
        "regulatory_basis": ["DORA Art. 17", "PSD2 Art. 96"],
        "owner": "CTO",
    },
    {
        "template_id": "outsourcing-third-party-risk",
        "name": "Outsourcing & Third-Party Risk",
        "category": "Governance",
        "regulatory_basis": ["DORA Art. 28-30", "EBA Guidelines"],
        "owner": "COO",
    },
    {
        "template_id": "information-security-policy",
        "name": "Information Security Policy",
        "category": "Governance",
        "regulatory_basis": ["DORA", "GDPR"],
        "owner": "CISO",
    },
    # Data Protection (GDPR)
    {
        "template_id": "data-protection-policy",
        "name": "Data Protection Policy",
        "category": "GDPR",
        "regulatory_basis": ["GDPR Art. 24"],
        "owner": "DPO",
    },
    {
        "template_id": "data-retention-policy",
        "name": "Data Retention Policy",
        "category": "GDPR",
        "regulatory_basis": ["GDPR Art. 5", "AMLD5 Art. 40"],
        "owner": "DPO",
    },
    {
        "template_id": "data-subject-rights-procedure",
        "name": "Data Subject Rights Procedure",
        "category": "GDPR",
        "regulatory_basis": ["GDPR Art. 12-23"],
        "owner": "DPO",
    },
    {
        "template_id": "data-breach-response-plan",
        "name": "Data Breach Response Plan",
        "category": "GDPR",
        "regulatory_basis": ["GDPR Art. 33-34"],
        "owner": "DPO",
    },
    {
        "template_id": "privacy-notice",
        "name": "Privacy Notice",
        "category": "GDPR",
        "regulatory_basis": ["GDPR Art. 13-14"],
        "owner": "DPO",
    },
    # HR & Training
    {
        "template_id": "fit-and-proper-policy",
        "name": "Fit & Proper Policy",
        "category": "HR",
        "regulatory_basis": ["MiCA Art. 62", "EMD2"],
        "owner": "HR",
    },
    {
        "template_id": "staff-training-policy-aml",
        "name": "Staff Training Policy (AML)",
        "category": "HR",
        "regulatory_basis": ["AMLD5 Art. 46"],
        "owner": "HR",
    },
    {
        "template_id": "whistleblowing-policy",
        "name": "Whistleblowing Policy",
        "category": "HR",
        "regulatory_basis": ["EU Whistleblower Directive"],
        "owner": "HR",
    },
    {
        "template_id": "remuneration-policy",
        "name": "Remuneration Policy",
        "category": "HR",
        "regulatory_basis": ["MiCA Art. 66"],
        "owner": "HR",
    },
]


def _default_institution_types(template: Dict[str, Any]) -> List[str]:
    category = (template.get("category") or "").upper()
    template_id = (template.get("template_id") or "").lower()

    if category == "EMI":
        return ["pi", "emi"]
    if category == "CASP":
        return ["vasp"]
    if category == "AML/CFT":
        if "travel-rule" in template_id:
            return ["vasp"]
        return ["pi", "emi", "vasp"]
    if category in {"GDPR", "GOVERNANCE", "HR"}:
        return ["pi", "emi", "vasp"]
    return ["pi", "emi", "vasp"]


def _default_applicable_regulations(template: Dict[str, Any]) -> List[str]:
    basis = template.get("regulatory_basis") or []
    if isinstance(basis, list):
        return [str(item) for item in basis]
    return [str(basis)] if basis else []


def seed_policy_templates(db: Optional[Session] = None) -> dict:
    owns_session = db is None
    if db is None:
        db = SessionLocal()

    created = 0
    updated = 0

    try:
        for template in POLICY_TEMPLATES:
            existing = (
                db.query(PolicyTemplate)
                .filter(PolicyTemplate.template_id == template["template_id"])
                .first()
            )
            payload = {
                "name": template["name"],
                "category": template["category"],
                "version": template.get("version", "1.0"),
                "owner": template.get("owner"),
                "review_frequency_months": template.get("review_frequency_months", 12),
                "regulatory_basis": template.get("regulatory_basis"),
                "institution_types": template.get("institution_types")
                or _default_institution_types(template),
                "applicable_regulations": template.get("applicable_regulations")
                or _default_applicable_regulations(template),
                "source_url": template.get("source_url"),
                "content": template.get("content"),
                "metadata_json": template.get("metadata"),
                "is_active": template.get("is_active", True),
            }

            if existing:
                for key, value in payload.items():
                    setattr(existing, key, value)
                existing.updated_at = utc_now()
                updated += 1
            else:
                new_template = PolicyTemplate(
                    template_id=template["template_id"],
                    created_at=utc_now(),
                    updated_at=utc_now(),
                    **payload,
                )
                db.add(new_template)
                created += 1

        db.commit()
        return {"created": created, "updated": updated}
    except Exception:
        if owns_session:
            db.rollback()
        raise
    finally:
        if owns_session:
            db.close()
