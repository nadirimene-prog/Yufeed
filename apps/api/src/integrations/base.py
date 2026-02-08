"""
Base Integration Class

Foundation for all external service integrations.
Provides common functionality for:
- Connection management
- Error handling
- Rate limiting
- Caching
- Audit logging
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


def utc_now() -> datetime:
    """Return current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


from typing import Any, Dict, List, Optional
import logging
import asyncio
import hashlib
import json

logger = logging.getLogger(__name__)


class IntegrationStatus(str, Enum):
    """Status of an integration operation."""

    SUCCESS = "success"
    PARTIAL = "partial"
    ERROR = "error"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"
    UNAVAILABLE = "unavailable"


@dataclass
class IntegrationResult:
    """Result from an integration operation."""

    status: IntegrationStatus
    data: Any = None
    error_message: Optional[str] = None
    processing_time_ms: int = 0
    cached: bool = False
    source: str = ""
    timestamp: datetime = field(default_factory=utc_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "data": self.data,
            "error_message": self.error_message,
            "processing_time_ms": self.processing_time_ms,
            "cached": self.cached,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
        }


class BaseIntegration(ABC):
    """
    Abstract base class for external integrations.

    Provides:
    - Connection management
    - Rate limiting
    - Caching
    - Error handling
    - Audit logging
    """

    def __init__(
        self,
        name: str,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout_seconds: int = 30,
        max_retries: int = 3,
        cache_ttl_seconds: int = 3600,
        rate_limit_per_minute: int = 60,
    ):
        self.name = name
        self.base_url = base_url
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.cache_ttl_seconds = cache_ttl_seconds
        self.rate_limit_per_minute = rate_limit_per_minute

        # Internal state
        self._cache: Dict[str, tuple[Any, datetime]] = {}
        self._request_times: List[datetime] = []
        self._initialized = False

        logger.info(f"Initialized {name} integration")

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the integration is available."""
        pass

    @abstractmethod
    async def _execute(self, **kwargs) -> IntegrationResult:
        """Execute the integration operation."""
        pass

    async def execute(self, **kwargs) -> IntegrationResult:
        """
        Execute with rate limiting, caching, and error handling.
        """
        import time

        start_time = time.time()

        # Check cache
        cache_key = self._get_cache_key(**kwargs)
        cached_result = self._check_cache(cache_key)
        if cached_result:
            cached_result.cached = True
            cached_result.processing_time_ms = int((time.time() - start_time) * 1000)
            return cached_result

        # Check rate limit
        if not self._check_rate_limit():
            return IntegrationResult(
                status=IntegrationStatus.RATE_LIMITED,
                error_message=f"Rate limit exceeded for {self.name}",
                source=self.name,
            )

        # Execute with retries
        last_error = None
        for attempt in range(self.max_retries):
            try:
                result = await asyncio.wait_for(
                    self._execute(**kwargs), timeout=self.timeout_seconds
                )

                # Cache successful results
                if result.status == IntegrationStatus.SUCCESS:
                    self._set_cache(cache_key, result)

                result.processing_time_ms = int((time.time() - start_time) * 1000)
                result.source = self.name
                return result

            except asyncio.TimeoutError:
                last_error = "Request timed out"
                logger.warning(f"{self.name} timeout on attempt {attempt + 1}")

            except Exception as e:
                last_error = str(e)
                logger.warning(f"{self.name} error on attempt {attempt + 1}: {e}")

            # Wait before retry
            if attempt < self.max_retries - 1:
                await asyncio.sleep(2**attempt)  # Exponential backoff

        return IntegrationResult(
            status=IntegrationStatus.ERROR,
            error_message=last_error,
            processing_time_ms=int((time.time() - start_time) * 1000),
            source=self.name,
        )

    def _get_cache_key(self, **kwargs) -> str:
        """Generate a cache key from kwargs."""
        data = json.dumps(kwargs, sort_keys=True, default=str)
        return hashlib.sha256(data.encode()).hexdigest()

    def _check_cache(self, key: str) -> Optional[IntegrationResult]:
        """Check if a cached result exists and is valid."""
        if key in self._cache:
            result, cached_at = self._cache[key]
            age_seconds = (utc_now() - cached_at).total_seconds()
            if age_seconds < self.cache_ttl_seconds:
                return result
            else:
                del self._cache[key]
        return None

    def _set_cache(self, key: str, result: IntegrationResult) -> None:
        """Cache a result."""
        self._cache[key] = (result, utc_now())

    def _check_rate_limit(self) -> bool:
        """Check if we're within rate limits."""
        now = utc_now()

        # Remove old request times
        one_minute_ago = now.timestamp() - 60
        self._request_times = [t for t in self._request_times if t.timestamp() > one_minute_ago]

        # Check limit
        if len(self._request_times) >= self.rate_limit_per_minute:
            return False

        # Record this request
        self._request_times.append(now)
        return True

    def clear_cache(self) -> None:
        """Clear the cache."""
        self._cache.clear()
        logger.info(f"Cleared cache for {self.name}")
