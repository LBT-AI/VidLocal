import asyncio
import time
import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import Callable, Any

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    def __init__(self, name: str, failure_threshold: int = 5, recovery_timeout: float = 30.0):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0.0

    def call(self, func: Callable, *args, **kwargs) -> Any:
        if self.state == CircuitState.OPEN:
            if time.monotonic() - self.last_failure_time >= self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                logger.info("Circuit breaker %s: OPEN -> HALF_OPEN", self.name)
            else:
                raise CircuitBreakerOpenError(f"Circuit breaker {self.name} is OPEN")

        try:
            result = func(*args, **kwargs)
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.monotonic()
            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
                logger.warning("Circuit breaker %s: CLOSED -> OPEN (failures=%d)", self.name, self.failure_count)
            raise e

        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            logger.info("Circuit breaker %s: HALF_OPEN -> CLOSED", self.name)

        return result


class CircuitBreakerOpenError(Exception):
    pass


class RetryExhaustedError(Exception):
    pass


class BaseAIService(ABC):
    def __init__(self, service_name: str, timeout: float, retries: int,
                 circuit_breaker_failure_threshold: int = 5,
                 circuit_breaker_recovery_timeout: float = 30.0):
        self.service_name = service_name
        self.timeout = timeout
        self.retries = retries
        self.circuit_breaker = CircuitBreaker(
            name=service_name,
            failure_threshold=circuit_breaker_failure_threshold,
            recovery_timeout=circuit_breaker_recovery_timeout,
        )

    def call_with_retry(self, fn: Callable, *args, **kwargs) -> Any:
        last_error = None
        for attempt in range(self.retries + 1):
            try:
                return self.circuit_breaker.call(fn, *args, **kwargs)
            except CircuitBreakerOpenError:
                raise
            except Exception as e:
                last_error = e
                logger.warning("%s attempt %d/%d failed: %s", self.service_name, attempt + 1, self.retries + 1, e)
                if attempt < self.retries:
                    time.sleep(1.0 * (attempt + 1))
        raise RetryExhaustedError(f"{self.service_name} failed after {self.retries + 1} attempts: {last_error}")

    async def call_with_retry_async(self, fn: Callable, *args, **kwargs) -> Any:
        last_error = None
        for attempt in range(self.retries + 1):
            try:
                return await self._circuit_breaker_call_async(fn, *args, **kwargs)
            except CircuitBreakerOpenError:
                raise
            except Exception as e:
                last_error = e
                logger.warning("%s attempt %d/%d failed: %s", self.service_name, attempt + 1, self.retries + 1, e)
                if attempt < self.retries:
                    await asyncio.sleep(1.0 * (attempt + 1))
        raise RetryExhaustedError(f"{self.service_name} failed after {self.retries + 1} attempts: {last_error}")

    async def _circuit_breaker_call_async(self, fn: Callable, *args, **kwargs) -> Any:
        cb = self.circuit_breaker
        if cb.state == CircuitState.OPEN:
            if time.monotonic() - cb.last_failure_time >= cb.recovery_timeout:
                cb.state = CircuitState.HALF_OPEN
                logger.info("Circuit breaker %s: OPEN -> HALF_OPEN", cb.name)
            else:
                raise CircuitBreakerOpenError(f"Circuit breaker {cb.name} is OPEN")

        try:
            if asyncio.iscoroutinefunction(fn):
                result = await asyncio.wait_for(fn(*args, **kwargs), timeout=self.timeout)
            else:
                result = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(None, lambda: fn(*args, **kwargs)),
                    timeout=self.timeout,
                )
        except asyncio.TimeoutError:
            cb.failure_count += 1
            cb.last_failure_time = time.monotonic()
            if cb.failure_count >= cb.failure_threshold:
                cb.state = CircuitState.OPEN
                logger.warning("Circuit breaker %s: CLOSED -> OPEN (timeout)", cb.name)
            raise TimeoutError(f"{self.service_name} timed out after {self.timeout}s")
        except Exception as e:
            cb.failure_count += 1
            cb.last_failure_time = time.monotonic()
            if cb.failure_count >= cb.failure_threshold:
                cb.state = CircuitState.OPEN
                logger.warning("Circuit breaker %s: CLOSED -> OPEN (failures=%d)", cb.name, cb.failure_count)
            raise e

        if cb.state == CircuitState.HALF_OPEN:
            cb.state = CircuitState.CLOSED
            cb.failure_count = 0
            logger.info("Circuit breaker %s: HALF_OPEN -> CLOSED", cb.name)

        return result
