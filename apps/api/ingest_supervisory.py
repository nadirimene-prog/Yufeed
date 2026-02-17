#!/usr/bin/env python3
"""
Ingest content from EU Supervisory Authorities.

Run: cd apps/api && python3 ingest_supervisory.py [--dry-run]
"""

import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

os.chdir("/Users/imenenadir/Documents/Yufeed/apps/api")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./compliance.db")
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

# Import the fetchers
sys.path.insert(0, "src")
from ingestion.supervisory_fetcher import SupervisoryAggregator


def main(dry_run: bool = False):
    print("=" * 70)
    print("EU Supervisory Authority Ingestion")
    print("=" * 70)

    aggregator = SupervisoryAggregator()

    print("\n1. Fetching AMLA updates...")
    amla_entries = aggregator.amla.fetch()
    print(f"   Found {len(amla_entries)} AMLA entries")

    print("\n2. Fetching ESMA updates...")
    esma_entries = aggregator.esma.fetch()
    print(f"   Found {len(esma_entries)} ESMA entries")

    print("\n3. Fetching TRACFIN updates...")
    tracfin_entries = aggregator.fiu.fetch("tracfin")
    print(f"   Found {len(tracfin_entries)} TRACFIN entries")

    total = len(amla_entries) + len(esma_entries) + len(tracfin_entries)
    print(f"\n{'='*70}")
    print(f"Total entries found: {total}")

    if dry_run:
        print("\nDRY RUN - Not saving to database")
        print("\nSample entries:")
        for entry in (amla_entries + esma_entries)[:3]:
            print(f"\n  [{entry['source_system'].upper()}] {entry['title'][:60]}...")
            print(f"   Link: {entry['link'][:60]}...")
        return

    # Save to database
    print("\nSaving to database...")
    db = Session()

    from sqlalchemy import Column, Integer, String, DateTime, Text, JSON
    from sqlalchemy.orm import declarative_base
    from datetime import datetime

    Base = declarative_base()

    class SupervisoryUpdate(Base):
        __tablename__ = "supervisory_updates"
        id = Column(Integer, primary_key=True)
        source = Column(String)
        title = Column(String)
        link = Column(String)
        description = Column(Text)
        published = Column(DateTime)
        celex = Column(String)
        jurisdiction = Column(String)
        authority_type = Column(String)
        topics = Column(JSON)
        fetched_at = Column(DateTime, default=datetime.utcnow)

    # Create table if not exists
    Base.metadata.create_all(engine)

    saved = 0
    for entry_list in [amla_entries, esma_entries, tracfin_entries]:
        for entry in entry_list:
            # Check for duplicates
            existing = db.query(SupervisoryUpdate).filter_by(link=entry.get("link")).first()

            if existing:
                continue

            # Parse date
            published = None
            if entry.get("published"):
                try:
                    from email.utils import parsedate_to_datetime

                    published = parsedate_to_datetime(entry["published"])
                except:
                    pass

            update = SupervisoryUpdate(
                source=entry.get("source_system"),
                title=entry.get("title"),
                link=entry.get("link"),
                description=entry.get("description"),
                published=published,
                celex=entry.get("celex"),
                jurisdiction=entry.get("jurisdiction"),
                authority_type=entry.get("authority_type"),
                topics=entry.get("topics", []),
            )
            db.add(update)
            saved += 1

    db.commit()
    db.close()

    print(f"✅ Saved {saved} new entries to database")
    print(f"\n{'='*70}")
    print("Next steps:")
    print("  1. Review new entries in database")
    print("  2. Extract obligations from relevant documents")
    print("  3. Link to policies in your compliance framework")
    print(f"{'='*70}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Show what would be ingested")
    args = parser.parse_args()

    main(dry_run=args.dry_run)
