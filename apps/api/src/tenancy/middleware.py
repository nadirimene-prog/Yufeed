"""
Tenant Middleware
Phase 4C: Task 7.2 & 7.4 - Multi-Tenancy Middleware

FastAPI middleware that extracts tenant from request and sets it in context.

Tenant extraction order:
1. API Key header (X-API-Key: yk_live_<tenant_id>_<random>)
2. JWT token (tenant_id claim)
3. Custom header (X-Tenant-ID)
4. Query parameter (?tenant_id=xxx)
"""
import logging
import hashlib
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import Optional
from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from src.tenancy.context import set_current_tenant, clear_current_tenant
from src.database import SessionLocal
from src.models.tenant_models import TenantAPIKey, Tenant

# Thread pool for running sync DB operations without blocking the event loop
_db_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="tenant_db_")

logger = logging.getLogger(__name__)


class TenantMiddleware(BaseHTTPMiddleware):
    """
    Middleware to extract and set tenant context for each request.

    Ensures all database queries are automatically filtered by tenant.
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        """
        Process request and set tenant context.

        Args:
            request: FastAPI request
            call_next: Next middleware/handler in chain

        Returns:
            Response from the application
        """
        tenant_id = None

        try:
            # Extract tenant from various sources
            tenant_id = await self._extract_tenant_from_request(request)

            if tenant_id:
                # Validate tenant exists and is active
                if await self._validate_tenant(tenant_id):
                    set_current_tenant(tenant_id)
                    logger.debug(f"Request tenant: {tenant_id}")
                else:
                    logger.warning(f"Invalid or inactive tenant: {tenant_id}")
                    raise HTTPException(status_code=403, detail="Invalid tenant")
            else:
                # No tenant found - check if endpoint requires tenant
                if self._requires_tenant(request):
                    raise HTTPException(
                        status_code=401,
                        detail="No tenant context found. Provide X-API-Key or X-Tenant-ID header."
                    )

            # Process request
            response = await call_next(request)
            return response

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Tenant middleware error: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Internal server error")
        finally:
            # Always clear context after request
            clear_current_tenant()

    async def _extract_tenant_from_request(self, request: Request) -> Optional[str]:
        """
        Extract tenant ID from request.

        Priority order:
        1. API Key (X-API-Key header)
        2. JWT token (if present)
        3. X-Tenant-ID header
        4. Query parameter

        Returns:
            Tenant ID or None
        """
        # 1. Try API Key
        api_key = request.headers.get("X-API-Key") or request.headers.get("Authorization", "").replace("Bearer ", "")

        if api_key and api_key.startswith("yk_"):
            tenant_id = await self._extract_tenant_from_api_key(api_key)
            if tenant_id:
                return tenant_id

        # 2. Try JWT token
        # TODO: Extract from JWT when auth is fully implemented
        # auth_header = request.headers.get("Authorization")
        # if auth_header and auth_header.startswith("Bearer "):
        #     token = auth_header[7:]
        #     tenant_id = extract_tenant_from_jwt(token)
        #     if tenant_id:
        #         return tenant_id

        # 3. Try X-Tenant-ID header
        tenant_id = request.headers.get("X-Tenant-ID")
        if tenant_id:
            return tenant_id

        # 4. Try query parameter (for development/testing only)
        tenant_id = request.query_params.get("tenant_id")
        if tenant_id:
            logger.warning("Using tenant_id from query parameter (development only)")
            return tenant_id

        # 5. Default tenant for backward compatibility
        # In production, this should be removed
        return "default"

    async def _extract_tenant_from_api_key(self, api_key: str) -> Optional[str]:
        """
        Extract and validate tenant from API key.

        API Key format: yk_live_<tenant_id>_<random>
        Example: yk_live_acme_corp_a1b2c3d4e5f6

        Args:
            api_key: API key string

        Returns:
            Tenant ID if valid, None otherwise
        """
        try:
            # Parse API key format
            parts = api_key.split("_")

            if len(parts) < 4 or parts[0] != "yk":
                return None

            # Run sync DB operation in thread pool to avoid blocking event loop
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                _db_executor,
                partial(self._validate_api_key_sync, api_key)
            )

        except Exception as e:
            logger.error(f"Error extracting tenant from API key: {e}")

        return None

    def _validate_api_key_sync(self, api_key: str) -> Optional[str]:
        """Sync helper to validate API key in database."""
        db = SessionLocal()
        try:
            # Hash the API key for lookup
            key_hash = hashlib.sha256(api_key.encode()).hexdigest()

            api_key_record = db.query(TenantAPIKey).filter(
                TenantAPIKey.key_hash == key_hash,
                TenantAPIKey.is_active == True,
            ).first()

            if not api_key_record:
                logger.warning(f"Invalid API key: {api_key[:20]}...")
                return None

            # Update last used
            from datetime import datetime, timezone
            api_key_record.last_used_at = datetime.now(timezone.utc)
            api_key_record.usage_count = (api_key_record.usage_count or 0) + 1
            db.commit()

            # Get tenant_id from the key record
            tenant = db.query(Tenant).filter(Tenant.id == api_key_record.tenant_id).first()
            if tenant:
                return tenant.tenant_id

        finally:
            db.close()

        return None

    async def _validate_tenant(self, tenant_id: str) -> bool:
        """
        Validate that tenant exists and is active.

        Args:
            tenant_id: Tenant identifier

        Returns:
            True if tenant is valid and active
        """
        if os.getenv("ENVIRONMENT", "").lower() in {"test", "testing"}:
            return True

        # Run sync DB operation in thread pool to avoid blocking event loop
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _db_executor,
            partial(self._validate_tenant_sync, tenant_id)
        )

    def _validate_tenant_sync(self, tenant_id: str) -> bool:
        """Sync helper to validate tenant in database."""
        db = SessionLocal()
        try:
            tenant = db.query(Tenant).filter(
                Tenant.tenant_id == tenant_id,
                Tenant.is_active == True,
            ).first()

            return tenant is not None
        finally:
            db.close()

    def _requires_tenant(self, request: Request) -> bool:
        """
        Check if the endpoint requires tenant context.

        Paths that don't require tenant:
        - /docs, /openapi.json (documentation)
        - /health, /metrics (monitoring)
        - /auth/login (authentication)

        Args:
            request: FastAPI request

        Returns:
            True if endpoint requires tenant
        """
        exempt_paths = [
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health",
            "/metrics",
            "/auth/login",
            "/auth/register",
        ]

        path = request.url.path

        # Check if path starts with any exempt path
        for exempt in exempt_paths:
            if path.startswith(exempt):
                return False

        return True
