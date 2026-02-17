#!/usr/bin/env python3
"""
Fix script for common pipeline issues.

Usage:
    python scripts/fix_pipeline.py --all              # Run all fixes
    python scripts/fix_pipeline.py --ingest          # Run ingestion
    python scripts/fix_pipeline.py --analyze         # Analyze unanalyzed docs
    python scripts/fix_pipeline.py --rag             # Re-index RAG
    python scripts/fix_pipeline.py --templates       # Create default templates
    python scripts/fix_pipeline.py --retry-failed    # Retry failed items
"""

import argparse
import sys
import os

# Add src to path (works when run from api/ or api/src/)
script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, "..", "src")
if os.path.exists(src_dir):
    sys.path.insert(0, os.path.abspath(src_dir))
else:
    sys.path.insert(0, os.path.abspath(os.path.join(script_dir, "..")))


def run_ingestion():
    """Run manual ingestion for all sources."""
    print("🔄 Running ingestion...")
    from src.database import SessionLocal
    from src.ingestion.manager import IngestionManager

    db = SessionLocal()
    try:
        mgr = IngestionManager(db)
        reports = mgr.run_manual_ingestion(send_alerts=False)
        for report in reports:
            print(
                f"  {report.source_name}: {report.status} - "
                f"{report.items_new} new, {report.items_updated} updated, "
                f"{report.items_skipped} skipped"
            )
        print("✅ Ingestion complete")
    finally:
        db.close()


def analyze_documents():
    """Analyze documents that haven't been analyzed yet."""
    print("🔄 Analyzing documents...")
    from src.database import SessionLocal
    from src.models import LegalDocument
    from src.ai.analyzer import analyze_document
    from src.services.obligation_service import seed_obligations_for_doc

    db = SessionLocal()
    try:
        # Find documents with text but no analysis
        docs = (
            db.query(LegalDocument)
            .filter(LegalDocument.analyzed_at.is_(None))
            .filter(LegalDocument.full_text.isnot(None))
            .all()
        )

        if not docs:
            print("  No documents to analyze")
            return

        print(f"  Found {len(docs)} documents to analyze")

        for doc in docs:
            print(f"  Analyzing {doc.celex}...", end=" ")
            try:
                article_breakdown = None
                if isinstance(doc.article_breakdown, dict):
                    article_breakdown = doc.article_breakdown.get("articles")
                elif isinstance(doc.article_breakdown, list):
                    article_breakdown = doc.article_breakdown

                result = analyze_document(
                    {
                        "celex": doc.celex,
                        "title": doc.title,
                        "publication_date": doc.publication_date,
                        "full_text": doc.full_text,
                        "article_breakdown": article_breakdown,
                    }
                )

                doc.compliance_domain = result.get("compliance_domain")
                doc.risk_level = result.get("risk_level")
                doc.obligations_json = result.get("obligations_json")
                doc.implementation_deadline = result.get("implementation_deadline")
                doc.ai_summary = result.get("ai_summary")
                doc.analyzed_at = result.get("analyzed_at")

                db.commit()

                # Seed obligations
                count = seed_obligations_for_doc(db, doc)
                print(f"✓ ({count} obligations)")

            except Exception as e:
                print(f"✗ ({e})")
                db.rollback()

        print("✅ Analysis complete")
    finally:
        db.close()


def index_rag():
    """Re-index all documents into RAG."""
    print("🔄 Indexing RAG...")
    from src.database import SessionLocal
    from src.ai.rag_indexer import RAGIndexer

    db = SessionLocal()
    try:
        indexer = RAGIndexer(db)
        total = indexer.index_all_documents()
        print(f"✅ Indexed {total} chunks")
    finally:
        db.close()


