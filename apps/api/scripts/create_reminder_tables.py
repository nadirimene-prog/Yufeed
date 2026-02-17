#!/usr/bin/env python3
"""
Database Migration: Deadline Reminder System
Adds tables and columns for reminder functionality
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
    print("DEADLINE REMINDER SYSTEM - DATABASE MIGRATION")
    print("=" * 70)
    print(f"Database: {DATABASE_URL}")

    with engine.connect() as conn:
        # 1. Add reminder columns to regulatory_obligations
        print("\n1. Adding reminder columns to regulatory_obligations...")
        columns_to_add = [
            ("reminder_sent_at", "TIMESTAMP"),
            ("reminder_count", "INTEGER DEFAULT 0"),
            ("last_reminder_at", "TIMESTAMP"),
            ("next_reminder_at", "TIMESTAMP"),
        ]

        for col_name, col_type in columns_to_add:
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

        # 2. Add notification preferences to users
        print("\n2. Adding notification preferences to users...")
        try:
            conn.execute(
                text(
                    """
                ALTER TABLE users
                ADD COLUMN notification_preferences JSON
            """
                )
            )
            print("   ✅ Added notification_preferences")
        except Exception as e:
            print(f"   ⚠️  notification_preferences: {e}")

        # 3. Create reminder_logs table
        print("\n3. Creating reminder_logs table...")
        try:
            conn.execute(
                text(
                    """
                CREATE TABLE IF NOT EXISTS reminder_logs (
                    id INTEGER PRIMARY KEY,
                    obligation_id INTEGER NOT NULL,
                    user_id INTEGER,
                    reminder_type VARCHAR(50) NOT NULL,
                    days_before_deadline INTEGER,
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    channel VARCHAR(20) DEFAULT 'email',
                    status VARCHAR(20) DEFAULT 'sent',
                    error_message TEXT,
                    opened_at TIMESTAMP,
                    clicked_at TIMESTAMP
                )
            """
                )
            )
            print("   ✅ Created reminder_logs")
        except Exception as e:
            print(f"   ⚠️  reminder_logs: {e}")

        # 4. Create user_deadline_subscriptions table
        print("\n4. Creating user_deadline_subscriptions table...")
        try:
            conn.execute(
                text(
                    """
                CREATE TABLE IF NOT EXISTS user_deadline_subscriptions (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    obligation_id INTEGER,
                    doc_id INTEGER,
                    reminder_days INTEGER[] DEFAULT '[30, 14, 7]',
                    email_enabled BOOLEAN DEFAULT 1,
                    slack_enabled BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, obligation_id),
                    UNIQUE(user_id, doc_id)
                )
            """
                )
            )
            print("   ✅ Created user_deadline_subscriptions")
        except Exception as e:
            print(f"   ⚠️  user_deadline_subscriptions: {e}")

        # 5. Create indexes
        print("\n5. Creating indexes...")
        indexes = [
            ("idx_reminder_logs_obligation", "reminder_logs", "obligation_id"),
            ("idx_reminder_logs_user", "reminder_logs", "user_id"),
            ("idx_reminder_logs_sent", "reminder_logs", "sent_at"),
            ("idx_obligations_next_reminder", "regulatory_obligations", "next_reminder_at"),
            ("idx_subscriptions_user", "user_deadline_subscriptions", "user_id"),
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
    print("  1. Build reminder_service.py")
    print("  2. Create Celery tasks")
    print("  3. Build API endpoints")


if __name__ == "__main__":
    run_migration()
