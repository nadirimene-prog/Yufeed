#!/usr/bin/env python3
"""
Test script for CELEX improvements
Tests normalization, caching, and API functionality
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from utils.celex_utils import (
    normalize_celex,
    is_valid_celex,
    parse_celex,
    generate_celex_variations,
    suggest_celex
)

def test_normalization():
    """Test CELEX normalization with various inputs."""
    print("=" * 60)
    print("Testing CELEX Normalization")
    print("=" * 60)

    test_cases = [
        ("GDPR", "32016R0679"),
        ("AI Act", "32024R1689"),
        ("2016/679", "32016R0679"),
        ("2016-679", "32016R0679"),
        ("Regulation 2016/679", "32016R0679"),
        ("32016R0679", "32016R0679"),
        ("32016R679", "32016R0679"),  # Missing leading zero
        ("DMA", "32022R1925"),
        ("DSA", "32022R2065"),
    ]

    passed = 0
    failed = 0

    for input_str, expected in test_cases:
        result = normalize_celex(input_str)
        status = "✅ PASS" if result == expected else "❌ FAIL"
        print(f"{status} | Input: '{input_str}' → Expected: {expected}, Got: {result}")

        if result == expected:
            passed += 1
        else:
            failed += 1

    print(f"\nResults: {passed} passed, {failed} failed")
    print()


def test_parsing():
    """Test CELEX parsing."""
    print("=" * 60)
    print("Testing CELEX Parsing")
    print("=" * 60)

    celex = "32016R0679"
    parsed = parse_celex(celex)

    if parsed:
        print(f"✅ Successfully parsed {celex}:")
        print(f"   Sector: {parsed['sector']} ({parsed['sector_name']})")
        print(f"   Year: {parsed['year']}")
        print(f"   Type: {parsed['document_type']} ({parsed['type_name']})")
        print(f"   Number: {parsed['number']}")
    else:
        print(f"❌ Failed to parse {celex}")

    print()


def test_variations():
    """Test CELEX variation generation."""
    print("=" * 60)
    print("Testing CELEX Variation Generation")
    print("=" * 60)

    celex = "32016R0679"
    variations = generate_celex_variations(celex)

    print(f"Variations for {celex}:")
    for var in variations:
        print(f"   - {var}")

    print()


def test_suggestions():
    """Test CELEX suggestions."""
    print("=" * 60)
    print("Testing CELEX Suggestions")
    print("=" * 60)

    test_queries = ["GDPR", "AI", "DATA"]

    for query in test_queries:
        suggestions = suggest_celex(query, limit=5)
        print(f"Query: '{query}' → {len(suggestions)} suggestions:")
        for suggestion in suggestions:
            print(f"   - {suggestion}")
        print()


def test_cache_initialization():
    """Test Redis cache initialization (without requiring Redis)."""
    print("=" * 60)
    print("Testing Cache Initialization")
    print("=" * 60)

    try:
        from cache.celex_cache import CelexCache

        # Try to initialize cache (may fail if Redis not running)
        cache = CelexCache(redis_url="redis://localhost:6379/0")

        if cache.is_connected():
            print("✅ Redis cache connected successfully")

            # Test basic operations
            test_data = {
                "celex": "32016R0679",
                "title": "Test GDPR Document",
                "work_type": "REG"
            }

            cache.set("32016R0679", test_data)
            print("✅ Successfully stored test data in cache")

            retrieved = cache.get("32016R0679")
            if retrieved and retrieved.get("title") == "Test GDPR Document":
                print("✅ Successfully retrieved test data from cache")
            else:
                print("❌ Failed to retrieve correct data from cache")

            stats = cache.get_stats()
            print(f"✅ Cache stats: {stats.get('total_keys', 0)} keys, "
                  f"{stats.get('memory_used_mb', 0):.2f} MB")

            cache.delete("32016R0679")
            cache.close()

        else:
            print("⚠️  Redis not connected (this is OK if Redis is not running)")
            print("   Cache will be disabled, but system will work without it")

    except ImportError as e:
        print(f"❌ Import error: {e}")
    except Exception as e:
        print(f"⚠️  Cache initialization error: {e}")
        print("   This is OK if Redis is not running - cache is optional")

    print()


def test_cellar_client():
    """Test CellarClient improvements (without external queries)."""
    print("=" * 60)
    print("Testing CellarClient")
    print("=" * 60)

    try:
        from ingestion.cellar import CellarClient

        # Initialize without cache for this test
        client = CellarClient(enable_cache=False)
        print("✅ CellarClient initialized successfully")

        # Test validation
        if client._validate_celex("32016R0679"):
            print("✅ CELEX validation working")
        else:
            print("❌ CELEX validation failed")

        # Test sanitization
        sanitized = client._sanitize_celex("32016R0679")
        if sanitized == "32016R0679":
            print("✅ CELEX sanitization working")
        else:
            print(f"❌ CELEX sanitization failed: {sanitized}")

        client.close()

    except ImportError as e:
        print(f"❌ Import error: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")

    print()


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("CELEX Improvements Test Suite")
    print("=" * 60 + "\n")

    test_normalization()
    test_parsing()
    test_variations()
    test_suggestions()
    test_cache_initialization()
    test_cellar_client()

    print("=" * 60)
    print("Test Suite Complete")
    print("=" * 60)
    print("\nNote: Some tests may show warnings if Redis is not running.")
    print("This is expected - the system works without Redis, just slower.")
    print()


if __name__ == "__main__":
    main()
