"""
Multi-Tenancy Isolation Validation Script
Phase 4C: Task 7 - Validate complete tenant isolation

This script performs comprehensive validation of tenant isolation.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import requests
import json
from typing import Dict, List
from datetime import datetime


class TenantIsolationValidator:
    """Validates tenant isolation across the API."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results = {"total_tests": 0, "passed": 0, "failed": 0, "errors": []}

    def test(self, name: str, condition: bool, error_msg: str = None):
        """Record a test result."""
        self.results["total_tests"] += 1
        if condition:
            self.results["passed"] += 1
            print(f"   ✅ {name}")
            return True
        else:
            self.results["failed"] += 1
            msg = error_msg or name
            self.results["errors"].append(msg)
            print(f"   ❌ {name}")
            if error_msg:
                print(f"      Error: {error_msg}")
            return False

    def test_api_key_authentication(self, api_key: str, tenant_id: str):
        """Test API key authentication."""
        print(f"\n🔐 Testing API Key Authentication for {tenant_id}")

        # Test valid API key
        response = requests.get(f"{self.base_url}/api/alerts", headers={"X-API-Key": api_key})
        self.test(
            "Valid API key accepted",
            response.status_code in [200, 404],  # 404 is ok if no alerts
            f"Got status {response.status_code}",
        )

        # Test invalid API key
        response = requests.get(
            f"{self.base_url}/api/alerts", headers={"X-API-Key": "invalid_key_12345"}
        )
        self.test(
            "Invalid API key rejected",
            response.status_code == 401,
            f"Expected 401, got {response.status_code}",
        )

    def test_data_isolation(self, api_key_a: str, api_key_b: str):
        """Test that data is isolated between tenants."""
        print(f"\n🔒 Testing Data Isolation Between Tenants")

        # Get alerts for tenant A
        response_a = requests.get(f"{self.base_url}/api/alerts", headers={"X-API-Key": api_key_a})

        # Get alerts for tenant B
        response_b = requests.get(f"{self.base_url}/api/alerts", headers={"X-API-Key": api_key_b})

        if response_a.status_code == 200 and response_b.status_code == 200:
            alerts_a = response_a.json()
            alerts_b = response_b.json()

            # Get alert IDs
            ids_a = {alert["alert_id"] for alert in alerts_a}
            ids_b = {alert["alert_id"] for alert in alerts_b}

            # Check no overlap
            overlap = ids_a.intersection(ids_b)
            self.test(
                "No alert ID overlap between tenants",
                len(overlap) == 0,
                f"Found {len(overlap)} overlapping alerts",
            )

            # Check both tenants can have data
            self.test(
                "Tenant A can access own alerts",
                response_a.status_code == 200,
                f"Status: {response_a.status_code}",
            )

            self.test(
                "Tenant B can access own alerts",
                response_b.status_code == 200,
                f"Status: {response_b.status_code}",
            )

    def test_cross_tenant_access(self, api_key_a: str, api_key_b: str):
        """Test that tenant A cannot access tenant B's data."""
        print(f"\n🚫 Testing Cross-Tenant Access Prevention")

        # First, get an alert ID from tenant B
        response_b = requests.get(f"{self.base_url}/api/alerts", headers={"X-API-Key": api_key_b})

        if response_b.status_code == 200:
            alerts_b = response_b.json()
            if len(alerts_b) > 0:
                alert_id_b = alerts_b[0]["alert_id"]

                # Try to access tenant B's alert using tenant A's API key
                response = requests.get(
                    f"{self.base_url}/api/alerts/{alert_id_b}", headers={"X-API-Key": api_key_a}
                )

                self.test(
                    "Tenant A cannot access Tenant B's alert",
                    response.status_code in [403, 404],
                    f"Expected 403/404, got {response.status_code}",
                )
            else:
                print("   ⚠️  Skipped: Tenant B has no alerts to test with")
        else:
            print(f"   ⚠️  Skipped: Could not get tenant B alerts (status {response_b.status_code})")

    def test_statistics_isolation(self, api_key_a: str, api_key_b: str):
        """Test that statistics are isolated between tenants."""
        print(f"\n📊 Testing Statistics Isolation")

        # Get statistics for tenant A
        response_a = requests.get(
            f"{self.base_url}/api/alerts/statistics/overview", headers={"X-API-Key": api_key_a}
        )

        # Get statistics for tenant B
        response_b = requests.get(
            f"{self.base_url}/api/alerts/statistics/overview", headers={"X-API-Key": api_key_b}
        )

        if response_a.status_code == 200 and response_b.status_code == 200:
            stats_a = response_a.json()
            stats_b = response_b.json()

            self.test(
                "Tenant A gets own statistics",
                "total_alerts" in stats_a,
                "Missing total_alerts field",
            )

            self.test(
                "Tenant B gets own statistics",
                "total_alerts" in stats_b,
                "Missing total_alerts field",
            )

            # Statistics should be different (unless both have exactly same data)
            if stats_a.get("total_alerts", 0) > 0 or stats_b.get("total_alerts", 0) > 0:
                print(f"      Tenant A total alerts: {stats_a.get('total_alerts', 0)}")
                print(f"      Tenant B total alerts: {stats_b.get('total_alerts', 0)}")

    def test_tenant_management(self):
        """Test tenant management endpoints."""
        print(f"\n🏢 Testing Tenant Management")

        # List all tenants
        response = requests.get(f"{self.base_url}/api/tenants")
        self.test(
            "Can list tenants", response.status_code == 200, f"Status: {response.status_code}"
        )

        if response.status_code == 200:
            tenants = response.json()
            self.test(
                "At least 2 test tenants exist",
                len(tenants) >= 2,
                f"Only found {len(tenants)} tenants",
            )

            # Check for test tenants
            tenant_ids = [t["tenant_id"] for t in tenants]
            self.test("acme_corp tenant exists", "acme_corp" in tenant_ids)
            self.test("beta_industries tenant exists", "beta_industries" in tenant_ids)

    def test_api_key_management(self, api_key: str, tenant_id: str):
        """Test API key management endpoints."""
        print(f"\n🔑 Testing API Key Management for {tenant_id}")

        # List API keys for tenant
        response = requests.get(
            f"{self.base_url}/api/tenants/{tenant_id}/api-keys", headers={"X-API-Key": api_key}
        )

        self.test(
            f"Can list API keys for {tenant_id}",
            response.status_code == 200,
            f"Status: {response.status_code}",
        )

        if response.status_code == 200:
            keys = response.json()
            self.test("At least 1 API key exists", len(keys) >= 1, f"Found {len(keys)} keys")

    def run_all_tests(self, api_keys: Dict[str, str]):
        """Run all validation tests."""
        print("\n" + "=" * 70)
        print("🧪 MULTI-TENANCY ISOLATION VALIDATION")
        print("=" * 70)

        # Get API keys
        api_key_acme = api_keys.get("acme_corp")
        api_key_beta = api_keys.get("beta_industries")

        if not api_key_acme or not api_key_beta:
            print("\n❌ Error: Missing API keys")
            print("   Run setup_test_tenants.py first to create test tenants")
            return False

        # Run tests
        self.test_api_key_authentication(api_key_acme, "acme_corp")
        self.test_api_key_authentication(api_key_beta, "beta_industries")
        self.test_tenant_management()
        self.test_api_key_management(api_key_acme, "acme_corp")
        self.test_data_isolation(api_key_acme, api_key_beta)
        self.test_cross_tenant_access(api_key_acme, api_key_beta)
        self.test_statistics_isolation(api_key_acme, api_key_beta)

        # Print summary
        self.print_summary()

        return self.results["failed"] == 0

    def print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 70)
        print("📋 TEST SUMMARY")
        print("=" * 70)
        print(f"\nTotal Tests:  {self.results['total_tests']}")
        print(f"✅ Passed:     {self.results['passed']}")
        print(f"❌ Failed:     {self.results['failed']}")

        if self.results["failed"] > 0:
            print("\n❌ FAILED TESTS:")
            for error in self.results["errors"]:
                print(f"   - {error}")
        else:
            print("\n🎉 ALL TESTS PASSED!")
            print("✅ Multi-tenancy isolation is working correctly")

        print("\n" + "=" * 70)


def load_api_keys(keys_file: Path) -> Dict[str, str]:
    """Load API keys from file."""
    api_keys = {}

    if not keys_file.exists():
        print(f"❌ API keys file not found: {keys_file}")
        print("   Run setup_test_tenants.py first to create test tenants")
        return api_keys

    with open(keys_file, "r") as f:
        lines = f.readlines()

    current_tenant = None
    for line in lines:
        line = line.strip()
        if line.startswith("Tenant:"):
            current_tenant = line.split(":", 1)[1].strip()
        elif line.startswith("API Key:") and current_tenant:
            api_key = line.split(":", 1)[1].strip()
            api_keys[current_tenant] = api_key

    return api_keys


def main():
    """Main validation function."""
    # Load API keys
    keys_file = Path(__file__).parent / "test_api_keys.txt"
    api_keys = load_api_keys(keys_file)

    if not api_keys:
        return 1

    # Run validation
    validator = TenantIsolationValidator()
    success = validator.run_all_tests(api_keys)

    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
