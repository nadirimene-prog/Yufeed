#!/usr/bin/env python3
"""
Fix source URLs to use working alternatives.
"""

import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

os.chdir("/Users/imenenadir/Documents/Yufeed/apps/api")

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./compliance.db")
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
db = Session()

Base = declarative_base()


class RegulatorySource(Base):
    __tablename__ = "regulatory_sources"
    id = Column(Integer, primary_key=True)
    source_key = Column(String, unique=True)
    name = Column(String)
    base_url = Column(String)
    is_active = Column(Boolean)


print("=" * 70)
print("FIXING SOURCE URLS TO WORKING ALTERNATIVES")
print("=" * 70)

# URL fixes based on testing
url_fixes = {
    # Use legifrss.org as fallback for Légifrance
    "legifrance-jorf-fr": {
        "old": "https://legifrance.gouv.fr/jorf/rss",
        "new": "https://legifrss.org/latest",
        "reason": "Official Légifrance RSS is 403, using legifrss.org",
    },
    # Mark EUR-Lex OJ as needing alternative
    "eur-lex-oj-en": {
        "old": "https://eur-lex.europa.eu/RSS/feed.html?type=OJ&oj=L&lang=en",
        "new": "https://publications.europa.eu/webapi/notification/ingestion?startDate=2024-01-01",
        "reason": "EUR-Lex RSS 404, using CELLAR ingestion",
    },
    "eur-lex-oj-fr": {
        "old": "https://eur-lex.europa.eu/RSS/feed.html?type=OJ&oj=L&lang=fr",
        "new": "https://publications.europa.eu/webapi/notification/ingestion?startDate=2024-01-01",
        "reason": "EUR-Lex RSS 404, using CELLAR ingestion",
    },
}

for source_key, fix in url_fixes.items():
    source = db.query(RegulatorySource).filter_by(source_key=source_key).first()
    if source:
        old_url = source.base_url
        source.base_url = fix["new"]
        db.commit()
        print(f"\n📝 Fixed {source_key}:")
        print(f"   From: {old_url}")
        print(f"   To:   {fix['new']}")
        print(f"   Reason: {fix['reason']}")
    else:
        print(f"\n⚠️  Source {source_key} not found in database")

db.close()

print("\n" + "=" * 70)
print("✅ SOURCE URLS UPDATED")
print("=" * 70)

print("\n⚠️  IMPORTANT NOTE:")
print("   EUR-Lex OJ RSS feeds are no longer working (404).")
print("   The system will now use CELLAR ingestion feed instead.")
print("   This requires the ingestion code to handle date parameters.")
print()
print("   Recommended action:")
print("   1. Update ingestion/manager.py to use fetch_cellar_ingestion()")
print("   2. Or manually specify CELEX numbers to track")
print()
