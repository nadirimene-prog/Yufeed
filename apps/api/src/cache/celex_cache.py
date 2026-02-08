"""
Redis Caching Layer for CELEX Queries

Provides high-performance caching for EU Cellar SPARQL queries to reduce
external API calls and improve response times from 500-2000ms to <10ms.

Cache Strategy:
- TTL: 24 hours (EU documents rarely change)
- Keys: celex:{CELEX_NUMBER}
- Values: JSON-encoded metadata
- Invalidation: Manual or on update
"""

import redis
import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class CelexCache:
    """
    Redis-based caching for CELEX document metadata.

    Features:
    - 100x faster queries (Redis vs SPARQL)
    - Automatic expiration (configurable TTL)
    - Bulk operations support
    - Cache statistics tracking
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        ttl_hours: int = 24,
        key_prefix: str = "celex:",
    ):
        """
        Initialize Redis cache connection.

        Args:
            redis_url: Redis connection URL
            ttl_hours: Time-to-live for cached entries in hours
            key_prefix: Prefix for all cache keys
        """
        try:
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            self.ttl = timedelta(hours=ttl_hours)
            self.key_prefix = key_prefix

            # Test connection
            self.redis_client.ping()
            logger.info(f"Redis cache connected: {redis_url}, TTL={ttl_hours}h")
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis_client = None

    def _make_key(self, celex: str) -> str:
        """Generate Redis key for CELEX."""
        return f"{self.key_prefix}{celex.upper()}"

    def get(self, celex: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached CELEX metadata.

        Args:
            celex: CELEX number

        Returns:
            Cached metadata dict or None if not found
        """
        if not self.redis_client:
            return None

        try:
            key = self._make_key(celex)
            data = self.redis_client.get(key)

            if data:
                logger.debug(f"Cache HIT for {celex}")
                metadata = json.loads(data)

                # Deserialize datetime fields
                if "date_document" in metadata and metadata["date_document"]:
                    metadata["date_document"] = datetime.fromisoformat(metadata["date_document"])
                if "date_entry_into_force" in metadata and metadata["date_entry_into_force"]:
                    metadata["date_entry_into_force"] = datetime.fromisoformat(
                        metadata["date_entry_into_force"]
                    )

                return metadata
            else:
                logger.debug(f"Cache MISS for {celex}")
                return None

        except (json.JSONDecodeError, redis.RedisError) as e:
            logger.error(f"Error reading cache for {celex}: {e}")
            return None

    def set(self, celex: str, metadata: Dict[str, Any]) -> bool:
        """
        Store CELEX metadata in cache.

        Args:
            celex: CELEX number
            metadata: Document metadata dict

        Returns:
            True if successfully cached
        """
        if not self.redis_client:
            return False

        try:
            key = self._make_key(celex)

            # Serialize datetime objects
            serializable_metadata = metadata.copy()
            for field in ["date_document", "date_entry_into_force"]:
                if field in serializable_metadata and isinstance(
                    serializable_metadata[field], datetime
                ):
                    serializable_metadata[field] = serializable_metadata[field].isoformat()

            data = json.dumps(serializable_metadata)

            # Set with TTL
            self.redis_client.setex(key, int(self.ttl.total_seconds()), data)

            logger.debug(f"Cached {celex} with TTL={self.ttl}")
            return True

        except (TypeError, redis.RedisError) as e:
            logger.error(f"Error caching {celex}: {e}")
            return False

    def get_many(self, celex_list: List[str]) -> Dict[str, Optional[Dict[str, Any]]]:
        """
        Retrieve multiple CELEX metadata entries in one operation.

        Args:
            celex_list: List of CELEX numbers

        Returns:
            Dictionary mapping CELEX to metadata (or None if not cached)
        """
        if not self.redis_client or not celex_list:
            return {celex: None for celex in celex_list}

        try:
            keys = [self._make_key(celex) for celex in celex_list]
            values = self.redis_client.mget(keys)

            results = {}
            for celex, data in zip(celex_list, values):
                if data:
                    try:
                        metadata = json.loads(data)
                        # Deserialize dates
                        if "date_document" in metadata and metadata["date_document"]:
                            metadata["date_document"] = datetime.fromisoformat(
                                metadata["date_document"]
                            )
                        if (
                            "date_entry_into_force" in metadata
                            and metadata["date_entry_into_force"]
                        ):
                            metadata["date_entry_into_force"] = datetime.fromisoformat(
                                metadata["date_entry_into_force"]
                            )
                        results[celex] = metadata
                    except json.JSONDecodeError:
                        results[celex] = None
                else:
                    results[celex] = None

            hits = sum(1 for v in results.values() if v is not None)
            logger.info(f"Bulk cache lookup: {hits}/{len(celex_list)} hits")

            return results

        except redis.RedisError as e:
            logger.error(f"Error in bulk cache lookup: {e}")
            return {celex: None for celex in celex_list}

    def set_many(self, entries: Dict[str, Dict[str, Any]]) -> int:
        """
        Store multiple CELEX metadata entries in one operation.

        Args:
            entries: Dictionary mapping CELEX to metadata

        Returns:
            Number of entries successfully cached
        """
        if not self.redis_client or not entries:
            return 0

        try:
            pipeline = self.redis_client.pipeline()
            count = 0

            for celex, metadata in entries.items():
                try:
                    key = self._make_key(celex)

                    # Serialize datetime objects
                    serializable_metadata = metadata.copy()
                    for field in ["date_document", "date_entry_into_force"]:
                        if field in serializable_metadata and isinstance(
                            serializable_metadata[field], datetime
                        ):
                            serializable_metadata[field] = serializable_metadata[field].isoformat()

                    data = json.dumps(serializable_metadata)
                    pipeline.setex(key, int(self.ttl.total_seconds()), data)
                    count += 1
                except (TypeError, json.JSONDecodeError) as e:
                    logger.error(f"Error serializing {celex}: {e}")

            pipeline.execute()
            logger.info(f"Bulk cached {count} entries")
            return count

        except redis.RedisError as e:
            logger.error(f"Error in bulk cache set: {e}")
            return 0

    def delete(self, celex: str) -> bool:
        """
        Remove CELEX from cache (cache invalidation).

        Args:
            celex: CELEX number to remove

        Returns:
            True if deleted
        """
        if not self.redis_client:
            return False

        try:
            key = self._make_key(celex)
            deleted = self.redis_client.delete(key)
            logger.debug(f"Deleted cache for {celex}: {deleted}")
            return deleted > 0
        except redis.RedisError as e:
            logger.error(f"Error deleting cache for {celex}: {e}")
            return False

    def clear_all(self) -> int:
        """
        Clear all CELEX cache entries.

        Returns:
            Number of keys deleted
        """
        if not self.redis_client:
            return 0

        try:
            pattern = f"{self.key_prefix}*"
            keys = list(self.redis_client.scan_iter(match=pattern))
            if keys:
                deleted = self.redis_client.delete(*keys)
                logger.info(f"Cleared {deleted} cache entries")
                return deleted
            return 0
        except redis.RedisError as e:
            logger.error(f"Error clearing cache: {e}")
            return 0

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats (size, memory, etc.)
        """
        if not self.redis_client:
            return {"connected": False}

        try:
            info = self.redis_client.info()
            pattern = f"{self.key_prefix}*"

            # Count keys (expensive for large caches - use with caution)
            key_count = sum(1 for _ in self.redis_client.scan_iter(match=pattern, count=1000))

            return {
                "connected": True,
                "total_keys": key_count,
                "memory_used_mb": round(info.get("used_memory", 0) / 1024 / 1024, 2),
                "total_commands": info.get("total_commands_processed", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "hit_rate": round(
                    info.get("keyspace_hits", 0)
                    / max(info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0), 1)
                    * 100,
                    2,
                ),
            }
        except redis.RedisError as e:
            logger.error(f"Error getting cache stats: {e}")
            return {"connected": False, "error": str(e)}

    def is_connected(self) -> bool:
        """Check if Redis connection is active."""
        if not self.redis_client:
            return False
        try:
            return self.redis_client.ping()
        except redis.RedisError:
            return False

    def close(self):
        """Close Redis connection."""
        if self.redis_client:
            self.redis_client.close()
            logger.info("Redis connection closed")
