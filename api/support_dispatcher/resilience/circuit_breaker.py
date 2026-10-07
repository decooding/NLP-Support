"""Circuit breaker and retry policies for external system resilience."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from enum import Enum
from typing import TypeVar

from support_dispatcher.core.config import CircuitBreakerOpenError

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CircuitState(str, Enum):
    """Possible states of the Circuit Breaker."""

    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreaker:
    """Protects downstream services from cascade failures by tripping after continuous errors."""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_state_change = time.monotonic()
        self._lock = asyncio.Lock()

    async def call(self, coro_func: Callable[[], Awaitable[T]]) -> T:
        """Executes the coroutine wrapped with circuit breaker protection."""
        async with self._lock:
            now = time.monotonic()
            if self.state == CircuitState.OPEN:
                if now - self.last_state_change > self.recovery_timeout:
                    self.state = CircuitState.HALF_OPEN
                    logger.info("Circuit breaker entered HALF_OPEN state.")
                else:
                    raise CircuitBreakerOpenError(
                        f"Circuit breaker is OPEN. Recovery in {self.recovery_timeout - (now - self.last_state_change):.1f}s"
                    )

        try:
            result = await coro_func()
            async with self._lock:
                if self.state in (CircuitState.HALF_OPEN, CircuitState.CLOSED):
                    self.failure_count = 0
                    self.state = CircuitState.CLOSED
            return result
        except Exception as e:
            async with self._lock:
                self.failure_count += 1
                if (
                    self.failure_count >= self.failure_threshold
                    or self.state == CircuitState.HALF_OPEN
                ):
                    self.state = CircuitState.OPEN
                    self.last_state_change = time.monotonic()
                    logger.warning(
                        "Circuit breaker tripped OPEN. Failures: %d, Threshold: %d",
                        self.failure_count,
                        self.failure_threshold,
                    )
            raise e
