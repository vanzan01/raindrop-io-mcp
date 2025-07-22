"""Unit tests for rate limiter."""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch
from src.raindrop.rate_limiter import TokenBucket, CircuitBreaker, CircuitState, RateLimiter


class TestTokenBucket:
    """Test cases for TokenBucket."""
    
    def test_token_bucket_initialization(self):
        """Test token bucket initialization."""
        bucket = TokenBucket(capacity=10, tokens=10, refill_rate=1.0)
        
        assert bucket.capacity == 10
        assert bucket.tokens == 10
        assert bucket.refill_rate == 1.0
        assert bucket.tokens_available() == 10
    
    def test_consume_tokens_success(self):
        """Test successful token consumption."""
        bucket = TokenBucket(capacity=10, tokens=10, refill_rate=1.0)
        
        assert bucket.consume(5) is True
        assert bucket.tokens_available() == 5
    
    def test_consume_tokens_insufficient(self):
        """Test token consumption with insufficient tokens."""
        bucket = TokenBucket(capacity=10, tokens=3, refill_rate=1.0)
        
        assert bucket.consume(5) is False
        assert bucket.tokens_available() == 3  # Unchanged
    
    def test_token_refill(self):
        """Test token refill over time."""
        bucket = TokenBucket(capacity=10, tokens=0, refill_rate=2.0)
        
        # Manually set last_refill to simulate time passage
        bucket.last_refill = time.time() - 2.0  # 2 seconds ago
        
        available = bucket.tokens_available()
        assert available == 4  # 2 seconds * 2 tokens/second
    
    def test_token_refill_capped_at_capacity(self):
        """Test token refill doesn't exceed capacity."""
        bucket = TokenBucket(capacity=10, tokens=5, refill_rate=2.0)
        
        # Simulate 10 seconds passage (would add 20 tokens)
        bucket.last_refill = time.time() - 10.0
        
        available = bucket.tokens_available()
        assert available == 10  # Capped at capacity
    
    def test_time_until_available(self):
        """Test calculating time until tokens are available."""
        bucket = TokenBucket(capacity=10, tokens=2, refill_rate=2.0)
        
        time_needed = bucket.time_until_available(5)
        expected_time = (5 - 2) / 2.0  # (needed - available) / rate
        assert abs(time_needed - expected_time) < 0.1
    
    def test_time_until_available_already_available(self):
        """Test time calculation when tokens are already available."""
        bucket = TokenBucket(capacity=10, tokens=10, refill_rate=1.0)
        
        time_needed = bucket.time_until_available(5)
        assert time_needed == 0.0


