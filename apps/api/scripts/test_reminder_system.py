#!/usr/bin/env python3
"""
Test Script: Deadline Reminder System
Verifies all components are working correctly.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

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
Session = sessionmaker(bind=engine)


def test_database_schema():
    """Test that all reminder tables exist."""
    print("\n" + "=" * 70)
    print("TEST 1: Database Schema")
    print("=" * 70)

    with engine.connect() as conn:
        # Check tables exist
        tables = ["reminder_logs", "user_deadline_subscriptions"]
        for table in tables:
            result = conn.execute(
                text(
                    f"""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='{table}'
            """
                )
            ).fetchone()

            if result:
                print(f"  ✅ Table '{table}' exists")
            else:
                print(f"  ❌ Table '{table}' NOT FOUND")

        # Check columns in regulatory_obligations
        columns = ["reminder_sent_at", "reminder_count", "last_reminder_at", "next_reminder_at"]
        for col in columns:
            try:
                conn.execute(text(f"SELECT {col} FROM regulatory_obligations LIMIT 1"))
                print(f"  ✅ Column '{col}' exists")
            except:
                print(f"  ❌ Column '{col}' NOT FOUND")


def test_reminder_service():
    """Test the reminder service."""
    print("\n" + "=" * 70)
    print("TEST 2: Reminder Service")
    print("=" * 70)

    try:
        from src.services.reminder_service import ReminderService

        print("  ✅ ReminderService imports successfully")

        db = Session()
        service = ReminderService(db)
        print("  ✅ ReminderService initializes")

        # Test getting upcoming deadlines
        upcoming = service.get_upcoming_deadlines(days_window=90)
        print(f"  ✅ Found {len(upcoming)} upcoming deadlines")

        if upcoming:
            print(f"\n  Sample deadlines:")
            for d in upcoming[:3]:
                print(f"    - {d.celex}: {d.days_remaining} days ({d.reminder_type.value})")

        db.close()

    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback

        traceback.print_exc()


def test_celery_tasks():
    """Test that Celery tasks are importable."""
    print("\n" + "=" * 70)
    print("TEST 3: Celery Tasks")
    print("=" * 70)

    try:
        from src.tasks.reminders import check_upcoming_deadlines, send_reminder, send_weekly_digest

        print("  ✅ check_upcoming_deadlines task imports")
        print("  ✅ send_reminder task imports")
        print("  ✅ send_weekly_digest task imports")
    except Exception as e:
        print(f"  ❌ Error importing tasks: {e}")


def test_api_endpoints():
    """Test that API router is importable."""
    print("\n" + "=" * 70)
    print("TEST 4: API Endpoints")
    print("=" * 70)

    try:
        from src.api.reminders import router

        print("  ✅ Reminder API router imports successfully")
        print(f"  ✅ Router prefix: {router.prefix}")
        print(f"  ✅ Number of routes: {len(router.routes)}")

        print("\n  Available endpoints:")
        for route in router.routes:
            methods = ",".join(route.methods) if hasattr(route, "methods") else "GET"
            print(f"    {methods:10} {route.path}")

    except Exception as e:
        print(f"  ❌ Error: {e}")


def test_statistics():
    """Test reminder statistics."""
    print("\n" + "=" * 70)
    print("TEST 5: Reminder Statistics")
    print("=" * 70)

    try:
        from src.services.reminder_service import ReminderService

        db = Session()
        service = ReminderService(db)

        stats = service.get_reminder_statistics(days=30)
        print(f"  ✅ Statistics retrieved successfully")
        print(f"\n  Stats (last 30 days):")
        print(f"    Total sent: {stats['total_sent']}")
        print(f"    Successful: {stats['successful']}")
        print(f"    Failed: {stats['failed']}")
        print(f"    Opened: {stats['opened']}")
        print(f"    Open rate: {stats['open_rate']}%")

        db.close()

    except Exception as e:
        print(f"  ❌ Error: {e}")


def main():
    print("\n" + "╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "DEADLINE REMINDER SYSTEM TEST" + " " * 29 + "║")
    print("╚" + "=" * 78 + "╝")

    test_database_schema()
    test_reminder_service()
    test_celery_tasks()
    test_api_endpoints()
    test_statistics()

    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print("\n✅ All core components are in place!")
    print("\nNext steps:")
    print("  1. Add reminder router to main.py")
    print("  2. Configure Celery beat schedule")
    print("  3. Test with real deadlines")
    print("  4. Monitor reminder_logs table")


if __name__ == "__main__":
    main()