def create_default_templates():
    """Create default policy templates if none exist."""
    print("🔄 Creating default policy templates...")
    from src.database import SessionLocal
    from src.models.compliance_workflow import PolicyTemplate

    db = SessionLocal()
    try:
        # Check if templates exist
        existing = db.query(PolicyTemplate).first()
        if existing:
            print("  Templates already exist, skipping")
            return

        default_templates = [
            {
                "template_id": "aml-cft-policy-master",
                "name": "AML/CFT Policy",
                "category": "aml/cft",
                "version": "1.0",
                "regulatory_basis": ["AMLD5", "AMLD6", "FATF"],
                "content": "# AML/CFT Policy\n\n## 1. Purpose\nThis policy establishes requirements for anti-money laundering and counter-terrorist financing compliance.\n\n## 2. Scope\nThis policy applies to all employees, customers, and transactions.\n\n## 3. Customer Due Diligence\n[To be populated based on regulatory obligations]\n\n## 4. Transaction Monitoring\n[To be populated based on regulatory obligations]\n\n## 5. Record Keeping\n[To be populated based on regulatory obligations]",
            },
            {
                "template_id": "kyc-policy-master",
                "name": "KYC Policy",
                "category": "kyc",
                "version": "1.0",
                "regulatory_basis": ["AMLD5", "AMLD6"],
                "content": "# KYC Policy\n\n## 1. Purpose\nThis policy establishes Know Your Customer requirements.\n\n## 2. Customer Identification\n[To be populated based on regulatory obligations]\n\n## 3. Risk Assessment\n[To be populated based on regulatory obligations]",
            },
            {
                "template_id": "sanctions-policy-master",
                "name": "Sanctions Policy",
                "category": "sanctions",
                "version": "1.0",
                "regulatory_basis": ["EU Sanctions", "OFAC"],
                "content": "# Sanctions Policy\n\n## 1. Purpose\nThis policy establishes requirements for sanctions compliance.\n\n## 2. Screening Requirements\n[To be populated based on regulatory obligations]\n\n## 3. Reporting Obligations\n[To be populated based on regulatory obligations]",
            },
            {
                "template_id": "gdpr-policy-master",
                "name": "Data Protection Policy",
                "category": "gdpr",
                "version": "1.0",
                "regulatory_basis": ["GDPR"],
                "content": "# Data Protection Policy\n\n## 1. Purpose\nThis policy establishes GDPR compliance requirements.\n\n## 2. Data Subject Rights\n[To be populated based on regulatory obligations]\n\n## 3. Data Breach Response\n[To be populated based on regulatory obligations]",
            },
        ]

        for tmpl_data in default_templates:
            template = PolicyTemplate(**tmpl_data, is_active=True)
            db.add(template)

        db.commit()
        print(f"✅ Created {len(default_templates)} default templates")

        # Create master policies
        print("  Creating master policies...")
        from src.services.policy_library import ensure_master_policies

        stats = ensure_master_policies(db)
        print(f"✅ Master policies: {stats}")

    finally:
        db.close()


def retry_failed():
    """Retry failed ingestion items."""
    print("🔄 Retrying failed items...")
    from src.database import SessionLocal
    from src.models.compliance_workflow import FailedIngestionItem
    from src.ingestion.manager import IngestionManager

    db = SessionLocal()
    try:
        # Get pending/retrying items
        items = (
            db.query(FailedIngestionItem)
            .filter(FailedIngestionItem.status.in_(["pending", "retrying"]))
            .all()
        )

        if not items:
            print("  No failed items to retry")
            return

        print(f"  Found {len(items)} items to retry")

        # For AI analysis failures, re-analyze
        analysis_items = [i for i in items if i.source_key == "ai_analysis"]
        if analysis_items:
            print(f"  Retrying {len(analysis_items)} AI analysis failures...")
            analyze_documents()

            # Mark as resolved
            for item in analysis_items:
                item.status = "resolved"
                item.resolved_at = datetime.utcnow()
            db.commit()

        print("✅ Retry complete")
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Fix pipeline issues")
    parser.add_argument("--all", action="store_true", help="Run all fixes")
    parser.add_argument("--ingest", action="store_true", help="Run ingestion")
    parser.add_argument("--analyze", action="store_true", help="Analyze documents")
    parser.add_argument("--rag", action="store_true", help="Index RAG")
    parser.add_argument("--templates", action="store_true", help="Create templates")
    parser.add_argument("--retry-failed", action="store_true", help="Retry failed items")

    args = parser.parse_args()

    # If no args, show help
    if not any(vars(args).values()):
        parser.print_help()
        return

    if args.all or args.ingest:
        run_ingestion()
        print()

    if args.all or args.analyze:
        analyze_documents()
        print()

    if args.all or args.rag:
        index_rag()
        print()

    if args.all or args.templates:
        create_default_templates()
        print()

    if args.all or args.retry_failed:
        retry_failed()
        print()

    print("✅ All fixes complete!")


if __name__ == "__main__":
    from datetime import datetime

    main()
