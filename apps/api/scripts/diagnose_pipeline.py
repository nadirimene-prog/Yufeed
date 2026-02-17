#!/usr/bin/env python3
"""
Diagnostic script to check the EU legal data pipeline status.

Run this to identify where the flow is broken:
    cd apps/api/src && python ../scripts/diagnose_pipeline.py
"""

import sys
import os

# Add src to path (works when run from api/ or api/src/)
script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, "..", "src")
if os.path.exists(src_dir):
    sys.path.insert(0, os.path.abspath(src_dir))
else:
    # Already in src
    sys.path.insert(0, os.path.abspath(os.path.join(script_dir, "..")))

from sqlalchemy import func, text

# from tabulate import tabulate  # Optional dependency


def main():
    print("=" * 80)
    print("Yufeed Pipeline Diagnostic Tool")
    print("=" * 80)
    print()

    # 1. Check environment configuration
    print("1. ENVIRONMENT CONFIGURATION")
    print("-" * 40)
    from src.config import settings

    checks = [
        ("ANTHROPIC_API_KEY", bool(settings.ANTHROPIC_API_KEY)),
        ("OPENAI_API_KEY", bool(settings.OPENAI_API_KEY)),
        ("DATABASE_URL", bool(settings.DATABASE_URL)),
        ("REDIS_URL", bool(settings.REDIS_URL)),
        ("OPENSEARCH_URL", bool(settings.OPENSEARCH_URL)),
        ("RAG_INDEX_ENABLED", settings.RAG_INDEX_ENABLED),
        ("EURLEX_LANGUAGES", settings.EURLEX_LANGUAGES),
    ]

    for name, value in checks:
        status = "✅" if value else "❌"
        display_value = "***" if "KEY" in name and value else value
        print(f"  {status} {name}: {display_value}")
    print()

    # 2. Database connectivity
    print("2. DATABASE CONNECTIVITY")
    print("-" * 40)
    try:
        from src.database import SessionLocal, engine

        db = SessionLocal()
        result = db.execute(text("SELECT 1")).scalar()
        print(f"  ✅ Database connection: OK")

        # Check tables exist
        from sqlalchemy import inspect

        inspector = inspect(engine)
        tables = inspector.get_table_names()
        required_tables = [
            "legal_documents",
            "regulatory_obligations",
            "legal_chunks",
            "policy_templates",
            "policy_documents",
        ]
        missing = [t for t in required_tables if t not in tables]
        if missing:
            print(f"  ❌ Missing tables: {', '.join(missing)}")
        else:
            print(f"  ✅ All required tables present")
    except Exception as e:
        print(f"  ❌ Database error: {e}")
        return
    print()

    # 3. Document ingestion status
    print("3. DOCUMENT INGESTION STATUS")
    print("-" * 40)
    try:
        from src.models import LegalDocument, IngestionRun, RegulatorySource

        # Total documents
        total_docs = db.query(func.count(LegalDocument.id)).scalar()
        print(f"  Total LegalDocuments: {total_docs}")

        # Documents by source
        sources = (
            db.query(LegalDocument.source_system, func.count(LegalDocument.id))
            .group_by(LegalDocument.source_system)
            .all()
        )
        for source, count in sources:
            print(f"    - {source or 'unknown'}: {count}")

        # Recent ingestion runs
        recent_runs = db.query(IngestionRun).order_by(IngestionRun.started_at.desc()).limit(3).all()
        if recent_runs:
            print(f"  Recent ingestion runs:")
            for run in recent_runs:
                print(
                    f"    - {run.started_at.date()}: {run.status}, "
                    f"{run.items_new} new, {run.items_updated} updated"
                )
        else:
            print(f"  ⚠️  No ingestion runs found")

        # Regulatory sources
        sources = db.query(RegulatorySource).all()
        print(f"  Configured sources: {len(sources)}")
        for src in sources:
            last = src.last_ingested_at.date() if src.last_ingested_at else "never"
            print(f"    - {src.source_key}: last={last}, active={src.is_active}")

    except Exception as e:
        print(f"  ❌ Error: {e}")
    print()

    # 4. Document analysis status
    print("4. DOCUMENT ANALYSIS STATUS")
    print("-" * 40)
    try:
        from src.models import LegalDocument

        # Analysis stats
        stats = (
            db.query(
                func.count(LegalDocument.id).label("total"),
                func.count(LegalDocument.analyzed_at).label("analyzed"),
                func.count(LegalDocument.full_text).label("has_text"),
            )
            .select_from(LegalDocument)
            .first()
        )

        print(f"  Total documents: {stats.total}")
        print(
            f"  Analyzed (AI): {stats.analyzed} ({stats.analyzed / stats.total * 100:.1f}% if stats.total else 0)"
        )
        print(
            f"  With full_text: {stats.has_text} ({stats.has_text / stats.total * 100:.1f}% if stats.total else 0)"
        )

        # Documents without analysis
        unanalyzed = (
            db.query(LegalDocument.celex, LegalDocument.title)
            .filter(LegalDocument.analyzed_at.is_(None))
            .filter(LegalDocument.full_text.isnot(None))
            .limit(5)
            .all()
        )
        if unanalyzed:
            print(f"  ⚠️  Documents ready for analysis (have text, not analyzed):")
            for celex, title in unanalyzed:
                print(f"    - {celex}: {title[:60] if title else 'No title'}...")

        # Check AI provider
        from src.ai.analyzer import _anthropic_enabled, _openai_enabled

        anthropic_ok = _anthropic_enabled()
        openai_ok = _openai_enabled()
        if anthropic_ok or openai_ok:
            print(f"  ✅ AI provider available: {'Anthropic' if anthropic_ok else 'OpenAI'}")
        else:
            print(f"  ❌ No AI provider available - set ANTHROPIC_API_KEY or OPENAI_API_KEY")

    except Exception as e:
        print(f"  ❌ Error: {e}")
    print()

    # 5. Obligation status
    print("5. OBLIGATION WORKFLOW STATUS")
    print("-" * 40)
    try:
        from src.models.compliance_workflow import RegulatoryObligation, PolicyTemplate

        # Obligations by status
        status_counts = (
            db.query(
                RegulatoryObligation.status,
                func.count(RegulatoryObligation.id),
            )
            .group_by(RegulatoryObligation.status)
            .all()
        )

        if status_counts:
            print(f"  Obligations by status:")
            for status, count in sorted(status_counts):
                print(f"    - {status}: {count}")
        else:
            print(f"  ⚠️  No obligations found")

        # Obligations without documents
        orphaned = (
            db.query(func.count(RegulatoryObligation.id))
            .filter(RegulatoryObligation.doc_id.notin_(db.query(LegalDocument.id)))
            .scalar()
        )
        if orphaned:
            print(f"  ❌ Orphaned obligations (no linked document): {orphaned}")

        # Approved but no policy
        approved_no_policy = (
            db.query(func.count(RegulatoryObligation.id))
            .filter(RegulatoryObligation.status == "approved")
            .filter(RegulatoryObligation.linked_policy_id.is_(None))
            .scalar()
        )
        if approved_no_policy:
            print(f"  ⚠️  Approved obligations without policy: {approved_no_policy}")

        # Policy templates
        template_count = db.query(func.count(PolicyTemplate.id)).scalar()
        active_templates = (
            db.query(func.count(PolicyTemplate.id))
            .filter(PolicyTemplate.is_active == True)
            .scalar()
        )
        print(f"  Policy templates: {active_templates} active / {template_count} total")

        if active_templates == 0:
            print(f"  ❌ No active policy templates - obligations cannot be approved!")

    except Exception as e:
        print(f"  ❌ Error: {e}")
    print()

    # 6. RAG indexing status
    print("6. RAG INDEXING STATUS")
    print("-" * 40)
    try:
        from src.models.rag_models import LegalChunk

        chunk_stats = db.query(
            func.count(LegalChunk.id).label("total_chunks"),
            func.count(func.distinct(LegalChunk.doc_id)).label("docs_indexed"),
        ).first()

        print(f"  Total chunks: {chunk_stats.total_chunks}")
        print(f"  Documents indexed: {chunk_stats.docs_indexed}")

        # Documents without chunks
        if stats.total > 0:
            not_indexed = stats.total - chunk_stats.docs_indexed
            if not_indexed > 0:
                print(f"  ⚠️  Documents not in RAG: {not_indexed}")

        # Check OpenSearch
        try:
            from src.search import get_opensearch_client

            client = get_opensearch_client()
            info = client.info()
            print(f"  ✅ OpenSearch connected: {info.get('version', {}).get('number', 'unknown')}")

            # Index stats
            from src.config import settings

            index_name = settings.RAG_INDEX_NAME
            try:
                index_stats = client.count(index=index_name)
                print(f"  OpenSearch index '{index_name}': {index_stats['count']} docs")
            except Exception as e:
                print(f"  ⚠️  OpenSearch index issue: {e}")
        except Exception as e:
            print(f"  ❌ OpenSearch connection failed: {e}")

    except Exception as e:
        print(f"  ❌ Error: {e}")
    print()

    # 7. Failed items
    print("7. FAILED/DLQ ITEMS")
    print("-" * 40)
    try:
        from src.models.compliance_workflow import FailedIngestionItem

        failed_counts = (
            db.query(
                FailedIngestionItem.status,
                func.count(FailedIngestionItem.id),
            )
            .group_by(FailedIngestionItem.status)
            .all()
        )

        if failed_counts:
            print(f"  Failed ingestion items:")
            for status, count in sorted(failed_counts):
                print(f"    - {status}: {count}")

            # Recent failures
            recent_failures = (
                db.query(FailedIngestionItem)
                .order_by(FailedIngestionItem.created_at.desc())
                .limit(3)
                .all()
            )
            print(f"  Recent failures:")
            for item in recent_failures:
                print(
                    f"    - {item.celex or 'N/A'}: {item.source_key} - {item.error_message[:50]}..."
                )
        else:
            print(f"  ✅ No failed items in DLQ")

    except Exception as e:
        print(f"  ❌ Error: {e}")
    print()

    # 8. Summary and recommendations
    print("8. SUMMARY & RECOMMENDATIONS")
    print("-" * 40)

    issues = []
    recommendations = []

    if stats.total == 0:
        issues.append("No documents in database")
        recommendations.append("Run ingestion: python scripts/ingest_eurlex.py")

    if stats.total > 0 and stats.analyzed == 0:
        issues.append("Documents not analyzed")
        if not (anthropic_ok or openai_ok):
            recommendations.append("Set ANTHROPIC_API_KEY or OPENAI_API_KEY")
        else:
            recommendations.append("Run: python scripts/reanalyze_documents.py")

    if active_templates == 0:
        issues.append("No policy templates")
        recommendations.append("Create policy templates in database")

    if chunk_stats.total_chunks == 0 and stats.total > 0:
        issues.append("RAG not indexed")
        recommendations.append("Run: python -c 'from src.ai.rag_indexer import RAGIndexer; ...'")

    if not issues:
        print("  ✅ Pipeline appears to be working!")
    else:
        print(f"  Found {len(issues)} issue(s):")
        for issue in issues:
            print(f"    - {issue}")
        print()
        print("  Recommendations:")
        for rec in recommendations:
            print(f"    → {rec}")

    print()
    print("=" * 80)

    db.close()


if __name__ == "__main__":
    main()
