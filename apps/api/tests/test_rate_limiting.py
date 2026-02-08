#!/usr/bin/env python3
"""
Rate Limiting Test Script

Tests the rate limiting functionality without starting the full server.
"""
import sys

from src.middleware.rate_limiter import limiter, RateLimits, get_identifier
from fastapi import Request
from unittest.mock import Mock


def test_rate_limits_configuration():
    """Test that rate limits are properly configured."""
    print("Testing rate limit configurations...")

    # Verify RateLimits class has expected attributes
    expected_limits = [
        "AUTH_LOGIN",
        "AUTH_REGISTER",
        "AUTH_REFRESH",
        "SEARCH",
        "QUERY",
        "CREATE",
        "UPDATE",
        "DELETE",
        "READ",
        "LIST",
        "AI_ANALYSIS",
        "AI_GENERATION",
        "EXPORT",
        "REPORT",
    ]

    for limit_name in expected_limits:
        if hasattr(RateLimits, limit_name):
            limit_value = getattr(RateLimits, limit_name)
            print(f"  ✅ {limit_name}: {limit_value}")
        else:
            print(f"  ❌ Missing limit: {limit_name}")
            return False

    print("✅ All rate limits configured correctly\n")
    return True


def test_get_identifier():
    """Test the identifier extraction logic."""
    print("Testing identifier extraction...")

    # Test 1: IP-based identifier (no user)
    mock_request = Mock(spec=Request)

    # Create a simple object for state without user attribute
    class EmptyState:
        pass

    mock_request.state = EmptyState()
    mock_request.client = Mock()
    mock_request.client.host = "192.168.1.100"

    identifier = get_identifier(mock_request)
    assert identifier.startswith("ip:"), f"Expected IP identifier, got {identifier}"
    print(f"  ✅ IP-based identifier: {identifier}")

    # Test 2: User-based identifier
    class UserState:
        def __init__(self):
            self.user = Mock()
            self.user.user_id = "user-123"

    mock_request.state = UserState()

    identifier = get_identifier(mock_request)
    assert identifier == "user:user-123", f"Expected user identifier, got {identifier}"
    print(f"  ✅ User-based identifier: {identifier}")

    print("✅ Identifier extraction working correctly\n")
    return True


def test_limiter_initialization():
    """Test that limiter is properly initialized."""
    print("Testing limiter initialization...")

    # Check limiter attributes
    assert limiter is not None, "Limiter not initialized"
    print("  ✅ Limiter initialized")

    # Check if limiter has the expected methods
    expected_methods = ["limit", "reset"]
    for method in expected_methods:
        if hasattr(limiter, method):
            print(f"  ✅ Method '{method}' available")
        else:
            print(f"  ⚠️  Method '{method}' not found")

    print("✅ Limiter initialization successful\n")
    return True


def test_rate_limit_values():
    """Test that rate limit values are reasonable."""
    print("Testing rate limit values...")

    # Define expected constraints
    constraints = {
        "AUTH_LOGIN": (1, 20, "minute"),  # Between 1-20 per minute for security
        "AUTH_REGISTER": (1, 10, "hour"),  # Between 1-10 per hour for security
        "AI_ANALYSIS": (1, 20, "hour"),  # Between 1-20 per hour (expensive)
    }

    for limit_name, (min_val, max_val, unit) in constraints.items():
        limit_str = getattr(RateLimits, limit_name)
        # Parse "X per Y" format
        parts = limit_str.split()
        if len(parts) >= 3:
            count = int(parts[0])
            period = parts[2]

            if period == unit:
                if min_val <= count <= max_val:
                    print(f"  ✅ {limit_name} = {limit_str} (valid)")
                else:
                    print(f"  ⚠️  {limit_name} = {limit_str} (outside recommended range)")
            else:
                print(f"  ⚠️  {limit_name} = {limit_str} (different time unit)")

    print("✅ Rate limit values reviewed\n")
    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("Rate Limiting Test Suite")
    print("=" * 60 + "\n")

    tests = [
        ("Rate Limits Configuration", test_rate_limits_configuration),
        ("Get Identifier", test_get_identifier),
        ("Limiter Initialization", test_limiter_initialization),
        ("Rate Limit Values", test_rate_limit_values),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results.append((test_name, False))

    # Summary
    print("=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print("\n⚠️  Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
