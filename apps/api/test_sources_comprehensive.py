#!/usr/bin/env python3
"""
Comprehensive test of all extraction sources with fallbacks.
"""

import sys
import os

os.chdir("/Users/imenenadir/Documents/Yufeed/apps/api")
sys.path.insert(0, "src")

import requests
import httpx
from config import settings

print("=" * 70)
print("COMPREHENSIVE SOURCE TEST WITH FALLBACKS")
print("=" * 70)

results = {}


def test_with_fallback(name, primary_url, fallback_urls=None, headers=None):
    """Test a URL with fallback options."""
    print(f"\n📡 Testing {name}...")

    urls = [primary_url] + (fallback_urls or [])

    for i, url in enumerate(urls):
        try:
            label = "Primary" if i == 0 else f"Fallback {i}"
            print(f"   Trying {label}: {url[:50]}...")

            resp = httpx.get(url, headers=headers, timeout=30, follow_redirects=True)

            if resp.status_code == 200:
                content_preview = resp.text[:200]
                has_entries = len(resp.text) > 500  # Basic check for content

                if has_entries:
                    print(f"   ✅ SUCCESS ({label}): {len(resp.text)} bytes")
                    return True, url, len(resp.text)
                else:
                    print(f"   ⚠️  {label}: Empty or minimal content")
            else:
                print(f"   ❌ {label}: HTTP {resp.status_code}")

        except Exception as e:
            print(f"   ❌ {label}: {str(e)[:40]}")

    return False, None, 0


# Headers
rss_headers = {"User-Agent": settings.RSS_USER_AGENT}
browser_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# 1. EUR-Lex OJ
results["eur-lex-oj"] = test_with_fallback(
    "EUR-Lex Official Journal",
    "https://eur-lex.europa.eu/RSS/feed.html?type=OJ&oj=L&lang=en",
    fallback_urls=[
        "https://eur-lex.europa.eu/rss/oj_L.xml",
        "https://eur-lex.europa.eu/rss/oj-L-en.xml",
    ],
    headers=browser_headers,
)

# 2. CELLAR
results["cellar"] = test_with_fallback(
    "CELLAR Ingestion",
    "https://publications.europa.eu/webapi/notification/ingestion",
    fallback_urls=[
        "https://publications.europa.eu/webapi/notification/ingestion?startDate=2024-01-01",
    ],
    headers=rss_headers,
)

# 3. Légifrance
results["legifrance"] = test_with_fallback(
    "Légifrance JORF",
    "https://www.legifrance.gouv.fr/jorf/rss",
    fallback_urls=[
        "https://legifrss.org/latest",
    ],
    headers=browser_headers,
)

# 4. ESMA (known working)
results["esma"] = test_with_fallback(
    "ESMA", "https://www.esma.europa.eu/rss.xml", headers=rss_headers
)

# 5. ECB (known working)
results["ecB"] = test_with_fallback(
    "ECB", "https://www.ecb.europa.eu/rss/press.html", headers=rss_headers
)

# 6. TRACFIN (known working)
results["tracfin"] = test_with_fallback(
    "TRACFIN", "https://www.economie.gouv.fr/tracfin/rss", headers=rss_headers
)

# 7. EUR-Lex HTML
results["eur-lex-html"] = test_with_fallback(
    "EUR-Lex HTML (MiCA)",
    "https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32023R1114",
    headers=browser_headers,
)

# 8. CELLAR SPARQL
results["cellar-sparql"] = test_with_fallback(
    "CELLAR SPARQL", "http://publications.europa.eu/webapi/rdf/sparql", headers=rss_headers
)

# Summary
print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)

working = sum(1 for r in results.values() if r[0])
total = len(results)

print(f"\nWorking: {working}/{total} sources")
print()

for source, (status, url, size) in results.items():
    icon = "✅" if status else "❌"
    size_str = f"({size} bytes)" if status else ""
    print(f"  {icon} {source:20s} {size_str}")
    if status and url:
        print(f"      URL: {url[:55]}...")

print("\n" + "=" * 70)

if working == total:
    print("🎉 ALL SOURCES WORKING!")
elif working >= total * 0.6:
    print("⚠️  MOST SOURCES WORKING - Some need attention")
else:
    print("🔴 MANY SOURCES FAILING - Needs attention")

print("=" * 70)

# Recommendations
print("\nRECOMMENDATIONS:")
print()

if not results["eur-lex-oj"][0] and not results["cellar"][0]:
    print("🔴 CRITICAL: EUR-Lex feeds not working!")
    print("   Options:")
    print("   1. Use EUR-Lex Search API instead")
    print("   2. Manual ingestion via EUR-Lex website")
    print("   3. Check EUR-Lex documentation for new RSS URLs")
    print()

if not results["legifrance"][0]:
    print("🟡 Légifrance feed not working")
    print("   Fallback: Use legifrss.org (third-party)")
    print()

if results["esma"][0] and results["ecB"][0] and results["tracfin"][0]:
    print("✅ Supervisory authorities working well")
    print("   - ESMA: MiCA guidance")
    print("   - ECB: Digital euro, payment systems")
    print("   - TRACFIN: AML typologies")
    print()

print("For EUR-Lex documents, consider:")
print("  - Periodic manual export from EUR-Lex")
print("  - Using the search API with CELEX numbers")
print("  - Checking EUR-Lex for updated feed URLs")
