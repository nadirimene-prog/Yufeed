"""
Redis cache manager with TTL support and cache-aside pattern.
Phase 4A: Task 3.1 & 3.2 - Redis Cache Infrastructure
"""

import json
import hashlib
import logging
from typing import Any, Optional, Callable, Union
from functools import wraps
from datetime import timedelta
import redis
from redis.exceptions import RedisError

from src.config import settings
from src.monitoring.metrics import record_cache_hit, record_cache_miss

logger = logging.getLogger(__name__)


class CacheManager:
    """
    Redis cache manager implementing cache-aside pattern with TTL support.

    Features:
    - Automatic serialization/deserialization
    - TTL (Time To Live) support
    - Key versioning for cache invalidation
    - Namespace support for logical separation
    - Error handling with fallback
    - Metrics integration
    """

    def __init__(self, redis_url: Optional[str] = None, default_ttl: int = 300):
        """
        Initialize cache manager.

        Args:
            redis_url: Redis connection URL (default: from settings)
            default_ttl: Default TTL in seconds (default: 5 minutes)
        """
        self.redis_url = redis_url or getattr(settings, "REDIS_URL", "redis://localhost:6379/0")
        self.default_ttl = default_ttl
        self._client: Optional[redis.Redis] = None
        self.enabled = True
        self.key_version = "v1"  # Increment to invalidate all cached keys

    @property
    def client(self) -> redis.Redis:
        """
        Lazy initialization of Redis client.
        """
        if self._client is None:
            try:
                self._client = redis.from_url(
                    self.redis_url,
                    decode_responses=True,
                    socket_connect_timeout=2,
                    socket_timeout=2,
                    retry_on_timeout=True,
                    health_check_interval=30,
                )
                # Test connection
                self._client.ping()
                logger.info("Redis cache connected successfully")
            except RedisError as e:
                logger.warning(f"Redis connection failed: {e}. Caching disabled.")
                self.enabled = False
                # Return a mock client that does nothing
                self._client = redis.from_url("redis://localhost:6379/0", decode_responses=True)

        return self._client

    def _make_key(self, namespace: str, key: str) -> str:
        """
        Create a versioned cache key with namespace.

        Args:
            namespace: Logical namespace (e.g., 'user_profile', 'rules')
            key: Unique key within namespace

        Returns:
            Fully qualified cache key
        """
        return f"yufeed:{self.key_version}:{namespace}:{key}"

    def get(self, namespace: str, key: str, cache_type: str = "general") -> Optional[Any]:
        """
        Get value from cache.

        Args:
            namespace: Cache namespace
            key: Cache key
            cache_type: Type of cache for metrics (e.g., 'user_profile', 'rules')

        Returns:
            Cached value or None if not found
        """
        if not self.enabled:
            record_cache_miss(cache_type)
            return None

        try:
            cache_key = self._make_key(namespace, key)
            value = self.client.get(cache_key)

            if value is not None:
                record_cache_hit(cache_type)
                logger.debug(f"Cache hit: {cache_key}")
                return json.loads(value)
            else:
                record_cache_miss(cache_type)
                logger.debug(f"Cache miss: {cache_key}")
                return None

        except (RedisError, json.JSONDecodeError) as e:
            logger.warning(f"Cache get error: {e}")
            record_cache_miss(cache_type)
            return None

    def set(
        self,
        namespace: str,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        cache_type: str = "general",
    ) -> bool:
        """
        Set value in cache with TTL.

        Args:
            namespace: Cache namespace
            key: Cache key
            value: Value to cache (must be JSON serializable)
            ttl: Time to live in seconds (default: self.default_ttl)
            cache_type: Type of cache for metrics

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            return False

        try:
            cache_key = self._make_key(namespace, key)
            serialized = json.dumps(value, default=str)
            ttl = ttl or self.default_ttl

            self.client.setex(cache_key, ttl, serialized)
            logger.debug(f"Cache set: {cache_key} (TTL: {ttl}s)")
            return True

        except (RedisError, TypeError, ValueError) as e:
            logger.warning(f"Cache set error: {e}")
            return False

    def delete(self, namespace: str, key: str) -> bool:
        """
        Delete value from cache.

        Args:
            namespace: Cache namespace
            key: Cache key

        Returns:
            True if key was deleted, False otherwise
        """
        if not self.enabled:
            return False

        try:
            cache_key = self._make_key(namespace, key)
            result = self.client.delete(cache_key)
            logger.debug(f"Cache delete: {cache_key}")
            return result > 0

        except RedisError as e:
            logger.warning(f"Cache delete error: {e}")
            return False

    def delete_pattern(self, namespace: str, pattern: str) -> int:
        """
        Delete all keys matching a pattern within namespace.

        Args:
            namespace: Cache namespace
            pattern: Pattern to match (e.g., 'user:*')

        Returns:
            Number of keys deleted
        """
        if not self.enabled:
            return 0

        try:
            cache_pattern = self._make_key(namespace, pattern)
            keys = self.client.keys(cache_pattern)

            if keys:
                deleted = self.client.delete(*keys)
                logger.info(f"Cache pattern delete: {cache_pattern} ({deleted} keys)")
                return deleted

            return 0

        except RedisError as e:
            logger.warning(f"Cache pattern delete error: {e}")
            return 0

    def clear_namespace(self, namespace: str) -> int:
        """
        Clear all keys in a namespace.

        Args:
            namespace: Cache namespace to clear

        Returns:
            Number of keys deleted
        """
        return self.delete_pattern(namespace, "*")

    def increment(
        self, namespace: str, key: str, amount: int = 1, ttl: Optional[int] = None
    ) -> Optional[int]:
        """
        Increment a counter in cache.

        Args:
            namespace: Cache namespace
            key: Cache key
            amount: Amount to increment by
            ttl: TTL for the key if it doesn't exist

        Returns:
            New value after increment, or None on error
        """
        if not self.enabled:
            return None

        try:
            cache_key = self._make_key(namespace, key)
            new_value = self.client.incrby(cache_key, amount)

            # Set TTL only if key is new
            if new_value == amount and ttl:
                self.client.expire(cache_key, ttl)

            return new_value

        except RedisError as e:
            logger.warning(f"Cache increment error: {e}")
            return None

    def get_ttl(self, namespace: str, key: str) -> Optional[int]:
        """
        Get remaining TTL for a key.

        Args:
            namespace: Cache namespace
            key: Cache key

        Returns:
            Remaining TTL in seconds, or None if key doesn't exist
        """
        if not self.enabled:
            return None

        try:
            cache_key = self._make_key(namespace, key)
            ttl = self.client.ttl(cache_key)
            return ttl if ttl >= 0 else None

        except RedisError as e:
            logger.warning(f"Cache TTL error: {e}")
            return None

    def exists(self, namespace: str, key: str) -> bool:
        """
        Check if key exists in cache.

        Args:
            namespace: Cache namespace
            key: Cache key

        Returns:
            True if key exists, False otherwise
        """
        if not self.enabled:
            return False

        try:
            cache_key = self._make_key(namespace, key)
            return self.client.exists(cache_key) > 0

        except RedisError as e:
            logger.warning(f"Cache exists error: {e}")
            return False


# Global cache manager instance
cache_manager = CacheManager()


def cached(
    namespace: str,
    key_prefix: str = "",
    ttl: Optional[int] = None,
    cache_type: str = "general",
    key_builder: Optional[Callable] = None,
):
    """
    Decorator for caching function results.

    Args:
        namespace: Cache namespace
        key_prefix: Prefix for cache key
        ttl: Time to live in seconds
        cache_type: Type of cache for metrics
        key_builder: Custom function to build cache key from function args

    Usage:
        @cached(namespace="user_profile", ttl=300)
        def get_user_profile(user_id: str) -> dict:
            return fetch_from_db(user_id)

        @cached(namespace="rules", key_builder=lambda rule_id: f"rule:{rule_id}")
        def get_rule(rule_id: str) -> dict:
            return fetch_rule(rule_id)
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Build cache key
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                # Default: hash of function args
                key_data = f"{func.__name__}:{args}:{kwargs}"
                cache_key = f"{key_prefix}:{hashlib.md5(key_data.encode()).hexdigest()}"

            # Try to get from cache
            cached_value = cache_manager.get(namespace, cache_key, cache_type)
            if cached_value is not None:
                return cached_value

            # Cache miss - call function
            result = func(*args, **kwargs)

            # Store in cache
            cache_manager.set(namespace, cache_key, result, ttl, cache_type)

            return result

        # Add cache management methods to decorated function
        wrapper.cache_invalidate = lambda *args, **kwargs: cache_manager.delete(
            namespace,
            (
                key_builder(*args, **kwargs)
                if key_builder
                else f"{key_prefix}:{hashlib.md5(f'{func.__name__}:{args}:{kwargs}'.encode()).hexdigest()}"
            ),
        )
        wrapper.cache_clear = lambda: cache_manager.clear_namespace(namespace)

        return wrapper

    return decorator


def cache_aside(
    namespace: str,
    key: Union[str, Callable],
    loader: Callable,
    ttl: Optional[int] = None,
    cache_type: str = "general",
) -> Any:
    """
    Cache-aside pattern helper.

    Args:
        namespace: Cache namespace
        key: Cache key or function to build key
        loader: Function to load data on cache miss
        ttl: Time to live in seconds
        cache_type: Type of cache for metrics

    Returns:
        Cached or freshly loaded data

    Usage:
        user_profile = cache_aside(
            namespace="user_profile",
            key=f"user:{user_id}",
            loader=lambda: fetch_user_from_db(user_id),
            ttl=300
        )
    """
    cache_key = key() if callable(key) else key

    # Try cache first
    cached_value = cache_manager.get(namespace, cache_key, cache_type)
    if cached_value is not None:
        return cached_value

    # Cache miss - load data
    data = loader()

    # Store in cache
    if data is not None:
        cache_manager.set(namespace, cache_key, data, ttl, cache_type)

    return data
