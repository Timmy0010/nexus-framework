# nexus_framework/core/rate_limiter.py
import time
import threading
from typing import Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class RateLimitExceededError(Exception):
    """Custom exception raised when a rate limit is exceeded and waiting is not an option."""
    def __init__(self, resource_id: str, message: Optional[str] = None):
        self.resource_id = resource_id
        self.message = message or f"Rate limit exceeded for resource '{resource_id}'."
        super().__init__(self.message)

class RateLimitTimeoutError(Exception):
    """Custom exception raised when waiting for a token times out."""
    def __init__(self, resource_id: str, timeout: float, message: Optional[str] = None):
        self.resource_id = resource_id
        self.timeout = timeout
        self.message = message or f"Timeout ({timeout}s) waiting for token for resource '{resource_id}'."
        super().__init__(self.message)

class TokenBucket:
    def __init__(self, capacity: int, refill_rate: float):
        """
        Initializes a TokenBucket.

        Args:
            capacity: The maximum number of tokens the bucket can hold.
            refill_rate: The number of tokens added to the bucket per second.
        """
        if capacity <= 0:
            raise ValueError("Capacity must be positive.")
        if refill_rate <= 0:
            raise ValueError("Refill rate must be positive.")

        self.capacity = capacity
        self.tokens = float(capacity)  # Start with a full bucket
        self.refill_rate = float(refill_rate)
        self.last_refill_timestamp = time.monotonic()
        self.lock = threading.Lock()

    def _refill(self) -> None:
        """Adds tokens to the bucket based on the time elapsed since the last refill."""
        now = time.monotonic()
        elapsed_time = now - self.last_refill_timestamp
        if elapsed_time > 0:
            tokens_to_add = elapsed_time * self.refill_rate
            self.tokens = min(self.capacity, self.tokens + tokens_to_add)
            self.last_refill_timestamp = now

    def consume(self, tokens_to_consume: int = 1) -> bool:
        """
        Attempts to consume a specified number of tokens from the bucket.

        Args:
            tokens_to_consume: The number of tokens to consume. Defaults to 1.

        Returns:
            True if tokens were successfully consumed, False otherwise.
        """
        if tokens_to_consume <= 0:
            raise ValueError("Tokens to consume must be positive.")
        
        with self.lock:
            self._refill()
            if self.tokens >= tokens_to_consume:
                self.tokens -= tokens_to_consume
                return True
            return False

    def get_current_tokens(self) -> float:
        """Returns the current number of tokens in the bucket after refilling."""
        with self.lock:
            self._refill()
            return self.tokens

    def get_time_to_next_token(self, tokens_needed: int = 1) -> float:
        """
        Calculates the estimated time until the bucket has enough tokens.
        Returns 0.0 if enough tokens are already available.
        """
        if tokens_needed <= 0:
            raise ValueError("Tokens needed must be positive.")
        with self.lock:
            self._refill()
            if self.tokens >= tokens_needed:
                return 0.0
            
            shortfall = tokens_needed - self.tokens
            if self.refill_rate == 0: # Should not happen with constructor validation
                return float('inf') 
            return shortfall / self.refill_rate


