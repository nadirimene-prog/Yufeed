"""
Tests for API versioning.

Verifies that:
- /api/* endpoints work (backward compatibility)
- /api/v1/* endpoints work (explicit version)
- Both paths return identical responses
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


def test_v1_endpoint_works(client: TestClient):
    """Test that /api/v1/* endpoints work."""
    response = client.get("/api/v1/tenants")

    # Should return 200 or 401 (depending on auth), not 404
    assert response.status_code in [200, 401, 403]


def test_unversioned_and_v1_return_same_response(client: TestClient, auth_headers):
    """Test that /api/* and /api/v1/* return identical responses."""
    # Test with a simple endpoint
    unversioned_response = client.get("/api/health", headers=auth_headers)
    v1_response = client.get("/api/v1/health", headers=auth_headers)

    assert unversioned_response.status_code == v1_response.status_code

    # If both succeed, responses should be identical
    if unversioned_response.status_code == 200:
        assert unversioned_response.json() == v1_response.json()


def test_openapi_schema_includes_versions(client: TestClient):
    """Test that OpenAPI schema documents versioned endpoints."""
    response = client.get("/api/openapi.json")

    assert response.status_code == 200
    schema = response.json()

    # Check that paths include both /api and /api/v1 prefixes
    paths = schema.get("paths", {})

    # Should have at least some /api/ paths
    api_paths = [p for p in paths if p.startswith("/api/") and not p.startswith("/api/v1")]
    assert len(api_paths) > 0, "No /api/ paths found"

    # Should have at least some /api/v1/ paths
    v1_paths = [p for p in paths if p.startswith("/api/v1/")]
    assert len(v1_paths) > 0, "No /api/v1/ paths found"


@pytest.mark.parametrize(
    "endpoint",
    [
        "/api/transactions",
        "/api/alerts",
        "/api/cases",
        "/api/monitoring_rules",
        "/api/compliance/obligations",
    ],
)
def test_critical_endpoints_available_in_both_versions(client: TestClient, endpoint: str):
    """Test that critical endpoints are available at both /api and /api/v1."""
    unversioned = client.get(endpoint)
    versioned = client.get(endpoint.replace("/api/", "/api/v1/", 1))

    # Both should exist (not 404)
    assert unversioned.status_code != 404, f"{endpoint} not found"
    assert versioned.status_code != 404, f"{endpoint.replace('/api/', '/api/v1/', 1)} not found"

    # Both should return same status code
    assert unversioned.status_code == versioned.status_code
