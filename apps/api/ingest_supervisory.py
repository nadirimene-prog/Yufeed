#!/usr/bin/env python3
"""Deprecated wrapper for supervisory ingestion.

Use the API endpoint ``POST /api/ingestion/run`` (mode=manual) or Celery task
``run_supervisory_ingestion`` in production. This script is kept for local
operability and now delegates to ``IngestionManager``.
"""

from __future__ import annotations

import argparse

from src.database import SessionLocal
from src.ingestion.manager import IngestionManager


def main(send_alerts: bool = False) -> int:
    db = SessionLocal()
    try:
        manager = IngestionManager(db)
        result = manager.run_supervisory_ingestion(send_alerts=send_alerts)
        print(result)
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--send-alerts", action="store_true", default=False)
    args = parser.parse_args()
    raise SystemExit(main(send_alerts=args.send_alerts))
