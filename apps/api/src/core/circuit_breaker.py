"""
Circuit Breaker Pattern for External Service Calls

Protects the application from cascading failures when external services
(Anthropic API, OpenSearch) are unavailable or degraded. The breaker
transitions through three states:

  CLOSED  -- normal operation; failures are counted.
  OPEN    -- calls fail fast with CircuitOpenError; after a recovery
             timeout the breaker moves to HALF_OPEN.
  HALF_OPEN -- a limited number of probe calls are allowed through.
               If enough succeed the breaker closes; if any fail it
               re-opens.

Thread-safe: all state mutations are protected by a threading.Lock.
Only stdlib dependencies are used (threading, time, enum, logging).
"""

from enum import Enum
from typing import Any, Callable, TypeVar

import logging
import threading
import time

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CircuitState(Enum):
    """Possible states of a circuit breaker."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitOpenError(Exception):
    """Raised when a call is attempted while the circuit is OPEN."""

    def __init__(self, name: str, remaining_seconds: float):
        self.name = name
        self.remaining_seconds = remaining_seconds
        super().__init__(
            f"Circuit breaker '{name}' is OPEN. " f"Retry in {remaining_seconds:.1f}s."
        )


class CircuitBreaker:
    """
    Circuit breaker that wraps calls to an external service.

    Parameters
    ----------
    name : str
        Human-readable identifier (used in logs and error messages).
    failure_threshold : int
        Number of consecutive failures required to trip the breaker open.
    recovery_timeout : float
        Seconds to wait in the OPEN state before transitioning to HALF_OPEN.
    success_threshold : int
        Consecutive successes needed in HALF_OPEN to close the breaker.
    excluded_exceptions : tuple
        Exception types that should NOT count as failures (e.g. validation
        errors caused by bad input, not by service problems).
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        success_threshold: int = 2,
        excluded_exceptions: tuple = (),
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        self.excluded_exceptions = excluded_exceptions

        # Internal state -- protected by _lock
        self._lock = threading.Lock()
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: float = 0.0
        self._opened_at: float = 0.0

    # ------------------------------------------------------------------
    # Public read-only properties
    # ------------------------------------------------------------------

    @property
    def state(self) -> CircuitState:
        """Return the current state, auto-transitioning from OPEN to HALF_OPEN
        if the recovery timeout has elapsed."""
        with self._lock:
            self._maybe_transition_to_half_open()
            return self._state

    @property
    def failure_count(self) -> int:
        with self._lock:
            return self._failure_count

    # ------------------------------------------------------------------
    # Synchronous call wrapper
    # ------------------------------------------------------------------

    def call(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """
        Execute *func* through the circuit breaker.

        Raises CircuitOpenError if the circuit is currently OPEN and the
        recovery timeout has not yet elapsed.
        """
        self._before_call()
        try:
            result = func(*args, **kwargs)
        except Exception as exc:
            self._on_failure(exc)
            raise
        else:
            self._on_success()
            return result

    # ------------------------------------------------------------------
    # Asynchronous call wrapper
    # ------------------------------------------------------------------

    async def async_call(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """
        Execute an async *func* through the circuit breaker.

        Raises CircuitOpenError if the circuit is currently OPEN and the
        recovery timeout has not yet elapsed.
        """
        self._before_call()
        try:
            result = await func(*args, **kwargs)
        except Exception as exc:
            self._on_failure(exc)
            raise
        else:
            self._on_success()
            return result

    # ------------------------------------------------------------------
    # Manual controls (useful for health-check endpoints)
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Force the breaker back to CLOSED."""
        with self._lock:
            old = self._state
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._success_count = 0
        if old != CircuitState.CLOSED:
            logger.info(
                "Circuit breaker '%s' manually reset: %s -> CLOSED",
                self.name,
                old.value,
            )

    def trip(self) -> None:
        """Force the breaker to OPEN."""
        with self._lock:
            old = self._state
            self._state = CircuitState.OPEN
            self._opened_at = time.monotonic()
            self._failure_count = self.failure_threshold
            self._success_count = 0
        if old != CircuitState.OPEN:
            logger.warning(
                "Circuit breaker '%s' manually tripped: %s -> OPEN",
                self.name,
                old.value,
            )

    # ------------------------------------------------------------------
    # State info (for monitoring / health endpoints)
    # ------------------------------------------------------------------

    def info(self) -> dict:
        """Return a snapshot of the breaker's internal state."""
        with self._lock:
            self._maybe_transition_to_half_open()
            remaining = 0.0
            if self._state == CircuitState.OPEN:
                elapsed = time.monotonic() - self._opened_at
                remaining = max(0.0, self.recovery_timeout - elapsed)
            return {
                "name": self.name,
                "state": self._state.value,
                "failure_count": self._failure_count,
                "failure_threshold": self.failure_threshold,
                "success_count": self._success_count,
                "success_threshold": self.success_threshold,
                "recovery_timeout": self.recovery_timeout,
                "retry_after_seconds": round(remaining, 1),
            }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _before_call(self) -> None:
        """Gate-check before allowing a call through."""
        with self._lock:
            self._maybe_transition_to_half_open()

            if self._state == CircuitState.OPEN:
                elapsed = time.monotonic() - self._opened_at
                remaining = max(0.0, self.recovery_timeout - elapsed)
                raise CircuitOpenError(self.name, remaining)

            # CLOSED and HALF_OPEN allow calls through.

    def _on_success(self) -> None:
        """Handle a successful call."""
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.success_threshold:
                    logger.info(
                        "Circuit breaker '%s' recovered: HALF_OPEN -> CLOSED "
                        "(%d consecutive successes)",
                        self.name,
                        self._success_count,
                    )
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    self._success_count = 0
            elif self._state == CircuitState.CLOSED:
                # Reset failure counter on success while closed.
                self._failure_count = 0

    def _on_failure(self, exc: Exception) -> None:
        """Handle a failed call."""
        # Skip excluded exception types (e.g. client-side validation errors).
        if isinstance(exc, self.excluded_exceptions):
            return

        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                # Any failure in half-open immediately re-opens.
                logger.warning(
                    "Circuit breaker '%s' re-opened: HALF_OPEN -> OPEN " "(probe call failed: %s)",
                    self.name,
                    exc,
                )
                self._state = CircuitState.OPEN
                self._opened_at = time.monotonic()
                self._success_count = 0
            elif self._state == CircuitState.CLOSED:
                self._failure_count += 1
                self._last_failure_time = time.monotonic()
                if self._failure_count >= self.failure_threshold:
                    logger.warning(
                        "Circuit breaker '%s' tripped: CLOSED -> OPEN "
                        "(%d consecutive failures, last: %s)",
                        self.name,
                        self._failure_count,
                        exc,
                    )
                    self._state = CircuitState.OPEN
                    self._opened_at = time.monotonic()
                    self._success_count = 0

    def _maybe_transition_to_half_open(self) -> None:
        """If OPEN and recovery timeout has elapsed, move to HALF_OPEN.
        Must be called while holding self._lock."""
        if self._state == CircuitState.OPEN:
            elapsed = time.monotonic() - self._opened_at
            if elapsed >= self.recovery_timeout:
                logger.info(
                    "Circuit breaker '%s' recovery window elapsed: "
                    "OPEN -> HALF_OPEN (after %.1fs)",
                    self.name,
                    elapsed,
                )
                self._state = CircuitState.HALF_OPEN
                self._success_count = 0


# =====================================================================
# Pre-configured instances for YuFeed external services
# =====================================================================

anthropic_breaker = CircuitBreaker(
    name="anthropic",
    failure_threshold=3,
    recovery_timeout=60,
    success_threshold=2,
)

opensearch_breaker = CircuitBreaker(
    name="opensearch",
    failure_threshold=5,
    recovery_timeout=30,
    success_threshold=2,
)
