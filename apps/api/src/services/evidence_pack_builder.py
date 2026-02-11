"""Evidence Pack builder — deterministic, hashed, audit-proof snapshots.

Assembles a Case's full context (findings, decisions, audit timeline,
references), canonicalises it as JSON, and computes a SHA-256 integrity hash.
Optionally renders a basic PDF via ReportLab.
"""

import hashlib
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import func, or_, and_
from sqlalchemy.inspection import inspect as sa_inspect
from sqlalchemy.orm import Session

from src.audit.models import EventRecord, AuditLog
from src.audit.recorders import record_event
from src.models.case_decision import CaseDecision, CaseDecisionStatus
from src.models.evidence_pack import EvidencePack
from src.models.finding_models import Finding
from src.models.transaction_models import Alert, Case, Transaction
from src.utils.time import utc_now

logger = logging.getLogger(__name__)


def _model_to_dict(obj: Any) -> Dict[str, Any]:
    """Convert a SQLAlchemy model instance to a plain dict.

    Reuses the pattern from ``api/reports/evidence.py``.
    """
    data: Dict[str, Any] = {}
    for attr in sa_inspect(obj).mapper.column_attrs:
        key = attr.key
        value = getattr(obj, key)
        if isinstance(value, datetime):
            value = value.isoformat()
        elif isinstance(value, Decimal):
            value = float(value)
        data[key] = value
    if "metadata_json" in data:
        data["metadata"] = data.pop("metadata_json")
    return data


