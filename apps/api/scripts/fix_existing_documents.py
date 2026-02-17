#!/usr/bin/env python3
"""
Fix Existing Documents
- Updates wrong CELEX numbers
- Re-extracts content for all documents
- Reports on success rates
"""

import sys
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

import os

# Find database with tables
possible_dbs = [
    "./compliance.db",
    "./src/compliance.db",
    "./yufeed.db",
]
DATABASE_URL = None
for db_path in possible_dbs:
    if os.path.exists(db_path):
        import sqlite3

        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='legal_documents'"
            )
            if cursor.fetchone():
                DATABASE_URL = f"sqlite:///{db_path}"
                print(f"Using database with legal_documents table: {db_path}")
                break
            conn.close()
        except:
            pass

if not DATABASE_URL:
    DATABASE_URL = "sqlite:///./compliance.db"
    print(f"Using default database: {DATABASE_URL}")
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

# Known CELEX corrections
KNOWN_CORRECTIONS = {
    # Current wrong CELEX -> Correct CELEX (reason)
    "32015D2366": ("32015L2366", "PSD2 is a Directive, not a Decision"),
}

# Check actual database to find any wrong CELEX
CELEX_CORRECTION_MAP = {}


def get_document_stats(db):
    """Get current document statistics."""
    stats = db.execute(
        text(
            """
        SELECT
            COUNT(*) as total,
            COUNT(full_text) as with_content,
            COUNT(CASE WHEN full_text IS NOT NULL AND LENGTH(full_text) > 1000 THEN 1 END) as with_good_content,
            AVG(LENGTH(full_text)) as avg_content_length
        FROM legal_documents
    """
        )
    ).fetchone()

    return {
        "total": stats[0],
        "with_content": stats[1],
        "with_good_content": stats[2],
        "content_rate": (stats[1] / stats[0] * 100) if stats[0] > 0 else 0,
        "avg_length": int(stats[3] or 0),
    }


def identify_problematic_celex(db):
    """Find documents that might have wrong CELEX."""
    results = []

    docs = db.execute(
        text(
            """
        SELECT id, celex, title, type
        FROM legal_documents
        ORDER BY celex
    """
        )
    ).fetchall()

    for doc_id, celex, title, doc_type in docs:
        issues = []

        # Check against known wrong CELEX
        if celex in KNOWN_CORRECTIONS:
            correct_celex, reason = KNOWN_CORRECTIONS[celex]
            issues.append(f"Known wrong CELEX: {reason}")

        # Check title vs document type (position 5 for sector 3)
        title_upper = (title or "").upper()

        if celex and len(celex) >= 6:
            doc_type_pos = 5 if celex[0] == "3" else 3 if celex[0] in ["1", "2"] else 5
            if doc_type_pos < len(celex):
                celex_type = celex[doc_type_pos]

                if "DIRECTIVE" in title_upper and celex_type not in ["L", "D"]:
                    issues.append(f"Title says Directive but CELEX type is {celex_type}")

                if "REGULATION" in title_upper and celex_type != "R":
                    issues.append(f"Title says Regulation but CELEX type is {celex_type}")

        if issues:
            results.append({"id": doc_id, "celex": celex, "title": title, "issues": issues})

    return results


def fix_celexs(db):
    """Apply CELEX corrections."""
    fixed = []

    for wrong_celex, (correct_celex, reason) in KNOWN_CORRECTIONS.items():
        # Check if document exists
        doc = db.execute(
            text(
                """
            SELECT id, title FROM legal_documents WHERE celex = :celex
        """
            ),
            {"celex": wrong_celex},
        ).fetchone()

        if doc:
            # Check if correct CELEX already exists
            existing = db.execute(
                text(
                    """
                SELECT id FROM legal_documents WHERE celex = :celex
            """
                ),
                {"celex": correct_celex},
            ).fetchone()

            if existing:
                print(f"⚠️ Both {wrong_celex} and {correct_celex} exist - manual review needed")
            else:
                # Update the document
                db.execute(
                    text(
                        """
                    UPDATE legal_documents
                    SET celex = :correct_celex,
                        full_text = NULL,  -- Force re-extraction
                        article_breakdown = NULL
                    WHERE celex = :wrong_celex
                """
                    ),
                    {"correct_celex": correct_celex, "wrong_celex": wrong_celex},
                )

                fixed.append({"old": wrong_celex, "new": correct_celex, "reason": reason})
                print(f"✅ Fixed: {wrong_celex} → {correct_celex}")

    return fixed


def plan_content_reextraction(db):
    """Plan batch re-extraction of content."""
    docs = db.execute(
        text(
            """
        SELECT id, celex, title
        FROM legal_documents
        WHERE full_text IS NULL OR LENGTH(full_text) < 1000
        ORDER BY celex
    """
        )
    ).fetchall()

    return [{"id": d[0], "celex": d[1], "title": d[2]} for d in docs]


def main():
    print("\n" + "=" * 70)
    print("FIX EXISTING DOCUMENTS")
    print("=" * 70)

    db = Session()

    try:
        # Step 1: Get current stats
        print("\n📊 CURRENT STATISTICS")
        stats = get_document_stats(db)
        print(f"   Total documents: {stats['total']}")
        print(f"   With content: {stats['with_content']} ({stats['content_rate']:.1f}%)")
        print(f"   With good content: {stats['with_good_content']}")
        print(f"   Average content length: {stats['avg_length']:,} chars")

        # Step 2: Identify problematic CELEX
        print("\n🔍 CHECKING CELEX ACCURACY")
        problems = identify_problematic_celex(db)
        print(f"   Found {len(problems)} documents with potential CELEX issues")

        for p in problems[:5]:  # Show first 5
            print(f"   - {p['celex']}: {p['title'][:40]}...")
            for issue in p["issues"]:
                print(f"     ⚠️ {issue}")

        if len(problems) > 5:
            print(f"   ... and {len(problems) - 5} more")

        # Step 3: Fix known wrong CELEX
        print("\n🔧 FIXING KNOWN WRONG CELEX")
        fixed = fix_celexs(db)
        print(f"   Fixed {len(fixed)} documents")

        # Step 4: Plan content re-extraction
        print("\n📋 RE-EXTRACTION PLAN")
        to_reextract = plan_content_reextraction(db)
        print(f"   {len(to_reextract)} documents need content re-extraction")

        # Step 5: Commit changes
        db.commit()

        # Save report
        report = {
            "timestamp": datetime.now().isoformat(),
            "before_stats": stats,
            "celex_problems_found": len(problems),
            "celex_fixed": fixed,
            "documents_to_reextract": len(to_reextract),
            "reextraction_list": to_reextract[:50],  # First 50
        }

        report_path = Path("fix_report.json")
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)

        print(f"\n💾 Report saved to: {report_path}")

        print("\n" + "=" * 70)
        print("NEXT STEPS:")
        print("=" * 70)
        print("1. Run content extractor v2 on documents without content")
        print("2. Re-index RAG after content extraction")
        print("3. Re-analyze documents with new content")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
