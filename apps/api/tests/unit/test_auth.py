"""
Unit tests for authentication endpoints.
"""
import pytest
from fastapi.testclient import TestClient


@pytest.mark.unit
class TestAuthRegistration:
    """Test user registration endpoint."""

    def test_register_success(self, client: TestClient):
        """Test successful user registration."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "SecurePassword123!",
                "full_name": "New User"
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_register_duplicate_email(self, client: TestClient):
        """Test registration with duplicate email fails."""
        # First registration
        client.post(
            "/api/auth/register",
            json={
                "email": "duplicate@example.com",
                "password": "SecurePassword123!",
                "full_name": "First User"
            }
        )

        # Second registration with same email
        response = client.post(
            "/api/auth/register",
            json={
                "email": "duplicate@example.com",
                "password": "AnotherPassword123!",
                "full_name": "Second User"
            }
        )

        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()

    def test_register_weak_password(self, client: TestClient):
        """Test registration with weak password fails."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "weakpass@example.com",
                "password": "123",
                "full_name": "Weak Password User"
            }
        )

        assert response.status_code == 422

    def test_register_invalid_email(self, client: TestClient):
        """Test registration with invalid email fails."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "not-an-email",
                "password": "SecurePassword123!",
                "full_name": "Invalid Email User"
            }
        )

        assert response.status_code == 422


@pytest.mark.unit
class TestAuthLogin:
    """Test user login endpoint."""

    def test_login_success(self, client: TestClient, ensure_tenant_membership):
        """Test successful login."""
        # Register user first
        client.post(
            "/api/auth/register",
            json={
                "email": "logintest@example.com",
                "password": "TestPassword123!",
                "full_name": "Login Test"
            }
        )
        ensure_tenant_membership("logintest@example.com", role="viewer", tenant_id="default")

        # Login
        response = client.post(
            "/api/auth/login",
            json={
                "email": "logintest@example.com",
                "password": "TestPassword123!",
                "tenant_id": "default",
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client: TestClient):
        """Test login with wrong password fails."""
        # Register user first
        client.post(
            "/api/auth/register",
            json={
                "email": "wrongpass@example.com",
                "password": "CorrectPassword123!",
                "full_name": "Wrong Pass User"
            }
        )

        # Login with wrong password
        response = client.post(
            "/api/auth/login",
            json={
                "email": "wrongpass@example.com",
                "password": "WrongPassword123!"
            }
        )

        assert response.status_code == 401
        assert "incorrect" in response.json()["detail"].lower()

    def test_login_nonexistent_user(self, client: TestClient):
        """Test login with nonexistent user fails."""
        response = client.post(
            "/api/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "SomePassword123!"
            }
        )

        assert response.status_code == 401


@pytest.mark.unit
class TestAuthToken:
    """Test token refresh endpoint."""

    def test_refresh_token_success(self, client: TestClient, ensure_tenant_membership):
        """Test successful token refresh."""
        # Register and get tokens
        client.post(
            "/api/auth/register",
            json={
                "email": "refresh@example.com",
                "password": "TestPassword123!",
                "full_name": "Refresh Test"
            }
        )
        ensure_tenant_membership("refresh@example.com", role="viewer", tenant_id="default")

        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "refresh@example.com",
                "password": "TestPassword123!",
                "tenant_id": "default",
            }
        )
        refresh_token = login_response.json()["refresh_token"]

        # Refresh token
        response = client.post(
            "/api/auth/refresh",
            json={"refresh_token": refresh_token}
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    def test_refresh_with_invalid_token(self, client: TestClient):
        """Test refresh with invalid token fails."""
        response = client.post(
            "/api/auth/refresh",
            json={"refresh_token": "invalid.token.here"}
        )

        assert response.status_code == 401

    def test_refresh_with_access_token(self, client: TestClient, ensure_tenant_membership):
        """Test refresh with access token (instead of refresh token) fails."""
        # Register and get tokens
        client.post(
            "/api/auth/register",
            json={
                "email": "wrongtoken@example.com",
                "password": "TestPassword123!",
                "full_name": "Wrong Token Test"
            }
        )
        ensure_tenant_membership("wrongtoken@example.com", role="viewer", tenant_id="default")

        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "wrongtoken@example.com",
                "password": "TestPassword123!",
                "tenant_id": "default",
            }
        )
        access_token = login_response.json()["access_token"]

        # Try to refresh with access token
        response = client.post(
            "/api/auth/refresh",
            json={"refresh_token": access_token}
        )

        assert response.status_code == 401


@pytest.mark.unit
class TestAuthProtectedEndpoints:
    """Test authentication requirement for protected endpoints."""

    def test_protected_endpoint_without_token(self, client: TestClient):
        """Test accessing protected endpoint without token fails."""
        response = client.get("/api/alerts")

        assert response.status_code == 401

    def test_protected_endpoint_with_invalid_token(self, client: TestClient):
        """Test accessing protected endpoint with invalid token fails."""
        response = client.get(
            "/api/alerts",
            headers={"Authorization": "Bearer invalid.token.here"}
        )

        assert response.status_code == 401

    def test_protected_endpoint_with_valid_token(self, client: TestClient, auth_headers: dict):
        """Test accessing protected endpoint with valid token succeeds."""
        response = client.get("/api/alerts", headers=auth_headers)

        # Should not be 401 (authentication error)
        assert response.status_code != 401
