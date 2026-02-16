"""
Tests for API versioning.

Verifies that:
- /api/* endpoints work (backward compatibility)
- API root documents versioning strategy

Note: /api/v1/* endpoints are reserved for future use and currently return 404.
The infrastructure supports adding v1 endpoints when breaking changes are needed.
"""

import pytest
from fastapi.testclient import TestClient


def test_api_root_shows_versions(client: TestClient):
    """Test that API root shows available versions."""
    response = client.get("/")

    assert response.status_code == 200
    data = response.json()

    assert "api_versions" in data
    assert "current" in data["api_versions"]
    assert "v1" in data["api_versions"]
    assert data["api_versions"]["current"]["path"] == "/api"
    assert data["api_versions"]["v1"]["path"] == "/api/v1"


def test_unversioned_endpoint_works(client: TestClient):
    """Test that unversioned /api/* endpoints still work (backward compatibility)."""
    response = client.get("/api/tenants")

    # Should return 200 or 401 (depending on auth), not 404
    assert response.status_code in [200, 401, 403]


def test_v1_endpoint_documented(client: TestClient):
    """Test that /api/v1/* endpoints are reserved (return 404 until implemented)."""
    response = client.get("/api/v1/tenants")

    # v1 endpoints are reserved for future use - currently return 404
    # This test documents that v1 paths are not yet implemented
    assert response.status_code == 404


def test_unversioned_and_v1_documented(client: TestClient):
    """Test that /api/* works and /api/v1/* is reserved for future use."""
    # Test with the health endpoint (no auth required)
    unversioned_response = client.get("/healthz")
    v1_response = client.get("/api/v1/healthz")

    # /healthz should work (200)
    assert unversioned_response.status_code == 200
    # /api/v1/healthz is reserved for future use (404)
    assert v1_response.status_code == 404


def test_openapi_schema_includes_api_paths(client: TestClient):
    """Test that OpenAPI schema documents API endpoints."""
    response = client.get("/api/openapi.json")

    assert response.status_code == 200
    schema = response.json()

    # Check that paths include /api/ paths
    paths = schema.get("paths", {})

    # Should have at least some /api/ paths
    api_paths = [p for p in paths if p.startswith("/api/")]
    assert len(api_paths) > 0, "No /api/ paths found"

    # Note: v1 paths are reserved for future use and not currently included


@pytest.mark.parametrize(
    "endpoint",
    [
        "/api/transactions",
        "/api/alerts",
        "/api/cases",
        "/api/monitoring-rules",  # Note: hyphen, not underscore
        "/api/obligations",  # Note: no /compliance/ prefix
    ],
)
def test_critical_endpoints_available(client: TestClient, endpoint: str):
    """Test that critical endpoints are available at /api/* paths."""
    response = client.get(endpoint)

    # Should exist (not 404) - may return 401/403 depending on auth
    assert response.status_code != 404, f"{endpoint} not found"
