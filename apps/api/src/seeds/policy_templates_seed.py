from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional, TypedDict

from sqlalchemy.orm import Session

from src.database import SessionLocal
from src.models.compliance_workflow import PolicyTemplate


class PolicyTemplateSeedSpec(TypedDict):
    template_id: str
    name: str
    category: str
    institution_types: List[str]
    applicable_regulations: List[str]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


STEP2_POLICY_TEMPLATES: List[PolicyTemplateSeedSpec] = [
    {
        "template_id": "step2-aml-cft-policy",
        "name": "Politique LCB-FT / AML",
        "category": "AML/CFT",
        "institution_types": ["pi", "emi", "vasp"],
        "applicable_regulations": ["AMLD5", "AMLD6", "Art. 8-11"],
    },
    {
        "template_id": "step2-kyc-cdd-policy",
        "name": "Politique KYC / CDD",
        "category": "AML/CFT",
        "institution_types": ["pi", "emi"],
        "applicable_regulations": ["AMLD5", "AMLD6", "Art. 13-14"],
    },
    {
        "template_id": "step2-edd-policy",
        "name": "Politique EDD",
        "category": "AML/CFT",
        "institution_types": ["pi", "emi"],
        "applicable_regulations": ["AMLD5", "AMLD6", "Art. 18-24"],
    },
    {
        "template_id": "step2-sanctions-freeze-policy",
        "name": "Politique Gel des Avoirs / Sanctions",
        "category": "AML/CFT",
        "institution_types": ["pi", "emi", "vasp"],
        "applicable_regulations": ["EU 2580/2001"],
    },
    {
        "template_id": "step2-sar-policy",
        "name": "Politique Déclaration de Soupçon (SAR)",
        "category": "AML/CFT",
        "institution_types": ["pi", "emi"],
        "applicable_regulations": ["AMLD5", "AMLD6", "Art. 33-35"],
    },
    {
        "template_id": "step2-safeguarding-policy",
        "name": "Politique Sauvegarde des Fonds",
        "category": "EMI",
        "institution_types": ["pi", "emi"],
        "applicable_regulations": ["PSD2 Art. 10", "DME2 Art. 7"],
    },
    {
        "template_id": "step2-payment-security-policy",
        "name": "Politique Sécurité des Opérations de Paiement",
        "category": "EMI",
        "institution_types": ["pi"],
        "applicable_regulations": ["PSD2 Art. 95-98", "RTS/SCA"],
    },
    {
        "template_id": "step2-operational-risk-policy",
        "name": "Politique Risques Opérationnels",
        "category": "Governance",
        "institution_types": ["pi", "emi"],
        "applicable_regulations": ["PSD2 Art. 5", "DME2 Art. 3"],
    },
    {
        "template_id": "step2-governance-policy",
        "name": "Politique Gouvernance et Contrôle Interne",
        "category": "Governance",
        "institution_types": ["pi", "emi"],
        "applicable_regulations": ["PSD2", "DME2", "AMLD"],
    },
    {
        "template_id": "step2-complaints-policy",
        "name": "Politique Gestion des Réclamations",
        "category": "EMI",
        "institution_types": ["pi", "emi"],
        "applicable_regulations": ["PSD2 Art. 101"],
    },
    {
        "template_id": "step2-gdpr-policy",
        "name": "Politique Protection des Données (RGPD)",
        "category": "GDPR",
        "institution_types": ["pi", "emi", "vasp"],
        "applicable_regulations": ["GDPR"],
    },
    {
        "template_id": "step2-outsourcing-policy",
        "name": "Politique Sous-traitance / Outsourcing",
        "category": "Governance",
        "institution_types": ["pi", "emi"],
        "applicable_regulations": ["EBA GL/2019/02"],
    },
    {
        "template_id": "step2-bcp-policy",
        "name": "Politique Continuité d'Activité (PCA/BCP)",
        "category": "Governance",
        "institution_types": ["pi", "emi"],
        "applicable_regulations": ["PSD2", "DORA"],
    },
    {
        "template_id": "step2-dora-security-policy",
        "name": "Politique Sécurité SI (DORA)",
        "category": "Governance",
        "institution_types": ["pi", "emi"],
        "applicable_regulations": ["DORA 2022/2554"],
    },
    {
        "template_id": "step2-mica-policy",
        "name": "Politique MiCA / Crypto Assets",
        "category": "CASP",
        "institution_types": ["vasp"],
        "applicable_regulations": ["MiCA 2023/1114"],
    },
    {
        "template_id": "step2-travel-rule-policy",
        "name": "Politique Travel Rule",
        "category": "CASP",
        "institution_types": ["vasp"],
        "applicable_regulations": ["TFR 2023/1113"],
    },
]


def _template_content(title: str, regulations: List[str]) -> str:
    joined_regs = ", ".join(regulations)
    return (
        f"# {title}\n\n"
        "## Objectif\n"
        "Définir le cadre de conformité opérationnel.\n\n"
        "## Périmètre\n"
        "Applicable aux équipes conformité, risque et opérations.\n\n"
        "## Base réglementaire\n"
        f"{joined_regs}\n\n"
        "## Contrôles\n"
        "1. Contrôle préventif\n"
        "2. Contrôle détectif\n"
        "3. Escalade et remédiation\n"
    )


def seed_step2_policy_templates(db: Optional[Session] = None) -> dict:
    owns_session = db is None
    if db is None:
        db = SessionLocal()

    created = 0
    updated = 0

    try:
        for spec in STEP2_POLICY_TEMPLATES:
            template_id = str(spec["template_id"])
            existing = (
                db.query(PolicyTemplate).filter(PolicyTemplate.template_id == template_id).first()
            )
            payload = {
                "name": str(spec["name"]),
                "category": str(spec["category"]),
                "version": "1.0",
                "owner": "Compliance",
                "review_frequency_months": 12,
                "regulatory_basis": list(spec["applicable_regulations"]),
                "institution_types": list(spec["institution_types"]),
                "applicable_regulations": list(spec["applicable_regulations"]),
                "content": _template_content(
                    title=str(spec["name"]),
                    regulations=list(spec["applicable_regulations"]),
                ),
                "is_active": True,
            }

            if existing:
                for key, value in payload.items():
                    setattr(existing, key, value)
                existing.updated_at = utc_now()
                updated += 1
            else:
                db.add(
                    PolicyTemplate(
                        template_id=template_id,
                        created_at=utc_now(),
                        updated_at=utc_now(),
                        **payload,
                    )
                )
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
