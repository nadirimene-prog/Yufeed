#!/usr/bin/env python3
"""
Comprehensive Endpoint Testing
Tests all new endpoints for Reminders, Gap Analysis, and Policy Generator
"""

import sys
import requests
import json
from datetime import datetime
from pathlib import Path

# Configuration
BASE_URL = "http://localhost:8000"
TOKEN = None  # Will be set after login


class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    END = "\033[0m"


def print_header(text):
    print(f"\n{Colors.BLUE}{'='*80}{Colors.END}")
    print(f"{Colors.BLUE}{text.center(80)}{Colors.END}")
    print(f"{Colors.BLUE}{'='*80}{Colors.END}\n")


def print_success(text):
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")


def print_error(text):
    print(f"{Colors.RED}❌ {text}{Colors.END}")


def print_warning(text):
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.END}")


def make_request(method, endpoint, data=None, params=None):
    """Make HTTP request and return response."""
    url = f"{BASE_URL}{endpoint}"
    headers = {"Content-Type": "application/json"}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"

    try:
        if method == "GET":
            response = requests.get(url, headers=headers, params=params, timeout=10)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data, timeout=10)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers, timeout=10)
        else:
            return None, f"Unknown method: {method}"

        return response, None
    except requests.exceptions.ConnectionError:
        return None, "Connection failed - is the server running?"
    except requests.exceptions.Timeout:
        return None, "Request timeout"
    except Exception as e:
        return None, str(e)


def test_endpoint(name, method, endpoint, data=None, params=None, expected_status=200):
    """Test a single endpoint."""
    response, error = make_request(method, endpoint, data, params)

    if error:
        print_error(f"{name}: {error}")
        return False

    if response.status_code == expected_status:
        print_success(f"{name} ({response.status_code})")
        return True
    else:
        print_error(f"{name}: Expected {expected_status}, got {response.status_code}")
        try:
            print(f"   Response: {response.text[:200]}")
        except:
            pass
        return False


def test_gap_analysis_endpoints():
    """Test all Gap Analysis endpoints."""
    print_header("TESTING: Gap Analysis Endpoints")

    results = []

    # Test dashboard
    results.append(
        test_endpoint("GET /api/gap-analysis/dashboard", "GET", "/api/gap-analysis/dashboard")
    )

    # Test gaps list
    results.append(
        test_endpoint(
            "GET /api/gap-analysis/gaps", "GET", "/api/gap-analysis/gaps", params={"limit": 5}
        )
    )

    # Test gaps with filter
    results.append(
        test_endpoint(
            "GET /api/gap-analysis/gaps?severity=critical",
            "GET",
            "/api/gap-analysis/gaps",
            params={"severity": "critical"},
        )
    )

    # Test coverage by document
    results.append(
        test_endpoint(
            "GET /api/gap-analysis/coverage-by-document",
            "GET",
            "/api/gap-analysis/coverage-by-document",
        )
    )

    # Test categories
    results.append(
        test_endpoint("GET /api/gap-analysis/categories", "GET", "/api/gap-analysis/categories")
    )

    # Test trend
    results.append(
        test_endpoint(
            "GET /api/gap-analysis/trend", "GET", "/api/gap-analysis/trend", params={"days": 30}
        )
    )

    passed = sum(results)
    total = len(results)
    print(f"\nGap Analysis: {passed}/{total} passed")
    return passed, total


def test_reminder_endpoints():
    """Test all Reminder endpoints."""
    print_header("TESTING: Reminder Endpoints")

    results = []

    # Test upcoming deadlines
    results.append(
        test_endpoint(
            "GET /api/reminders/upcoming", "GET", "/api/reminders/upcoming", params={"days": 30}
        )
    )

    # Test statistics
    results.append(
        test_endpoint(
            "GET /api/reminders/statistics", "GET", "/api/reminders/statistics", params={"days": 30}
        )
    )

    # Test subscriptions
    results.append(
        test_endpoint("GET /api/reminders/subscriptions", "GET", "/api/reminders/subscriptions")
    )

    passed = sum(results)
    total = len(results)
    print(f"\nReminders: {passed}/{total} passed")
    return passed, total


