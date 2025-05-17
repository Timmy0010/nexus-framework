# nexus_framework/core/enhanced_rate_limiter.py
import time
import threading
from typing import Dict, Any, Optional, Tuple, List, Callable
import logging
import statistics
from dataclasses import dataclass
from enum import Enum
import math

logger = logging.getLogger(__name__)

# Import existing rate limiter components
from nexus_framework.core.rate_limiter import (
    TokenBucket, 
    RateLimiter, 
    RateLimitExceededError, 
    RateLimitTimeoutError
)

class ServiceHealthState(Enum):
    """States a service can be in, affecting rate limiting."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    RECOVERING = "recovering"

@dataclass
class HealthMetrics:
    """Metrics to track for adaptive rate limiting."""
    response_times: List[float] = None  # in seconds
    error_count: int = 0
    total_requests: int = 0
    last_update_time: float = 0
    
    def __post_init__(self):
        if self.response_times is None:
            self.response_times = []
        self.last_update_time = time.time()
    
    def add_response_time(self, response_time: float) -> None:
        """Add a response time sample."""
        self.response_times.append(response_time)
        # Keep a reasonable history size to avoid memory issues
        if len(self.response_times) > 100:
            self.response_times.pop(0)
    
    def record_request(self, error: bool = False) -> None:
        """Record a request, optionally as an error."""
        self.total_requests += 1
        if error:
            self.error_count += 1
    
    def get_error_rate(self) -> float:
        """Get the current error rate (0.0-1.0)."""
        if self.total_requests == 0:
            return 0.0
        return self.error_count / self.total_requests
    
    def get_average_response_time(self) -> Optional[float]:
        """Get the average response time, or None if no data."""
        if not self.response_times:
            return None
        return statistics.mean(self.response_times)
    
    def get_p95_response_time(self) -> Optional[float]:
        """Get the 95th percentile response time, or None if insufficient data."""
        if len(self.response_times) < 10:  # Need reasonable sample size
            return None
        return statistics.quantiles(sorted(self.response_times), n=20)[-1]  # 95th percentile
    
    def reset(self) -> None:
        """Reset the metrics to start fresh."""
        self.response_times = []
        self.error_count = 0
        self.total_requests = 0
        self.last_update_time = time.time()

class HealthAwareRateLimiter(RateLimiter):
    """
    Enhanced rate limiter that adapts based on service health metrics.
    
    This extends the basic RateLimiter with the ability to dynamically adjust
    rate limits based on service health indicators like response time and error rates.
    """
    
    def __init__(self, default_capacity: int = 10, default_refill_rate: float = 1.0):
        """
        Initialize the health-aware rate limiter.
        
        Args:
            default_capacity: Default capacity for new token buckets
            default_refill_rate: Default refill rate (tokens per second) for new token buckets
        """
        super().__init__(default_capacity, default_refill_rate)
        
        # Track health metrics for each resource
        self._health_metrics: Dict[str, HealthMetrics] = {}
        
        # Track current health state for each resource
        self._health_states: Dict[str, ServiceHealthState] = {}
        
        # Track original capacities and refill rates for recovery
        self._original_configs: Dict[str, Dict[str, float]] = {}
        
        # Health check configuration
        self._health_check_thresholds = {
            # Default thresholds - can be overridden per resource
            "default": {
                "error_rate_degraded": 0.05,  # 5% errors -> degraded
                "error_rate_critical": 0.15,  # 15% errors -> critical
                "response_time_degraded": 1.0,  # 1 second -> degraded
                "response_time_critical": 3.0,  # 3 seconds -> critical
                "recovery_factor": 0.8,  # Recover to 80% of original when improving
                "degraded_reduction_factor": 0.5,  # Reduce to 50% when degraded
                "critical_reduction_factor": 0.2,  # Reduce to 20% when critical
            }
        }
        
        # Lock for health metrics updates
        self._health_lock = threading.Lock()
        
        # Start health check background thread
        self._stop_health_check = threading.Event()
        self._health_check_thread = threading.Thread(
            target=self._health_check_loop,
            daemon=True,
            name="HealthAwareRateLimiter-HealthCheck"
        )
        self._health_check_thread.start()
    
    def configure_health_thresholds(self, resource_id: str, thresholds: Dict[str, float]) -> None:
        """
        Configure health check thresholds for a specific resource.
        
        Args:
            resource_id: Resource identifier
            thresholds: Dictionary of threshold values to override defaults
        """
        with self._health_lock:
            if resource_id not in self._health_check_thresholds:
                # Start with default thresholds
                self._health_check_thresholds[resource_id] = self._health_check_thresholds["default"].copy()
            
            # Update with provided thresholds
            self._health_check_thresholds[resource_id].update(thresholds)
            
            logger.info(f"Configured health thresholds for resource '{resource_id}': {thresholds}")
    
    def configure_limit(self, resource_id: str, capacity: int, refill_rate: float) -> None:
        """
        Configure rate limit for a specific resource and store the original configuration.
        
        Args:
            resource_id: Resource identifier
            capacity: Maximum token capacity
            refill_rate: Token refill rate per second
        """
        super().configure_limit(resource_id, capacity, refill_rate)
        
        # Store original configuration for recovery
        with self._health_lock:
            self._original_configs[resource_id] = {
                "capacity": capacity,
                "refill_rate": refill_rate
            }
    
    def record_request_start(self, resource_id: str) -> float:
        """
        Record the start of a request for health tracking.
        
        Args:
            resource_id: Resource identifier
            
        Returns:
            Start timestamp for later calculation of response time
        """
        # Ensure health metrics exist for this resource
        with self._health_lock:
            if resource_id not in self._health_metrics:
                self._health_metrics[resource_id] = HealthMetrics()
            
            metrics = self._health_metrics[resource_id]
            metrics.record_request()
        
        return time.time()
    
    def record_request_complete(self, resource_id: str, start_time: float, error: bool = False) -> None:
        """
        Record the completion of a request for health tracking.
        
        Args:
            resource_id: Resource identifier
            start_time: Start timestamp from record_request_start
            error: Whether the request resulted in an error
        """
        end_time = time.time()
        response_time = end_time - start_time
        
        with self._health_lock:
            if resource_id not in self._health_metrics:
                self._health_metrics[resource_id] = HealthMetrics()
            
            metrics = self._health_metrics[resource_id]
            if error:
                metrics.error_count += 1
            
            metrics.add_response_time(response_time)
            
            # Log if response time is unusually high
            avg_time = metrics.get_average_response_time()
            if avg_time and response_time > avg_time * 2:
                logger.warning(f"Slow response for resource '{resource_id}': {response_time:.3f}s (avg: {avg_time:.3f}s)")
    
    def execute_with_rate_limit(self, resource_id: str, func: Callable, *args, **kwargs) -> Any:
        """
        Execute a function with rate limiting and health tracking.
        
        Args:
            resource_id: Resource identifier
            func: Function to execute
            *args, **kwargs: Arguments to pass to the function
            
        Returns:
            Result from the function
            
        Raises:
            RateLimitExceededError: If rate limit is exceeded
            Any exception raised by the function
        """
        # Apply rate limit
        if not self.is_allowed(resource_id):
            raise RateLimitExceededError(resource_id)
        
        # Record request start
        start_time = self.record_request_start(resource_id)
        
        try:
            # Execute function
            result = func(*args, **kwargs)
            
            # Record successful completion
            self.record_request_complete(resource_id, start_time)
            
            return result
        
        except Exception as e:
            # Record error
            self.record_request_complete(resource_id, start_time, error=True)
            raise
    
    async def execute_with_rate_limit_async(self, resource_id: str, func: Callable, *args, **kwargs) -> Any:
        """
        Execute an async function with rate limiting and health tracking.
        
        Args:
            resource_id: Resource identifier
            func: Async function to execute
            *args, **kwargs: Arguments to pass to the function
            
        Returns:
            Result from the async function
            
        Raises:
            RateLimitExceededError: If rate limit is exceeded
            Any exception raised by the function
        """
        # Apply rate limit
        if not self.is_allowed(resource_id):
            raise RateLimitExceededError(resource_id)
        
        # Record request start
        start_time = self.record_request_start(resource_id)
        
        try:
            # Execute function
            result = await func(*args, **kwargs)
            
            # Record successful completion
            self.record_request_complete(resource_id, start_time)
            
            return result
        
        except Exception as e:
            # Record error
            self.record_request_complete(resource_id, start_time, error=True)
            raise
    
    def get_resource_health_state(self, resource_id: str) -> ServiceHealthState:
        """
        Get the current health state of a resource.
        
        Args:
            resource_id: Resource identifier
            
        Returns:
            Current service health state
        """
        with self._health_lock:
            return self._health_states.get(resource_id, ServiceHealthState.HEALTHY)
    
    def get_health_metrics(self, resource_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current health metrics for a resource.
        
        Args:
            resource_id: Resource identifier
            
        Returns:
            Dictionary of health metrics or None if no data
        """
        with self._health_lock:
            if resource_id not in self._health_metrics:
                return None
            
            metrics = self._health_metrics[resource_id]
            
            return {
                "error_rate": metrics.get_error_rate(),
                "average_response_time": metrics.get_average_response_time(),
                "p95_response_time": metrics.get_p95_response_time(),
                "total_requests": metrics.total_requests,
                "error_count": metrics.error_count,
                "health_state": self.get_resource_health_state(resource_id).value
            }
    
    def _health_check_loop(self) -> None:
        """Background thread for periodic health checks and rate limit adjustments."""
        check_interval = 5  # Check every 5 seconds
        
        while not self._stop_health_check.is_set():
            try:
                self._perform_health_checks()
            except Exception as e:
                logger.error(f"Error in health check loop: {str(e)}")
            
            # Sleep before next check
            self._stop_health_check.wait(check_interval)
    
    def _perform_health_checks(self) -> None:
        """Check health metrics and adjust rate limits as needed."""
        with self._health_lock:
            # Check each resource with metrics
            for resource_id, metrics in self._health_metrics.items():
                # Skip if not enough data
                if metrics.total_requests < 10 or not metrics.response_times:
                    continue
                
                # Get thresholds for this resource (or use defaults)
                thresholds = self._health_check_thresholds.get(
                    resource_id, self._health_check_thresholds["default"]
                )
                
                # Get current metrics
                error_rate = metrics.get_error_rate()
                avg_response_time = metrics.get_average_response_time() or 0
                
                # Determine health state
                current_state = self._health_states.get(resource_id, ServiceHealthState.HEALTHY)
                new_state = current_state
                
                # Check thresholds for state transitions
                if error_rate >= thresholds["error_rate_critical"] or \
                   avg_response_time >= thresholds["response_time_critical"]:
                    new_state = ServiceHealthState.CRITICAL
                elif error_rate >= thresholds["error_rate_degraded"] or \
                     avg_response_time >= thresholds["response_time_degraded"]:
                    new_state = ServiceHealthState.DEGRADED
                elif current_state in (ServiceHealthState.CRITICAL, ServiceHealthState.DEGRADED):
                    # Check if recovered enough to improve state
                    if error_rate < thresholds["error_rate_degraded"] * 0.7 and \
                       avg_response_time < thresholds["response_time_degraded"] * 0.7:
                        new_state = ServiceHealthState.RECOVERING
                elif current_state == ServiceHealthState.RECOVERING:
                    # Check if fully recovered
                    if error_rate < thresholds["error_rate_degraded"] * 0.5 and \
                       avg_response_time < thresholds["response_time_degraded"] * 0.5:
                        new_state = ServiceHealthState.HEALTHY
                
                # Handle state transition if changed
                if new_state != current_state:
                    self._handle_health_state_transition(resource_id, current_state, new_state, thresholds)
                    self._health_states[resource_id] = new_state
    
    def _handle_health_state_transition(
        self, 
        resource_id: str, 
        old_state: ServiceHealthState, 
        new_state: ServiceHealthState,
        thresholds: Dict[str, float]
    ) -> None:
        """
        Handle a health state transition by adjusting rate limits.
        
        Args:
            resource_id: Resource identifier
            old_state: Previous health state
            new_state: New health state
            thresholds: Threshold configuration for this resource
        """
        # Skip if we don't have original config (can't adjust)
        if resource_id not in self._original_configs:
            return
        
        # Get original configuration
        original_config = self._original_configs[resource_id]
        original_capacity = original_config["capacity"]
        original_refill_rate = original_config["refill_rate"]
        
        # Get current bucket if exists
        bucket = self._buckets.get(resource_id)
        if not bucket:
            return
        
        # Calculate new limits based on new state
        new_capacity = original_capacity
        new_refill_rate = original_refill_rate
        
        if new_state == ServiceHealthState.DEGRADED:
            # Reduce capacity and rate for degraded service
            factor = thresholds["degraded_reduction_factor"]
            new_capacity = max(1, int(original_capacity * factor))
            new_refill_rate = max(0.1, original_refill_rate * factor)
            
            logger.warning(
                f"Service '{resource_id}' health degraded. "
                f"Reducing rate limit to {new_capacity} capacity, {new_refill_rate:.2f} tps"
            )
        
        elif new_state == ServiceHealthState.CRITICAL:
            # Severely reduce capacity and rate for critical service
            factor = thresholds["critical_reduction_factor"]
            new_capacity = max(1, int(original_capacity * factor))
            new_refill_rate = max(0.05, original_refill_rate * factor)
            
            logger.error(
                f"Service '{resource_id}' health critical. "
                f"Reducing rate limit to {new_capacity} capacity, {new_refill_rate:.2f} tps"
            )
        
        elif new_state == ServiceHealthState.RECOVERING:
            # Gradually increase capacity and rate for recovering service
            # Use a value between current and original, based on recovery factor
            factor = thresholds["recovery_factor"]
            current_capacity = bucket.capacity
            current_refill_rate = bucket.refill_rate
            
            # Calculate target as percentage between current and original
            target_capacity = current_capacity + (original_capacity - current_capacity) * factor
            target_refill_rate = current_refill_rate + (original_refill_rate - current_refill_rate) * factor
            
            new_capacity = max(current_capacity, int(target_capacity))
            new_refill_rate = max(current_refill_rate, target_refill_rate)
            
            logger.info(
                f"Service '{resource_id}' recovering. "
                f"Increasing rate limit to {new_capacity} capacity, {new_refill_rate:.2f} tps"
            )
        
        elif new_state == ServiceHealthState.HEALTHY:
            # Restore original capacity and rate for healthy service
            new_capacity = original_capacity
            new_refill_rate = original_refill_rate
            
            logger.info(
                f"Service '{resource_id}' returned to healthy state. "
                f"Restoring rate limit to {new_capacity} capacity, {new_refill_rate:.2f} tps"
            )
        
        # Apply the new rate limit
        self.configure_limit(resource_id, new_capacity, new_refill_rate)
    
    def shutdown(self) -> None:
        """Stop the health check background thread."""
        self._stop_health_check.set()
        self._health_check_thread.join(timeout=1.0)
        logger.info("HealthAwareRateLimiter shutdown complete")
