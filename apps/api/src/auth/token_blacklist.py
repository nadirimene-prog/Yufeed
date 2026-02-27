"""
Token Blacklist (Redis-backed JWT Revocation)

Provides token-level and user-level revocation using Redis.
Graceful degradation: if Redis is unavailable, operations log a warning
but never crash the application.
"""

import time
import logging
from typing import Optional

import redis  # type: ignore[import-untyped]

from src.config import settings

logger = logging.getLogger(__name__)

# Redis key prefixes
_PREFIX_TOKEN = "token:blacklist:"
_PREFIX_USER = "token:revoked_users:"


class TokenBlacklist:
    """
    Redis-backed token blacklist for JWT revocation.

    Supports:
    - Individual token revocation by JTI (with TTL matching JWT expiry).
    - User-level revocation: all tokens issued before a certain timestamp
      are considered revoked.

    All public methods degrade gracefully when Redis is unreachable.
    """

    def __init__(self, redis_url: Optional[str] = None):
        self._redis_url = redis_url or settings.REDIS_URL
        self._client: Optional[redis.Redis] = None

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def _get_client(self) -> Optional[redis.Redis]:
        """Return a Redis client, creating one lazily. Returns None on failure."""
        if self._client is not None:
            return self._client
        try:
            self._client = redis.from_url(
                self._redis_url,
                **settings.redis_connection_kwargs,
            )
            # Verify connectivity
            self._client.ping()
            logger.debug("Token blacklist connected to Redis")
            return self._client
        except Exception as exc:
            logger.warning(
                f"Token blacklist: Redis unavailable ({exc}). Operating without revocation."
            )
            self._client = None
            return None

    # ------------------------------------------------------------------
    # Individual token revocation
    # ------------------------------------------------------------------

    def revoke_token(self, jti: str, expires_in: int) -> bool:
        """
        Add a token's JTI to the blacklist.

        Args:
            jti: The JWT ID claim (unique per token).
            expires_in: Remaining lifetime of the token in seconds.
                        The Redis key will auto-expire after this duration,
                        so the blacklist is self-cleaning.

        Returns:
            True if the token was successfully blacklisted, False on Redis error.
        """
        if not jti:
            return False
        client = self._get_client()
        if client is None:
            return False
        try:
            key = f"{_PREFIX_TOKEN}{jti}"
            ttl = max(expires_in, 1)  # at least 1 second
            client.setex(key, ttl, "1")
            logger.info(f"Token revoked: jti={jti}, ttl={ttl}s")
            return True
        except Exception as exc:
            logger.warning(f"Token blacklist: failed to revoke jti={jti}: {exc}")
            return False

    def is_revoked(self, jti: str) -> bool:
        """
        Check whether a token has been individually revoked.

        Returns False (not revoked) if Redis is unavailable, allowing
        the request through rather than locking out all users.
        """
        if not jti:
            return False
        client = self._get_client()
        if client is None:
            return False
        try:
            return client.exists(f"{_PREFIX_TOKEN}{jti}") > 0
        except Exception as exc:
            logger.warning(f"Token blacklist: failed to check jti={jti}: {exc}")
            return False

    # ------------------------------------------------------------------
    # User-level revocation
    # ------------------------------------------------------------------

    def revoke_all_user_tokens(self, user_id: str) -> bool:
        """
        Revoke every token issued to *user_id* before this moment.

        Stores the current UNIX timestamp; any token whose ``iat`` is
        earlier than this value is considered revoked.

        The key persists for 8 days (longer than the maximum refresh
        token lifetime of 7 days) so it outlives all outstanding tokens.

        Args:
            user_id: The user whose tokens should be revoked.

        Returns:
            True on success, False on Redis error.
        """
        client = self._get_client()
        if client is None:
            return False
        try:
            key = f"{_PREFIX_USER}{user_id}"
            now = int(time.time())
            # 8 days TTL > 7-day refresh token lifetime
            client.setex(key, 8 * 86400, str(now))
            logger.info(f"All tokens revoked for user_id={user_id} (before ts={now})")
            return True
        except Exception as exc:
            logger.warning(
                f"Token blacklist: failed to revoke user tokens for user_id={user_id}: {exc}"
            )
            return False

    def is_user_revoked(self, user_id: str, issued_at: int) -> bool:
        """
        Check whether a user-level revocation applies to a token.

        Args:
            user_id: The user ID from the token payload.
            issued_at: The ``iat`` claim (UNIX timestamp) of the token.

        Returns:
            True if the token was issued before the user-level revocation
            timestamp. False (not revoked) if Redis is unavailable.
        """
        if not user_id:
            return False
        client = self._get_client()
        if client is None:
            return False
        try:
            key = f"{_PREFIX_USER}{user_id}"
            revoked_at = client.get(key)
            if revoked_at is None:
                return False
            return issued_at <= int(revoked_at)
        except Exception as exc:
            logger.warning(
                f"Token blacklist: failed to check user revocation for user_id={user_id}: {exc}"
            )
            return False

    # ------------------------------------------------------------------
    # Combined check (convenience)
    # ------------------------------------------------------------------

    def is_token_revoked(self, jti: str, user_id: str, issued_at: int) -> bool:
        """
        Combined check: individual JTI revocation OR user-level revocation.

        Returns True if the token should be rejected.
        """
        return self.is_revoked(jti) or self.is_user_revoked(user_id, issued_at)


# ------------------------------------------------------------------
# Module-level singleton
# ------------------------------------------------------------------
token_blacklist = TokenBlacklist()