def test_policy_generator_endpoints():
    """Test all Policy Generator endpoints."""
    print_header("TESTING: Policy Generator Endpoints")

    results = []

    # Test templates list
    results.append(
        test_endpoint(
            "GET /api/policy-generator/templates", "GET", "/api/policy-generator/templates"
        )
    )

    # Test stats
    results.append(
        test_endpoint(
            "GET /api/policy-generator/stats",
            "GET",
            "/api/policy-generator/stats",
            params={"days": 30},
        )
    )

    # Test jobs list
    results.append(
        test_endpoint(
            "GET /api/policy-generator/jobs",
            "GET",
            "/api/policy-generator/jobs",
            params={"limit": 5},
        )
    )

    # Test template variables (for aml-cft-policy-master)
    results.append(
        test_endpoint(
            "GET /api/policy-generator/templates/aml-cft-policy-master/variables",
            "GET",
            "/api/policy-generator/templates/aml-cft-policy-master/variables",
        )
    )

    passed = sum(results)
    total = len(results)
    print(f"\nPolicy Generator: {passed}/{total} passed")
    return passed, total


def test_server_health():
    """Test if server is running."""
    print_header("TESTING: Server Health")

    response, error = make_request("GET", "/healthz")

    if error:
        print_error(f"Server health check failed: {error}")
        return False

    if response.status_code == 200:
        print_success("Server is running")
        try:
            data = response.json()
            print(f"   Status: {data.get('status', 'unknown')}")
            return True
        except:
            return True
    else:
        print_error(f"Server returned {response.status_code}")
        return False


def test_existing_endpoints():
    """Test some existing endpoints to ensure we didn't break anything."""
    print_header("TESTING: Existing Endpoints (Regression)")

    results = []

    # Test root
    results.append(test_endpoint("GET / (API Root)", "GET", "/"))

    # Test docs
    results.append(
        test_endpoint("GET /api/docs (Swagger)", "GET", "/api/docs", expected_status=200)
    )

    passed = sum(results)
    total = len(results)
    print(f"\nExisting Endpoints: {passed}/{total} passed")
    return passed, total


def print_summary(
    gap_passed,
    gap_total,
    reminder_passed,
    reminder_total,
    policy_passed,
    policy_total,
    existing_passed,
    existing_total,
):
    """Print final summary."""
    print_header("TEST SUMMARY")

    total_passed = gap_passed + reminder_passed + policy_passed + existing_passed
    total_tests = gap_total + reminder_total + policy_total + existing_total

    print(
        f"""
{Colors.BLUE}Gap Analysis:{Colors.END}      {gap_passed}/{gap_total} passed
{Colors.BLUE}Reminders:{Colors.END}         {reminder_passed}/{reminder_total} passed
{Colors.BLUE}Policy Generator:{Colors.END}  {policy_passed}/{policy_total} passed
{Colors.BLUE}Existing APIs:{Colors.END}     {existing_passed}/{existing_total} passed

{Colors.GREEN if total_passed == total_tests else Colors.YELLOW}
TOTAL: {total_passed}/{total_tests} tests passed ({total_passed/total_tests*100:.1f}%)
{Colors.END}
"""
    )

    if total_passed == total_tests:
        print_success("All tests passed! 🎉")
        print("\nNext steps:")
        print("  1. Test authentication with a real token")
        print("  2. Try POST endpoints with real data")
        print("  3. Check Swagger UI at http://localhost:8000/api/docs")
    else:
        print_warning("Some tests failed or require authentication")
        print("\nTroubleshooting:")
        print("  1. Is the server running? (uvicorn src.main:app --reload)")
        print("  2. Check logs for errors")
        print("  3. Some endpoints require authentication - that's OK")


def main():
    print_header("Yufeed API Endpoint Testing")
    print(f"Base URL: {BASE_URL}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Check server health first
    if not test_server_health():
        print_error("\nServer is not running. Please start it first:")
        print("  cd apps/api && uvicorn src.main:app --reload")
        sys.exit(1)

    # Run all tests
    gap_passed, gap_total = test_gap_analysis_endpoints()
    reminder_passed, reminder_total = test_reminder_endpoints()
    policy_passed, policy_total = test_policy_generator_endpoints()
    existing_passed, existing_total = test_existing_endpoints()

    # Print summary
    print_summary(
        gap_passed,
        gap_total,
        reminder_passed,
        reminder_total,
        policy_passed,
        policy_total,
        existing_passed,
        existing_total,
    )


if __name__ == "__main__":
    main()
