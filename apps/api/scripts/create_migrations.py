#!/usr/bin/env python3
"""
Create database migrations for new features
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os


def get_database_url():
    possible_dbs = ["./compliance.db", "./src/compliance.db"]
    for db_path in possible_dbs:
        if os.path.exists(db_path):
            return f"sqlite:///{db_path}"
    return "sqlite:///./compliance.db"


DATABASE_URL = get_database_url()
engine = create_engine(DATABASE_URL)


def run_migrations():
    """Run all migrations."""
    print("\n" + "=" * 70)
    print("DATABASE MIGRATIONS")
    print("=" * 70)
    print(f"Database: {DATABASE_URL}")

    with engine.connect() as conn:
        # Migration 1: Add confidence columns to legal_documents
        print("\n1. Adding confidence columns to legal_documents...")
        try:
            conn.execute(
                text(
                    """
                ALTER TABLE legal_documents
                ADD COLUMN ai_confidence FLOAT
            """
                )
            )
            print("   ✅ ai_confidence added")
        except Exception as e:
            print(f"   ⚠️  ai_confidence: {e}")

        try:
            conn.execute(
                text(
                    """
                ALTER TABLE legal_documents
                ADD COLUMN analysis_quality VARCHAR(20)
            """
                )
            )
            print("   ✅ analysis_quality added")
        except Exception as e:
            print(f"   ⚠️  analysis_quality: {e}")

        # Migration 2: Create document_versions table
        print("\n2. Creating document_versions table...")
        try:
            conn.execute(
                text(
                    """
                CREATE TABLE IF NOT EXISTS document_versions (
                    id INTEGER PRIMARY KEY,
                    doc_id INTEGER NOT NULL,
                    version INTEGER NOT NULL,
                    content_hash VARCHAR(64),
                    word_count INTEGER,
                    extracted_at TIMESTAMP,
                    change_summary TEXT,
                    obligations_changed TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
                )
            )
            print("   ✅ document_versions created")
        except Exception as e:
            print(f"   ⚠️  document_versions: {e}")

        # Migration 3: Create obligation_embeddings table
        print("\n3. Creating obligation_embeddings table...")
        try:
            conn.execute(
                text(
                    """
                CREATE TABLE IF NOT EXISTS obligation_embeddings (
                    obligation_id INTEGER PRIMARY KEY,
                    embedding_vector TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
                )
            )
            print("   ✅ obligation_embeddings created")
        except Exception as e:
            print(f"   ⚠️  obligation_embeddings: {e}")

        # Migration 4: Create processing_queue table
        print("\n4. Creating processing_queue table...")
        try:
            conn.execute(
                text(
                    """
                CREATE TABLE IF NOT EXISTS processing_queue (
                    id INTEGER PRIMARY KEY,
                    task_type VARCHAR(50) NOT NULL,
                    celex VARCHAR(64),
                    doc_id INTEGER,
                    status VARCHAR(20) DEFAULT 'pending',
                    priority INTEGER DEFAULT 5,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    error_message TEXT
                )
            """
                )
            )
            print("   ✅ processing_queue created")
        except Exception as e:
            print(f"   ⚠️  processing_queue: {e}")

        # Migration 5: Create extraction_attempts table
        print("\n5. Creating extraction_attempts table...")
        try:
            conn.execute(
                text(
                    """
                CREATE TABLE IF NOT EXISTS extraction_attempts (
                    id INTEGER PRIMARY KEY,
                    celex VARCHAR(64),
                    strategy VARCHAR(50),
                    success BOOLEAN,
                    word_count INTEGER,
                    error_message TEXT,
                    attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
                )
            )
            print("   ✅ extraction_attempts created")
        except Exception as e:
            print(f"   ⚠️  extraction_attempts: {e}")

        # Create indexes
        print("\n6. Creating indexes...")
        indexes = [
            ("idx_doc_versions_doc_id", "document_versions", "doc_id"),
            ("idx_queue_status", "processing_queue", "status"),
            ("idx_queue_celex", "processing_queue", "celex"),
            ("idx_extraction_celex", "extraction_attempts", "celex"),
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
    print("MIGRATIONS COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    run_migrations()
