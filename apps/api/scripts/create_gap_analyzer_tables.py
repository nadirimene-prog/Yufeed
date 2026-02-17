#!/usr/bin/env python3
"""
Database Migration: Compliance Gap Analyzer
Tables for tracking policy-obligation mappings and coverage metrics
"""

import sys
from pathlib import Path
from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def get_database_url():
    possible_dbs = ["./compliance.db", "./src/compliance.db"]
    for db_path in possible_dbs:
        if os.path.exists(db_path):
            return f"sqlite:///{db_path}"
    return "sqlite:///./compliance.db"


import os

DATABASE_URL = get_database_url()
engine = create_engine(DATABASE_URL)


def run_migration():
    print("\n" + "=" * 70)
    print("COMPLIANCE GAP ANALYZER - DATABASE MIGRATION")
    print("=" * 70)
    print(f"Database: {DATABASE_URL}")

    with engine.connect() as conn:
        # 1. Create obligation_policy_mappings table
        print("\n1. Creating obligation_policy_mappings table...")
        try:
            conn.execute(
                text(
                    """
                CREATE TABLE IF NOT EXISTS obligation_policy_mappings (
                    id INTEGER PRIMARY KEY,
                    obligation_id INTEGER NOT NULL,
                    policy_id INTEGER NOT NULL,
                    mapping_type VARCHAR(50) DEFAULT 'direct',
                    mapping_confidence FLOAT DEFAULT 1.0,
                    mapped_by VARCHAR(50) DEFAULT 'manual',
                    mapped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    review_status VARCHAR(20) DEFAULT 'pending',
                    reviewed_by INTEGER,
                    reviewed_at TIMESTAMP,
                    notes TEXT,
                    UNIQUE(obligation_id, policy_id)
                )
            """
                )
            )
            print("   ✅ obligation_policy_mappings created")
        except Exception as e:
            print(f"   ⚠️  {e}")

        # 2. Create coverage_metrics table
        print("\n2. Creating coverage_metrics table...")
        try:
            conn.execute(
                text(
                    """
                CREATE TABLE IF NOT EXISTS coverage_metrics (
                    id INTEGER PRIMARY KEY,
                    metric_type VARCHAR(50) NOT NULL,
                    category VARCHAR(100),
                    total_count INTEGER NOT NULL,
                    covered_count INTEGER NOT NULL,
                    coverage_percentage FLOAT NOT NULL,
                    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    details_json TEXT
                )
            """
                )
            )
            print("   ✅ coverage_metrics created")
        except Exception as e:
            print(f"   ⚠️  {e}")

        # 3. Create gap_analysis_results table
        print("\n3. Creating gap_analysis_results table...")
        try:
            conn.execute(
                text(
                    """
                CREATE TABLE IF NOT EXISTS gap_analysis_results (
                    id INTEGER PRIMARY KEY,
                    analysis_id VARCHAR(64) NOT NULL UNIQUE,
                    obligation_id INTEGER NOT NULL,
                    gap_type VARCHAR(50) NOT NULL,
                    severity VARCHAR(20) NOT NULL,
                    description TEXT NOT NULL,
                    suggested_policy_template_id VARCHAR(100),
                    suggested_actions TEXT,
                    ai_recommendation TEXT,
                    status VARCHAR(20) DEFAULT 'open',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    resolved_at TIMESTAMP,
                    resolved_by INTEGER
                )
            """
                )
            )
            print("   ✅ gap_analysis_results created")
        except Exception as e:
            print(f"   ⚠️  {e}")

        # 4. Create policy_coverage_rules table
        print("\n4. Creating policy_coverage_rules table...")
        try:
            conn.execute(
                text(
                    """
                CREATE TABLE IF NOT EXISTS policy_coverage_rules (
                    id INTEGER PRIMARY KEY,
                    policy_id INTEGER NOT NULL,
                    rule_type VARCHAR(50) NOT NULL,
                    rule_pattern TEXT NOT NULL,
                    coverage_scope TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
                )
            )
            print("   ✅ policy_coverage_rules created")
        except Exception as e:
            print(f"   ⚠️  {e}")

        # 5. Add columns to regulatory_obligations
        print("\n5. Adding gap analysis columns to regulatory_obligations...")
        columns = [
            ("coverage_status", "VARCHAR(20) DEFAULT 'uncovered'"),
            ("auto_categorized", "BOOLEAN DEFAULT 0"),
            ("category", "VARCHAR(100)"),
            ("gap_severity", "VARCHAR(20)"),
        ]

        for col_name, col_type in columns:
            try:
                conn.execute(
                    text(
                        f"""
                    ALTER TABLE regulatory_obligations
                    ADD COLUMN {col_name} {col_type}
                """
                    )
                )
                print(f"   ✅ Added {col_name}")
            except Exception as e:
                print(f"   ⚠️  {col_name}: {e}")

        # 6. Add columns to policy_documents
        print("\n6. Adding coverage columns to policy_documents...")
        policy_columns = [
            ("coverage_score", "FLOAT"),
            ("last_coverage_analysis", "TIMESTAMP"),
            ("obligations_covered_count", "INTEGER DEFAULT 0"),
        ]

        for col_name, col_type in policy_columns:
            try:
                conn.execute(
                    text(
                        f"""
                    ALTER TABLE policy_documents
                    ADD COLUMN {col_name} {col_type}
                """
                    )
                )
                print(f"   ✅ Added {col_name}")
            except Exception as e:
                print(f"   ⚠️  {col_name}: {e}")

        # 7. Create indexes
        print("\n7. Creating indexes...")
        indexes = [
            ("idx_opm_obligation", "obligation_policy_mappings", "obligation_id"),
            ("idx_opm_policy", "obligation_policy_mappings", "policy_id"),
            ("idx_gap_obligation", "gap_analysis_results", "obligation_id"),
            ("idx_gap_status", "gap_analysis_results", "status"),
            ("idx_metrics_type", "coverage_metrics", "metric_type"),
            ("idx_obl_coverage", "regulatory_obligations", "coverage_status"),
            ("idx_obl_category", "regulatory_obligations", "category"),
        ]

        for idx_name, table, column in indexes:
            try:
                conn.execute(
                    text(
                        f"""
                    CREATE INDEX IF NOT EXISTS {idx_name} ON {table} ({column})
                """
                    )
                )
                print(f"   ✅ {idx_name}")
            except Exception as e:
                print(f"   ⚠️  {idx_name}: {e}")

        conn.commit()

    print("\n" + "=" * 70)
    print("MIGRATION COMPLETE")
    print("=" * 70)
    print("\nNext steps:")
    print("  1. Build gap_analyzer_service.py")
    print("  2. Create coverage scoring algorithms")
    print("  3. Build gap analysis API endpoints")


if __name__ == "__main__":
    run_migration()