class EvidencePackBuilder:
    """Build deterministic, hashed evidence snapshots for cases."""

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_pack(
        self,
        case_id: int,
        tenant_id: str,
        created_by: str,
        pack_format: str = "json",
    ) -> EvidencePack:
        """Build snapshot, canonicalise, hash, and store as ``EvidencePack``."""

        case = self.db.query(Case).filter(Case.id == case_id, Case.tenant_id == tenant_id).first()
        if not case:
            raise ValueError("Case not found")

        snapshot = self.build_snapshot(case, tenant_id)

        # Inject placeholder for hash
        snapshot["integrity"] = {
            "content_hash": "",
            "source_data_cutoff": datetime.now(timezone.utc).isoformat(),
        }

        canonical = self.canonicalize(snapshot)
        integrity_hash = self.compute_hash(canonical)

        # Re-inject the real hash and re-canonicalize
        snapshot["integrity"]["content_hash"] = f"sha256:{integrity_hash}"
        canonical = self.canonicalize(snapshot)

        # Auto-increment version
        latest_version = (
            self.db.query(func.max(EvidencePack.version))
            .filter(EvidencePack.case_id == case_id, EvidencePack.tenant_id == tenant_id)
            .scalar()
        ) or 0

        pack_id = f"EPACK-{utc_now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"

        storage_ref: Optional[str] = None
        if pack_format == "pdf":
            storage_ref = self.generate_pdf(snapshot, pack_id)

        pack = EvidencePack(
            pack_id=pack_id,
            tenant_id=tenant_id,
            case_id=case_id,
            schema_version="v1",
            version=latest_version + 1,
            format=pack_format,
            snapshot_json=snapshot,
            integrity_hash=integrity_hash,
            storage_ref=storage_ref,
            created_by=created_by,
        )
        self.db.add(pack)
        self.db.flush()

        record_event(
            self.db,
            event_type="evidence_pack.created",
            entity_type="evidence_pack",
            entity_id=pack.pack_id,
            tenant_id=tenant_id,
            payload={
                "case_id": case.case_id,
                "version": pack.version,
                "format": pack_format,
                "integrity_hash": integrity_hash,
            },
        )
        logger.info(
            "Created evidence pack %s v%s for case %s (hash=%s)",
            pack.pack_id,
            pack.version,
            case.case_id,
            integrity_hash[:12],
        )
        return pack

    # ------------------------------------------------------------------
    # Snapshot builder
    # ------------------------------------------------------------------

    def build_snapshot(self, case: Case, tenant_id: str) -> Dict[str, Any]:
        """Assemble the full evidence snapshot for a case."""

        # --- Findings ---
        findings_data = [_model_to_dict(f) for f in (case.findings or [])]

        # --- Decision (latest approved) ---
        decision = (
            self.db.query(CaseDecision)
            .filter(
                CaseDecision.case_id == case.id,
                CaseDecision.tenant_id == tenant_id,
                CaseDecision.status == CaseDecisionStatus.approved.value,
            )
            .order_by(CaseDecision.version.desc())
            .first()
        )
        decision_data = _model_to_dict(decision) if decision else None

        # --- Alerts ---
        related_alert_ids = case.related_alert_ids or []
        alerts = (
            self.db.query(Alert).filter(Alert.id.in_(related_alert_ids)).all()
            if related_alert_ids
            else []
        )
        alerts_data = [_model_to_dict(a) for a in alerts]

        # --- Transactions ---
        related_tx_ids = case.related_transaction_ids or []
        transactions = (
            self.db.query(Transaction).filter(Transaction.id.in_(related_tx_ids)).all()
            if related_tx_ids
            else []
        )
        transactions_data = [_model_to_dict(t) for t in transactions]

        # --- Audit timeline (EventRecords) ---
        entity_ids = [case.case_id] + [str(f.get("id", "")) for f in findings_data]
        alert_entity_ids = [a.get("alert_id", "") for a in alerts_data]

        event_filters = [
            and_(EventRecord.entity_type == "case", EventRecord.entity_id == case.case_id),
        ]
        if entity_ids:
            event_filters.append(
                and_(
                    EventRecord.entity_type == "finding",
                    EventRecord.entity_id.in_(
                        [str(f.get("id", "")) for f in findings_data] or ["__none__"]
                    ),
                )
            )
        if alert_entity_ids:
            event_filters.append(
                and_(
                    EventRecord.entity_type == "alert",
                    EventRecord.entity_id.in_(alert_entity_ids or ["__none__"]),
                )
            )
        # Include case_decision events
        event_filters.append(
            and_(
                EventRecord.entity_type == "case_decision",
                EventRecord.entity_id.in_(
                    [str(d.id) for d in (getattr(case, "decisions", None) or [])] or ["__none__"]
                ),
            )
        )

        events = (
            self.db.query(EventRecord)
            .filter(
                EventRecord.tenant_id == tenant_id,
                or_(*event_filters),
            )
            .order_by(EventRecord.created_at.asc())
            .all()
        )
        timeline_data = [_model_to_dict(e) for e in events]

        # --- References (extracted from findings source_refs) ---
        references: Dict[str, List[Any]] = {
            "transactions": [],
            "alerts": [],
            "documents": [],
            "sanctions_lists": [],
        }
        for f in findings_data:
            refs = f.get("source_refs") or f.get("source_refs_json") or {}
            if isinstance(refs, dict):
                if "transaction_id" in refs:
                    references["transactions"].append(refs["transaction_id"])
                if "transaction_ids" in refs:
                    references["transactions"].extend(refs["transaction_ids"])
                if "alert_id" in refs:
                    references["alerts"].append(refs["alert_id"])
                if "doc_id" in refs:
                    references["documents"].append(refs["doc_id"])
                if "celex_id" in refs:
                    references["documents"].append(refs["celex_id"])
                if "list_sources" in refs:
                    references["sanctions_lists"].extend(refs["list_sources"])

        # Deduplicate references
        for key in references:
            references[key] = sorted(set(str(v) for v in references[key]))

        return {
            "schema_version": "v1",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "tenant_id": tenant_id,
            "case": _model_to_dict(case),
            "findings": sorted(findings_data, key=lambda x: x.get("id", 0)),
            "decision": decision_data,
            "audit_timeline": timeline_data,
            "references": references,
            "integrity": {},
        }

    # ------------------------------------------------------------------
    # Canonicalization / Hashing
    # ------------------------------------------------------------------

    @staticmethod
    def canonicalize(snapshot: Dict[str, Any]) -> str:
        """Deterministic JSON serialisation (sorted keys, no whitespace)."""
        return json.dumps(snapshot, sort_keys=True, separators=(",", ":"), default=str)

    @staticmethod
    def compute_hash(canonical_json: str) -> str:
        """SHA-256 of the canonical JSON bytes."""
        return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

    # ------------------------------------------------------------------
    # PDF generation (basic — via ReportLab)
    # ------------------------------------------------------------------

    def generate_pdf(self, snapshot: Dict[str, Any], pack_id: str) -> str:
        """Render a basic PDF from the snapshot and return the file path."""
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.lib.units import mm
            from reportlab.platypus import (
                SimpleDocTemplate,
                Paragraph,
                Spacer,
                Table,
                TableStyle,
            )
            from reportlab.lib import colors
        except ImportError:
            logger.warning("reportlab not installed — skipping PDF generation")
            return ""

        output_dir = os.path.join(os.getcwd(), "evidence_packs")
        os.makedirs(output_dir, exist_ok=True)
        filepath = os.path.join(output_dir, f"{pack_id}.pdf")

        doc = SimpleDocTemplate(filepath, pagesize=A4)
        styles = getSampleStyleSheet()
        elements: list = []

        # Title
        elements.append(Paragraph(f"Evidence Pack — {pack_id}", styles["Title"]))
        elements.append(Spacer(1, 6 * mm))

        # Case summary
        case_data = snapshot.get("case", {})
        elements.append(Paragraph("Case Summary", styles["Heading2"]))
        case_info = [
            ["Case ID", str(case_data.get("case_id", ""))],
            ["Status", str(case_data.get("status", ""))],
            ["Priority", str(case_data.get("priority", ""))],
            ["Title", str(case_data.get("title", ""))[:80]],
            ["Opened", str(case_data.get("opened_at", ""))],
            ["Closed", str(case_data.get("closed_at", "") or "—")],
            ["Outcome", str(case_data.get("outcome", "") or "—")],
        ]
        t = Table(case_info, colWidths=[100, 350])
        t.setStyle(
            TableStyle(
                [
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ]
            )
        )
        elements.append(t)
        elements.append(Spacer(1, 6 * mm))

        # Findings
        findings = snapshot.get("findings", [])
        if findings:
            elements.append(Paragraph(f"Findings ({len(findings)})", styles["Heading2"]))
            f_rows = [["ID", "Type", "Severity", "Status", "Title"]]
            for f in findings:
                f_rows.append(
                    [
                        str(f.get("id", "")),
                        str(f.get("finding_type", "")),
                        str(f.get("severity", "")),
                        str(f.get("status", "")),
                        str(f.get("title", ""))[:50],
                    ]
                )
            ft = Table(f_rows, colWidths=[40, 80, 60, 60, 210])
            ft.setStyle(
                TableStyle(
                    [
                        ("FONTSIZE", (0, 0), (-1, -1), 8),
                        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ]
                )
            )
            elements.append(ft)
            elements.append(Spacer(1, 6 * mm))

        # Decision
        decision = snapshot.get("decision")
        if decision:
            elements.append(Paragraph("Decision", styles["Heading2"]))
            d_info = [
                ["Disposition", str(decision.get("disposition", ""))],
                ["Status", str(decision.get("status", ""))],
                ["Rationale", str(decision.get("rationale", ""))[:200]],
                ["Created By", str(decision.get("created_by", ""))],
                ["Approver", str(decision.get("approver_id", "") or "—")],
                ["Approved At", str(decision.get("approved_at", "") or "—")],
            ]
            dt = Table(d_info, colWidths=[100, 350])
            dt.setStyle(
                TableStyle(
                    [
                        ("FONTSIZE", (0, 0), (-1, -1), 9),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ]
                )
            )
            elements.append(dt)
            elements.append(Spacer(1, 6 * mm))

        # Audit Timeline
        timeline = snapshot.get("audit_timeline", [])
        if timeline:
            elements.append(
                Paragraph(f"Audit Timeline ({len(timeline)} events)", styles["Heading2"])
            )
            tl_rows = [["Time", "Type", "Entity", "Entity ID"]]
            for evt in timeline[:50]:  # cap at 50 for PDF readability
                tl_rows.append(
                    [
                        str(evt.get("created_at", ""))[:19],
                        str(evt.get("event_type", "")),
                        str(evt.get("entity_type", "")),
                        str(evt.get("entity_id", ""))[:20],
                    ]
                )
            tlt = Table(tl_rows, colWidths=[110, 120, 80, 140])
            tlt.setStyle(
                TableStyle(
                    [
                        ("FONTSIZE", (0, 0), (-1, -1), 7),
                        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ]
                )
            )
            elements.append(tlt)
            elements.append(Spacer(1, 6 * mm))

        # Integrity
        integrity = snapshot.get("integrity", {})
        elements.append(Paragraph("Integrity", styles["Heading2"]))
        elements.append(
            Paragraph(f"Hash: {integrity.get('content_hash', 'N/A')}", styles["Normal"])
        )
        elements.append(
            Paragraph(f"Schema: {snapshot.get('schema_version', 'v1')}", styles["Normal"])
        )

        doc.build(elements)
        logger.info("Generated PDF at %s", filepath)
        return filepath
