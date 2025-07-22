"""Rate limiting system with token bucket algorithm and circuit breaker."""

import asyncio
import time
from typing import Dict, Optional, Tuple, Any
from enum import Enum
from dataclasses import dataclass, field
from .exceptions import RateLimitError
from ..utils.config import Config
from ..utils.logging import get_logger


logger = get_logger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Circuit tripped, requests rejected
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class TokenBucket:
    """Token bucket for rate limiting."""

    capacity: int
    tokens: float
    refill_rate: float  # tokens per second
    last_refill: float = field(default_factory=time.time)

    def consume(self, tokens: int = 1) -> bool:
        """
        Attempt to consume tokens from the bucket.

        Args:
            tokens: Number of tokens to consume

        Returns:
            True if tokens were consumed, False if insufficient tokens
        """
        self._refill()

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill

        # Add tokens based on elapsed time
        tokens_to_add = elapsed * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now

    def tokens_available(self) -> int:
        """Get current number of available tokens."""
        self._refill()
        return int(self.tokens)

    def time_until_available(self, tokens: int = 1) -> float:
        """
        Calculate time until specified tokens are available.

        Args:
            tokens: Number of tokens needed

        Returns:
            Time in seconds until tokens are available
        """
        self._refill()

        if self.tokens >= tokens:
            return 0.0

        tokens_needed = tokens - self.tokens
        return tokens_needed / self.refill_rate


