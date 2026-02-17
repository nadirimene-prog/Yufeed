#!/usr/bin/env python3
"""
Test all extraction sources to verify they're working.
"""

import sys
import os

os.chdir("/Users/imenenadir/Documents/Yufeed/apps/api")
sys.path.insert(0, "src")

import feedparser
import requests
from datetime import datetime

print("=" * 70)
print("TESTING ALL EXTRACTION SOURCES")
print("=" * 70)


def test_rss_feed(name, url, expected_entries=1):
    """Test an RSS feed."""
    print(f"\n📡 Testing {name}...")
    print(f"   URL: {url[:60]}...")

    try:
        # Use requests to fetch with timeout, then parse
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        feed = feedparser.parse(response.content)

        if feed.bozo and hasattr(feed, "bozo_exception"):
            print(f"   ⚠️  Parse warning: {feed.bozo_exception}")

        entries_count = len(feed.entries)

        if entries_count >= expected_entries:
            print(f"   ✅ SUCCESS: {entries_count} entries found")
            # Show latest entry
            if entries_count > 0:
                latest = feed.entries[0]
                title = latest.get("title", "No title")[:50]
                print(f"   📄 Latest: {title}...")
            return True
        else:
            print(f"   ❌ FAILED: Only {entries_count} entries (expected {expected_entries})")
            return False

    except Exception as e:
        print(f"   ❌ ERROR: {str(e)[:60]}")
        return False


def test_http_endpoint(name, url):
    """Test an HTTP endpoint."""
    print(f"\n🌐 Testing {name}...")
    print(f"   URL: {url[:60]}...")

    try:
        response = requests.get(url, timeout=30, allow_redirects=True)

        if response.status_code == 200:
            print(f"   ✅ SUCCESS: HTTP {response.status_code}")
            return True
        else:
            print(f"   ❌ FAILED: HTTP {response.status_code}")
            return False

    except Exception as e:
        print(f"   ❌ ERROR: {str(e)[:60]}")
        return False


# Test Results
results = {}

# 1. EUR-Lex RSS Feeds
print("\n" + "=" * 70)
print("EU LEGISLATIVE SOURCES")
print("=" * 70)

results["eur-lex-oj-en"] = test_rss_feed(
    "EUR-Lex Official Journal (EN)",
    "https://eur-lex.europa.eu/RSS/feed.html?type=OJ&oj=L&lang=en",
    expected_entries=5,
)

results["eur-lex-oj-fr"] = test_rss_feed(
    "EUR-Lex Official Journal (FR)",
    "https://eur-lex.europa.eu/RSS/feed.html?type=OJ&oj=L&lang=fr",
    expected_entries=5,
)

# 2. Légifrance
print("\n" + "=" * 70)
print("NATIONAL SOURCES")
print("=" * 70)

results["legifrance"] = test_rss_feed(
    "Légifrance JORF",
    "https://www.legifrance.gouv.fr/content/download/481/5533/version/3/file/rss_jorf.xml",
    expected_entries=1,
)

# 3. Supervisory Authorities
print("\n" + "=" * 70)
print("SUPERVISORY AUTHORITIES")
print("=" * 70)

results["amla"] = test_rss_feed(
    "AMLA (Anti-Money Laundering Authority)",
    "https://www.amla.europa.eu/news_en/rss",
    expected_entries=0,  # New authority, may be empty
)

results["esma"] = test_rss_feed(
    "ESMA (Digital Finance)", "https://www.esma.europa.eu/rss.xml", expected_entries=1
)

results["eba"] = test_rss_feed(
    "EBA (European Banking Authority)",
    "https://www.eba.europa.eu/news-and-media/news-and-updates/rss",
    expected_entries=1,
)

results["ecb"] = test_rss_feed(
    "ECB (European Central Bank)", "https://www.ecb.europa.eu/rss/press.html", expected_entries=1
)

results["tracfin"] = test_rss_feed(
    "TRACFIN (France FIU)", "https://www.economie.gouv.fr/tracfin/rss", expected_entries=1
)

results["amf"] = test_rss_feed("AMF France", "https://www.amf-france.org/rss", expected_entries=1)

# 4. EUR-Lex Search/Cellar
print("\n" + "=" * 70)
print("EUR-LEX API ENDPOINTS")
print("=" * 70)

results["eur-lex-html"] = test_http_endpoint(
    "EUR-Lex HTML (MiCA test)",
    "https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32023R1114",
)

results["cellar-sparql"] = test_http_endpoint(
    "CELLAR SPARQL Endpoint", "http://publications.europa.eu/webapi/rdf/sparql"
)

results["publications-cellar"] = test_http_endpoint(
    "Publications.europa.eu (CELEX)",
    "https://publications.europa.eu/resource/celex/32023R1114?language=eng",
)

# Summary
print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)

working = sum(1 for v in results.values() if v)
total = len(results)

print(f"\nWorking: {working}/{total} sources")
print()

for source, status in results.items():
    icon = "✅" if status else "❌"
    print(f"  {icon} {source}")

print("\n" + "=" * 70)

if working == total:
    print("🎉 ALL SOURCES WORKING!")
elif working >= total * 0.7:
    print("⚠️  MOST SOURCES WORKING - Check failed ones")
else:
    print("🔴 MANY SOURCES FAILING - Needs attention")

print("=" * 70)
