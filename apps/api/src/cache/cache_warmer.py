"""
Cache warming service to preload frequently accessed data on startup.
Phase 4A: Task 3.3 - Add cache warming on startup
"""
import logging
from typing import List
from sqlalchemy.orm import Session

from src.cache.cached_queries import (
    get_cached_active_rules,
    get_cached_sanctions_list,
    get_cached_dashboard_stats,
    _fetch_active_rules,
    _compute_dashboard_stats
)
from src.cache.cache_manager import cache_manager
from src.database import SessionLocal

logger = logging.getLogger(__name__)


class CacheWarmer:
    """
    Service to warm up cache on application startup.

    Preloads frequently accessed data to improve initial response times.
    """

    def __init__(self):
        self.warmed_namespaces: List[str] = []

    def warm_all(self):
        """
        Warm all caches.

        This should be called during application startup.
        """
        logger.info("Starting cache warming...")

        try:
            db = SessionLocal()

            # Warm rules cache
            self.warm_rules_cache(db)

            # Warm sanctions list
            self.warm_sanctions_cache()

            # Warm dashboard stats
            self.warm_dashboard_cache(db)

            logger.info(f"Cache warming completed. Warmed namespaces: {self.warmed_namespaces}")

        except Exception as e:
            logger.error(f"Cache warming failed: {e}", exc_info=True)

        finally:
            if 'db' in locals():
                db.close()

    def warm_rules_cache(self, db: Session):
        """
        Preload all active monitoring rules.
        """
        try:
            rules = get_cached_active_rules(db)
            logger.info(f"Warmed rules cache: {len(rules)} active rules")
            self.warmed_namespaces.append("rules")

        except Exception as e:
            logger.warning(f"Failed to warm rules cache: {e}")

    def warm_sanctions_cache(self):
        """
        Preload sanctions lists.
        """
        try:
            sanctions = get_cached_sanctions_list()
            logger.info(f"Warmed sanctions cache: {len(sanctions)} entries")
            self.warmed_namespaces.append("sanctions")

        except Exception as e:
            logger.warning(f"Failed to warm sanctions cache: {e}")

    def warm_dashboard_cache(self, db: Session):
        """
        Preload dashboard statistics.
        """
        try:
            stats = get_cached_dashboard_stats(db)
            logger.info(f"Warmed dashboard cache: {stats.get('total_alerts', 0)} alerts")
            self.warmed_namespaces.append("dashboard")

        except Exception as e:
            logger.warning(f"Failed to warm dashboard cache: {e}")

    def warm_user_cache(self, db: Session, user_ids: List[str]):
        """
        Preload cache for specific high-activity users.

        Args:
            db: Database session
            user_ids: List of user IDs to warm cache for
        """
        from src.cache.cached_queries import get_cached_user_risk_profile

        warmed_count = 0

        for user_id in user_ids:
            try:
                get_cached_user_risk_profile(db, user_id)
                warmed_count += 1

            except Exception as e:
                logger.warning(f"Failed to warm cache for user {user_id}: {e}")

        logger.info(f"Warmed user cache for {warmed_count}/{len(user_ids)} users")
        self.warmed_namespaces.append("user_risk_profile")

    def get_cache_stats(self) -> dict:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        try:
            info = cache_manager.client.info("stats")

            return {
                "enabled": cache_manager.enabled,
                "warmed_namespaces": self.warmed_namespaces,
                "redis_stats": {
                    "total_commands_processed": info.get("total_commands_processed", 0),
                    "keyspace_hits": info.get("keyspace_hits", 0),
                    "keyspace_misses": info.get("keyspace_misses", 0),
                    "hit_rate": round(
                        info.get("keyspace_hits", 0) /
                        (info.get("keyspace_hits", 0) + info.get("keyspace_misses", 1)) * 100,
                        2
                    ) if (info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0)) > 0 else 0
                }
            }

        except Exception as e:
            logger.warning(f"Failed to get cache stats: {e}")
            return {
                "enabled": cache_manager.enabled,
                "warmed_namespaces": self.warmed_namespaces,
                "error": str(e)
            }


# Global cache warmer instance
cache_warmer = CacheWarmer()
