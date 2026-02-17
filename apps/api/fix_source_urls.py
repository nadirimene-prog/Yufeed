#!/usr/bin/env python3
"""
Find correct URLs for failing sources and update them.
"""

import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

os.chdir("/Users/imenenadir/Documents/Yufeed/apps/api")
sys.path.insert(0, "src")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./compliance.db")
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
db = Session()

print("=" * 70)
print("FIXING SOURCE URLS")
print("=" * 70)

# Test different URL patterns for EUR-Lex
test_urls = {
    "eur-lex-oj-en": [
        "https://eur-lex.europa.eu/RSS/oj/oj_L.xml",
        "https://eur-lex.europa.eu/rss/oj_L.xml",
        "https://eur-lex.europa.eu/rss/oj/oj_L.xml",
    ],
    "eur-lex-oj-fr": [
        "https://eur-lex.europa.eu/RSS/oj/oj_L.xml?lang=fr",
        "https://eur-lex.europa.eu/rss/oj_L_fr.xml",
    ],
    "legifrance": [
        "https://www.legifrance.gouv.fr/rss/jo.xml",
        "https://www.legifrance.gouv.fr/jorf/rss",
    ],
    "amla": [
        "https://www.amla.europa.eu/rss",
        "https://www.amla.europa.eu/news/rss",
    ],
    "eba": [
        "https://www.eba.europa.eu/rss",
        "https://www.eba.europa.eu/news/rss",
    ],
}

import requests


def test_url(url):
    try:
        resp = requests.get(url, timeout=15, allow_redirects=True)
        if resp.status_code == 200 and len(resp.content) > 100:
            return True, len(resp.content)
        return False, resp.status_code
    except Exception as e:
        return False, str(e)[:30]


for source_key, urls in test_urls.items():
    print(f"\n🔍 Testing {source_key}...")
    for url in urls:
        result, info = test_url(url)
        status = "✅" if result else "❌"
        print(f"   {status} {url[:55]}... ({info})")
        if result:
            # Update in database
            from sqlalchemy import Column, Integer, String, DateTime, Boolean
            from sqlalchemy.orm import declarative_base

            Base = declarative_base()

            class RegulatorySource(Base):
                __tablename__ = "regulatory_sources"
                id = Column(Integer, primary_key=True)
                source_key = Column(String, unique=True)
                base_url = Column(String)

            source = db.query(RegulatorySource).filter_by(source_key=source_key).first()
            if source and source.base_url != url:
                old_url = source.base_url
                source.base_url = url
                db.commit()
                print(f"   📝 Updated URL: {old_url[:40]}... → {url[:40]}...")
            break

db.close()
print("\n" + "=" * 70)
print("Done!")
print("=" * 70)