@dataclass
class CircuitBreaker:
    """Circuit breaker implementation."""

    failure_threshold: int = 5
    recovery_timeout: float = 60.0  # seconds
    success_threshold: int = 2  # for half-open -> closed transition

    state: CircuitState = field(default=CircuitState.CLOSED)
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: float = 0.0

    def can_execute(self) -> bool:
        """Check if request can be executed through circuit breaker."""
        if self.state == CircuitState.CLOSED:
            return True
        elif self.state == CircuitState.OPEN:
            # Check if we should transition to half-open
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
                logger.info("Circuit breaker transitioning to HALF_OPEN")
                return True
            return False
        elif self.state == CircuitState.HALF_OPEN:
            return True

        return False

    def record_success(self) -> None:
        """Record a successful operation."""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                logger.info("Circuit breaker CLOSED - service recovered")
        elif self.state == CircuitState.CLOSED:
            # Reset failure count on success
            self.failure_count = 0

    def record_failure(self) -> None:
        """Record a failed operation."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.state == CircuitState.CLOSED:
            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
                logger.warning(f"Circuit breaker OPEN - {self.failure_count} failures")
        elif self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            logger.warning("Circuit breaker OPEN - failure during half-open test")


class PriorityQueue:
    """Priority queue for request management."""

    def __init__(self) -> None:
        self._high_priority: asyncio.Queue[Any] = asyncio.Queue()
        self._normal_priority: asyncio.Queue[Any] = asyncio.Queue()
        self._low_priority: asyncio.Queue[Any] = asyncio.Queue()

    async def put(self, item: Any, priority: str = "normal") -> None:
        """Add item to queue with specified priority."""
        if priority == "high":
            await self._high_priority.put(item)
        elif priority == "low":
            await self._low_priority.put(item)
        else:
            await self._normal_priority.put(item)

    async def get(self) -> Tuple[Any, str]:
        """Get next item from queue, respecting priority."""
        # Check high priority first
        if not self._high_priority.empty():
            item = await self._high_priority.get()
            return item, "high"

        # Then normal priority
        if not self._normal_priority.empty():
            item = await self._normal_priority.get()
            return item, "normal"

        # Finally low priority
        if not self._low_priority.empty():
            item = await self._low_priority.get()
            return item, "low"

        # If all queues are empty, wait for any item
        tasks = [
            asyncio.create_task(self._high_priority.get()),
            asyncio.create_task(self._normal_priority.get()),
            asyncio.create_task(self._low_priority.get()),
        ]

        try:
            done, pending = await asyncio.wait(
                tasks, return_when=asyncio.FIRST_COMPLETED
            )

            # Cancel remaining tasks
            for task in pending:
                task.cancel()

            # Get result from completed task
            completed_task = next(iter(done))
            result = await completed_task

            # Determine priority based on which task completed
            if completed_task == tasks[0]:
                return result, "high"
            elif completed_task == tasks[1]:
                return result, "normal"
            else:
                return result, "low"

        except Exception:
            # Cancel all tasks on error
            for task in tasks:
                if not task.done():
                    task.cancel()
            raise

    def qsize(self) -> Dict[str, int]:
        """Get queue sizes by priority."""
        return {
            "high": self._high_priority.qsize(),
            "normal": self._normal_priority.qsize(),
            "low": self._low_priority.qsize(),
        }


class RateLimiter:
    """
    Comprehensive rate limiting system with token bucket algorithm,
    circuit breaker, and priority queue.
    """

    def __init__(
        self, requests_per_minute: Optional[int] = None, circuit_breaker_enabled: bool = True
    ) -> None:
        """
        Initialize rate limiter.

        Args:
            requests_per_minute: Maximum requests per minute
            circuit_breaker_enabled: Enable circuit breaker protection
        """
        self.requests_per_minute = requests_per_minute or Config.RATE_LIMIT_REQUESTS
        self.requests_per_second = self.requests_per_minute / 60.0

        # Initialize token bucket
        self.token_bucket = TokenBucket(
            capacity=self.requests_per_minute,
            tokens=self.requests_per_minute,  # Start with full bucket
            refill_rate=self.requests_per_second,
        )

        # Initialize circuit breaker
        self.circuit_breaker = CircuitBreaker() if circuit_breaker_enabled else None

        # Request queue for handling overflow
        self.request_queue = PriorityQueue()
        self._queue_processor_task: Optional[asyncio.Task] = None
        self._running = False

        # Statistics
        self.stats = {
            "requests_processed": 0,
            "requests_rejected": 0,
            "requests_queued": 0,
            "circuit_breaker_trips": 0,
            "average_wait_time": 0.0,
        }

    async def start(self) -> None:
        """Start the rate limiter and queue processor."""
        if self._running:
            return

        self._running = True
        self._queue_processor_task = asyncio.create_task(self._process_queue())
        logger.info(f"Rate limiter started: {self.requests_per_minute} req/min")

    async def stop(self) -> None:
        """Stop the rate limiter and queue processor."""
        self._running = False

        if self._queue_processor_task:
            self._queue_processor_task.cancel()
            try:
                await self._queue_processor_task
            except asyncio.CancelledError:
                pass

        logger.info("Rate limiter stopped")

    async def acquire(self, priority: str = "normal", timeout: float = 30.0) -> bool:
        """
        Acquire permission to make a request.

        Args:
            priority: Request priority ("high", "normal", "low")
            timeout: Maximum time to wait for permission

        Returns:
            True if permission granted, False if timeout or rejected

        Raises:
            RateLimitError: If rate limit exceeded and cannot queue
        """
        start_time = time.time()

        # Check circuit breaker first
        if self.circuit_breaker and not self.circuit_breaker.can_execute():
            self.stats["requests_rejected"] += 1
            raise RateLimitError(
                "Service temporarily unavailable (circuit breaker open)"
            )

        # Try immediate token consumption
        if self.token_bucket.consume():
            self.stats["requests_processed"] += 1
            return True

        # If no tokens available, queue the request
        future: asyncio.Future[bool] = asyncio.Future()
        request_info = {
            "timestamp": start_time,
            "priority": priority,
            "future": future,
        }

        await self.request_queue.put(request_info, priority)
        self.stats["requests_queued"] += 1

        try:
            # Wait for request to be processed or timeout
            result: bool = await asyncio.wait_for(future, timeout=timeout)

            wait_time = time.time() - start_time
            self._update_average_wait_time(wait_time)

            return result

        except asyncio.TimeoutError:
            self.stats["requests_rejected"] += 1
            logger.warning(f"Request timed out after {timeout}s")
            return False

    async def _process_queue(self) -> None:
        """Process queued requests."""
        logger.info("Queue processor started")

        while self._running:
            try:
                # Get next request from queue
                request_info, priority = await self.request_queue.get()

                # Wait for tokens to be available
                while self._running and not self.token_bucket.consume():
                    wait_time = self.token_bucket.time_until_available()
                    await asyncio.sleep(min(wait_time, 1.0))

                if not self._running:
                    break

                # Check circuit breaker
                if self.circuit_breaker and not self.circuit_breaker.can_execute():
                    request_info["future"].set_result(False)
                    self.stats["requests_rejected"] += 1
                    continue

                # Grant permission
                request_info["future"].set_result(True)
                self.stats["requests_processed"] += 1

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in queue processor: {e}")
                await asyncio.sleep(1.0)

        logger.info("Queue processor stopped")

    def record_success(self) -> None:
        """Record successful API operation."""
        if self.circuit_breaker:
            self.circuit_breaker.record_success()

    def record_failure(self) -> None:
        """Record failed API operation."""
        if self.circuit_breaker:
            self.circuit_breaker.record_failure()
            if self.circuit_breaker.state == CircuitState.OPEN:
                self.stats["circuit_breaker_trips"] += 1

    def get_status(self) -> Dict[str, Any]:
        """Get current rate limiter status."""
        return {
            "running": self._running,
            "tokens_available": self.token_bucket.tokens_available(),
            "requests_per_minute": self.requests_per_minute,
            "queue_sizes": self.request_queue.qsize(),
            "circuit_breaker": {
                "state": (
                    self.circuit_breaker.state.value
                    if self.circuit_breaker
                    else "disabled"
                ),
                "failure_count": (
                    self.circuit_breaker.failure_count if self.circuit_breaker else 0
                ),
            },
            "statistics": self.stats.copy(),
        }

    def _update_average_wait_time(self, wait_time: float) -> None:
        """Update average wait time statistic."""
        current_avg = self.stats["average_wait_time"]
        processed = self.stats["requests_processed"]

        if processed <= 1:
            self.stats["average_wait_time"] = wait_time
        else:
            # Calculate rolling average
            self.stats["average_wait_time"] = (
                (current_avg * (processed - 1)) + wait_time
            ) / processed