class RateLimiter:
    def __init__(self, default_capacity: int = 10, default_refill_rate: float = 1.0):
        """
        Initializes the RateLimiter.

        Args:
            default_capacity: Default capacity for new token buckets.
            default_refill_rate: Default refill rate (tokens per second) for new token buckets.
        """
        self._buckets: Dict[str, TokenBucket] = {}
        self._default_capacity = default_capacity
        self._default_refill_rate = default_refill_rate
        self._lock = threading.Lock() # To protect access to self._buckets

    def _get_or_create_bucket(self, resource_id: str,
                               capacity: Optional[int] = None,
                               refill_rate: Optional[float] = None) -> TokenBucket:
        """Retrieves an existing bucket or creates a new one for the given resource_id."""
        if resource_id not in self._buckets:
            with self._lock:
                if resource_id not in self._buckets: # Double-check locking
                    use_capacity = capacity if capacity is not None else self._default_capacity
                    use_refill_rate = refill_rate if refill_rate is not None else self._default_refill_rate
                    logger.info(f"Creating new token bucket for resource '{resource_id}' "
                                f"with capacity {use_capacity} and refill rate {use_refill_rate} tps.")
                    self._buckets[resource_id] = TokenBucket(use_capacity, use_refill_rate)
        
        bucket = self._buckets[resource_id]
        # If specific capacity/refill_rate are provided and different from existing, update.
        if (capacity is not None and bucket.capacity != capacity) or \
           (refill_rate is not None and bucket.refill_rate != refill_rate):
            with self._lock: # Lock for modification
                bucket = self._buckets[resource_id] # Re-fetch in case another thread modified
                new_cap = capacity if capacity is not None else bucket.capacity
                new_rate = refill_rate if refill_rate is not None else bucket.refill_rate
                if bucket.capacity != new_cap or bucket.refill_rate != new_rate:
                    logger.warning(f"Resource '{resource_id}' limit is being updated: "
                                   f"new capacity={new_cap}, new refill_rate={new_rate} tps.")
                    self._buckets[resource_id] = TokenBucket(new_cap, new_rate)
                    bucket = self._buckets[resource_id]
        return bucket

    def configure_limit(self, resource_id: str, capacity: int, refill_rate: float) -> None:
        """
        Configures or updates the rate limit for a specific resource.
        """
        with self._lock:
            logger.info(f"Configuring rate limit for resource '{resource_id}': "
                        f"capacity={capacity}, refill_rate={refill_rate} tps.")
            self._buckets[resource_id] = TokenBucket(capacity, refill_rate)

    def is_allowed(self, resource_id: str, tokens_to_consume: int = 1,
                   capacity: Optional[int] = None, refill_rate: Optional[float] = None) -> bool:
        """
        Checks if a request for the given resource is allowed.
        """
        bucket = self._get_or_create_bucket(resource_id, capacity, refill_rate)
        allowed = bucket.consume(tokens_to_consume)
        if not allowed:
            logger.debug(f"Rate limit hit for resource '{resource_id}'. Request denied.")
        return allowed

    def wait_for_token(self, resource_id: str, tokens_to_consume: int = 1,
                       timeout_seconds: Optional[float] = None,
                       capacity: Optional[int] = None, refill_rate: Optional[float] = None,
                       polling_interval: float = 0.05) -> None: # Reduced polling interval
        """
        Waits until tokens are available for the specified resource, or until timeout.
        """
        bucket = self._get_or_create_bucket(resource_id, capacity, refill_rate)
        start_time = time.monotonic()
        while True:
            if bucket.consume(tokens_to_consume):
                logger.debug(f"Token acquired for resource '{resource_id}'.")
                return
            if timeout_seconds is not None and (time.monotonic() - start_time) >= timeout_seconds:
                raise RateLimitTimeoutError(resource_id, timeout_seconds)
            
            time_to_wait_for_tokens = bucket.get_time_to_next_token(tokens_to_consume)
            actual_wait_time = max(min(time_to_wait_for_tokens, polling_interval), 0) # Ensure non-negative
            
            if timeout_seconds is not None:
                remaining_timeout = timeout_seconds - (time.monotonic() - start_time)
                if remaining_timeout <= 0:
                    raise RateLimitTimeoutError(resource_id, timeout_seconds)
                actual_wait_time = min(actual_wait_time, remaining_timeout)

            if actual_wait_time > 0:
                 time.sleep(actual_wait_time)
            # If actual_wait_time is 0, loop immediately to re-check (e.g. tokens became available)

    def try_consume_or_raise(self, resource_id: str, tokens_to_consume: int = 1,
                             capacity: Optional[int] = None, refill_rate: Optional[float] = None) -> None:
        """
        Attempts to consume tokens and raises RateLimitExceededError if not allowed.
        """
        if not self.is_allowed(resource_id, tokens_to_consume, capacity, refill_rate):
            raise RateLimitExceededError(resource_id)
        logger.debug(f"Token successfully consumed for resource '{resource_id}'.")