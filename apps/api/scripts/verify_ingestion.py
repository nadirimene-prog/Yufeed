import logging
import sys
import os

# Ensure src is importable
if os.path.exists("src"):
    sys.path.append(os.getcwd())

from src.database import SessionLocal
from src.ingestion.manager import IngestionManager

logging.basicConfig(level=logging.INFO)


def main():
    print("Running Ingestion Test...")
    db = SessionLocal()
    try:
        manager = IngestionManager(db)
        manager.run_weekly_ingestion()
        print("Ingestion ran successfully.")
    except Exception as e:
        print(f"Ingestion failed: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