class TestCircuitBreaker:
    """Test cases for CircuitBreaker."""
    
    def test_circuit_breaker_initialization(self):
        """Test circuit breaker initialization."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=30.0)
        
        assert cb.failure_threshold == 3
        assert cb.recovery_timeout == 30.0
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0
    
    def test_circuit_breaker_can_execute_closed(self):
        """Test execution permission in closed state."""
        cb = CircuitBreaker()
        
        assert cb.can_execute() is True
    
    def test_circuit_breaker_record_success_closed(self):
        """Test recording success in closed state."""
        cb = CircuitBreaker()
        cb.failure_count = 2
        
        cb.record_success()
        
        assert cb.failure_count == 0
        assert cb.state == CircuitState.CLOSED
    
    def test_circuit_breaker_record_failure_trip(self):
        """Test circuit breaker trips after threshold failures."""
        cb = CircuitBreaker(failure_threshold=2)
        
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 1
        
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        assert cb.failure_count == 2
    
    def test_circuit_breaker_half_open_transition(self):
        """Test transition from open to half-open state."""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)
        
        # Trip the circuit
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        assert cb.can_execute() is False
        
        # Wait for recovery timeout
        time.sleep(0.2)
        
        # Should transition to half-open
        assert cb.can_execute() is True
        assert cb.state == CircuitState.HALF_OPEN
    
    def test_circuit_breaker_half_open_to_closed(self):
        """Test transition from half-open to closed state."""
        cb = CircuitBreaker(success_threshold=2)
        cb.state = CircuitState.HALF_OPEN
        
        cb.record_success()
        assert cb.state == CircuitState.HALF_OPEN
        
        cb.record_success()
        assert cb.state == CircuitState.CLOSED
    
    def test_circuit_breaker_half_open_to_open(self):
        """Test transition from half-open back to open on failure."""
        cb = CircuitBreaker()
        cb.state = CircuitState.HALF_OPEN
        
        cb.record_failure()
        assert cb.state == CircuitState.OPEN


class TestRateLimiter:
    """Test cases for RateLimiter."""
    
    @pytest.fixture
    def rate_limiter(self):
        """Create rate limiter for testing."""
        return RateLimiter(requests_per_minute=60, circuit_breaker_enabled=False)
    
    @pytest.mark.asyncio
    async def test_rate_limiter_initialization(self, rate_limiter):
        """Test rate limiter initialization."""
        await rate_limiter.start()
        
        assert rate_limiter.requests_per_minute == 60
        assert rate_limiter.requests_per_second == 1.0
        assert rate_limiter._running is True
        
        await rate_limiter.stop()
    
    @pytest.mark.asyncio
    async def test_rate_limiter_acquire_immediate(self, rate_limiter):
        """Test immediate token acquisition."""
        await rate_limiter.start()
        
        success = await rate_limiter.acquire()
        assert success is True
        
        await rate_limiter.stop()
    
    @pytest.mark.asyncio
    async def test_rate_limiter_acquire_queue(self):
        """Test queued token acquisition."""
        # Create rate limiter with higher rate for testing (60 requests/minute = 1/second)
        rate_limiter = RateLimiter(requests_per_minute=60, circuit_breaker_enabled=False)
        await rate_limiter.start()
        
        # Consume all tokens (capacity is 60 for 60 req/min)
        for _ in range(60):
            assert await rate_limiter.acquire(timeout=1.0) is True
        
        # Next request should be queued and wait for refill
        start_time = time.time()
        success = await rate_limiter.acquire(timeout=2.0)
        elapsed = time.time() - start_time
        
        assert success is True
        assert elapsed > 0.8  # Should have waited ~1 second for refill
        
        await rate_limiter.stop()
    
    @pytest.mark.asyncio
    async def test_rate_limiter_acquire_timeout(self):
        """Test token acquisition timeout."""
        # Create rate limiter with very low rate
        rate_limiter = RateLimiter(requests_per_minute=6, circuit_breaker_enabled=False)
        await rate_limiter.start()
        
        # Consume all tokens
        for _ in range(6):
            assert await rate_limiter.acquire(timeout=0.1) is True
        
        # Next request should timeout
        success = await rate_limiter.acquire(timeout=0.1)
        assert success is False
        
        await rate_limiter.stop()
    
    @pytest.mark.asyncio
    async def test_rate_limiter_circuit_breaker_integration(self):
        """Test rate limiter with circuit breaker."""
        rate_limiter = RateLimiter(requests_per_minute=60, circuit_breaker_enabled=True)
        await rate_limiter.start()
        
        # Record failures to trip circuit breaker
        for _ in range(5):
            rate_limiter.record_failure()
        
        # Should be rejected due to circuit breaker
        with pytest.raises(Exception, match="circuit breaker"):
            await rate_limiter.acquire()
        
        await rate_limiter.stop()
    
    @pytest.mark.asyncio
    async def test_rate_limiter_statistics(self, rate_limiter):
        """Test rate limiter statistics tracking."""
        await rate_limiter.start()
        
        # Perform some operations
        await rate_limiter.acquire()
        rate_limiter.record_success()
        
        status = rate_limiter.get_status()
        
        assert status["running"] is True
        assert status["statistics"]["requests_processed"] == 1
        assert status["requests_per_minute"] == 60
        
        await rate_limiter.stop()
    
    @pytest.mark.asyncio
    async def test_rate_limiter_priority_queue(self, rate_limiter):
        """Test priority queue functionality."""
        await rate_limiter.start()
        
        # High priority should be processed first
        high_priority = await rate_limiter.acquire(priority="high")
        low_priority = await rate_limiter.acquire(priority="low")
        
        assert high_priority is True
        assert low_priority is True
        
        await rate_limiter.stop()
    
    @pytest.mark.asyncio
    async def test_rate_limiter_stop_while_running(self, rate_limiter):
        """Test stopping rate limiter while processing."""
        await rate_limiter.start()
        
        # Start and immediately stop
        stop_task = asyncio.create_task(rate_limiter.stop())
        await stop_task
        
        assert rate_limiter._running is False
    
    def test_rate_limiter_get_status_stopped(self, rate_limiter):
        """Test getting status when stopped."""
        status = rate_limiter.get_status()
        
        assert status["running"] is False
        assert status["tokens_available"] >= 0
        assert "statistics" in status
        assert "circuit_breaker" in status