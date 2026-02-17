#!/usr/bin/env python3
"""
Add EU supervisory authority sources to Yufeed ingestion system.

Run: cd apps/api && python3 add_supervisory_sources.py
"""

import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

os.chdir("/Users/imenenadir/Documents/Yufeed/apps/api")

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./compliance.db")
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
db = Session()

Base = declarative_base()


class RegulatorySource(Base):
    __tablename__ = "regulatory_sources"
    id = Column(Integer, primary_key=True)
    source_key = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    jurisdiction = Column(String, nullable=False)
    language = Column(String, default="en")
    source_type = Column(String, default="rss")
    base_url = Column(String)
    schedule = Column(String, default="daily")
    is_active = Column(Boolean, default=True)
    last_ingested_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


# Define new supervisory sources
new_sources = [
    # AMLA - Anti-Money Laundering Authority
    {
        "source_key": "amla-news",
        "name": "AMLA - Anti-Money Laundering Authority",
        "jurisdiction": "EU",
        "language": "en",
        "source_type": "rss",
        "base_url": "https://www.amla.europa.eu/news_en/rss",
        "schedule": "daily",
        "is_active": True,
    },
    # ESMA Digital Finance
    {
        "source_key": "esma-digital",
        "name": "ESMA - Digital Finance & Innovation",
        "jurisdiction": "EU",
        "language": "en",
        "source_type": "rss",
        "base_url": "https://www.esma.europa.eu/rss.xml",
        "schedule": "daily",
        "is_active": True,
    },
    # EBA
    {
        "source_key": "eba-news",
        "name": "EBA - European Banking Authority",
        "jurisdiction": "EU",
        "language": "en",
        "source_type": "rss",
        "base_url": "https://www.eba.europa.eu/news-and-media/news-and-updates/rss",
        "schedule": "daily",
        "is_active": True,
    },
    # TRACFIN France
    {
        "source_key": "tracfin-fr",
        "name": "TRACFIN - France FIU",
        "jurisdiction": "FR",
        "language": "fr",
        "source_type": "rss",
        "base_url": "https://www.economie.gouv.fr/tracfin/rss",
        "schedule": "daily",
        "is_active": True,
    },
    # AMF France
    {
        "source_key": "amf-france",
        "name": "AMF - Autorité des Marchés Financiers",
        "jurisdiction": "FR",
        "language": "fr",
        "source_type": "rss",
        "base_url": "https://www.amf-france.org/rss",
        "schedule": "daily",
        "is_active": True,
    },
    # BaFin Germany
    {
        "source_key": "bafin-de",
        "name": "BaFin - German Financial Supervision",
        "jurisdiction": "DE",
        "language": "de",
        "source_type": "rss",
        "base_url": "https://www.bafin.de/DE/Service/Newsletter/Newsletter_node.html",
        "schedule": "daily",
        "is_active": True,
    },
    # ECB
    {
        "source_key": "ecb-news",
        "name": "ECB - European Central Bank",
        "jurisdiction": "EU",
        "language": "en",
        "source_type": "rss",
        "base_url": "https://www.ecb.europa.eu/rss/press.html",
        "schedule": "daily",
        "is_active": True,
    },
]

print("=" * 70)
print("Adding EU Supervisory Authority Sources")
print("=" * 70)

added = 0
updated = 0

for source_data in new_sources:
    existing = db.query(RegulatorySource).filter_by(source_key=source_data["source_key"]).first()

    if existing:
        # Update existing
        existing.name = source_data["name"]
        existing.base_url = source_data["base_url"]
        existing.jurisdiction = source_data["jurisdiction"]
        existing.updated_at = datetime.utcnow()
        updated += 1
        print(f"  🔄 Updated: {source_data['name']}")
    else:
        # Create new
        source = RegulatorySource(**source_data)
        db.add(source)
        added += 1
        print(f"  ➕ Added: {source_data['name']}")

db.commit()

print(f"\n{'='*70}")
print(f"Done! Added: {added}, Updated: {updated}")
print(f"{'='*70}")

# Show all sources
print("\nAll Regulatory Sources:")
print("-" * 70)
sources = (
    db.query(RegulatorySource).order_by(RegulatorySource.jurisdiction, RegulatorySource.name).all()
)
for s in sources:
    status = "✅" if s.is_active else "❌"
    print(f"  {status} [{s.jurisdiction}] {s.name}")
    print(f"      Key: {s.source_key} | Type: {s.source_type}")
    if s.last_ingested_at:
        print(f"      Last ingested: {s.last_ingested_at.strftime('%Y-%m-%d')}")
    print()

db.close()
