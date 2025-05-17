"""
Example demonstrating the enhanced rate limiter functionality.

This script shows how to use the HealthAwareRateLimiter for dynamic 
rate limiting based on service health metrics.
"""

import logging
import time
import random
import threading
import concurrent.futures
from typing import List, Dict, Any

from nexus_framework.core.enhanced_rate_limiter import (
    HealthAwareRateLimiter,
    ServiceHealthState,
    RateLimitExceededError
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger("rate_limiter_example")

class MockService:
    """Mock service that simulates variable response times and errors."""
    
    def __init__(self, name: str, error_rate: float = 0.0, base_latency: float = 0.1):
        """
        Initialize the mock service.
        
        Args:
            name: Service name
            error_rate: Probability of errors (0.0-1.0)
            base_latency: Base response time in seconds
        """
        self.name = name
        self.error_rate = error_rate
        self.base_latency = base_latency
        self.call_count = 0
        self.error_count = 0
        self.lock = threading.Lock()
    
    def set_error_rate(self, error_rate: float) -> None:
        """Update the error rate."""
        self.error_rate = max(0.0, min(1.0, error_rate))
    
    def set_base_latency(self, base_latency: float) -> None:
        """Update the base latency."""
        self.base_latency = max(0.01, base_latency)
    
    def call(self) -> Dict[str, Any]:
        """
        Call the mock service.
        
        Returns:
            Response data
            
        Raises:
            Exception: If the service encounters an error
        """
        with self.lock:
            self.call_count += 1
            call_id = self.call_count
        
        # Simulate processing time
        latency = self.base_latency
        
        # Add some random variation
        latency += random.uniform(0, self.base_latency)
        
        # Simulate service degradation under load
        recent_calls = self.call_count % 100  # Simplistic proxy for load
        if recent_calls > 70:
            # Increase latency exponentially with load
            load_factor = (recent_calls - 70) / 30.0  # 0.0-1.0
            latency *= (1.0 + load_factor * 3)  # Up to 4x slower under max load
        
        time.sleep(latency)
        
        # Determine if this call will error
        if random.random() < self.error_rate:
            with self.lock:
                self.error_count += 1
            raise Exception(f"Mock service {self.name} error")
        
        # Return success response
        return {
            "service": self.name,
            "call_id": call_id,
            "latency": latency,
            "timestamp": time.time()
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current service statistics."""
        with self.lock:
            return {
                "service": self.name,
                "call_count": self.call_count,
                "error_count": self.error_count,
                "error_rate": self.error_count / max(1, self.call_count),
                "base_latency": self.base_latency
            }

def service_caller_thread(
    service: MockService,
    rate_limiter: HealthAwareRateLimiter,
    thread_id: int,
    call_count: int,
    delay: float
) -> Dict[str, Any]:
    """
    Thread that calls a service with rate limiting.
    
    Args:
        service: The service to call
        rate_limiter: Rate limiter to use
        thread_id: ID of this thread
        call_count: Number of calls to make
        delay: Delay between calls
        
    Returns:
        Statistics about the calls
    """
    resource_id = service.name
    success_count = 0
    error_count = 0
    rate_limited_count = 0
    response_times = []
    
    logger.info(f"Thread {thread_id} started for service {service.name}")
    
    for i in range(call_count):
        try:
            # Wait for rate limit
            try:
                rate_limiter.wait_for_token(resource_id, timeout_seconds=2.0)
            except RateLimitExceededError:
                rate_limited_count += 1
                logger.warning(f"Thread {thread_id}: Rate limit exceeded for {resource_id}")
                time.sleep(0.5)  # Back off a bit
                continue
            
            # Record request start for health tracking
            start_time = rate_limiter.record_request_start(resource_id)
            
            # Call service
            try:
                result = service.call()
                success_count += 1
                response_time = time.time() - start_time
                response_times.append(response_time)
                
                # Record successful completion
                rate_limiter.record_request_complete(resource_id, start_time)
                
                if i % 10 == 0:
                    logger.info(f"Thread {thread_id}: Call {i} to {resource_id} succeeded in {response_time:.3f}s")
            
            except Exception as e:
                error_count += 1
                
                # Record error for health tracking
                rate_limiter.record_request_complete(resource_id, start_time, error=True)
                
                if i % 10 == 0:
                    logger.warning(f"Thread {thread_id}: Call {i} to {resource_id} failed: {str(e)}")
        
        except Exception as e:
            error_count += 1
            logger.error(f"Thread {thread_id}: Unexpected error: {str(e)}")
        
        # Wait before next call
        time.sleep(delay)
    
    # Calculate statistics
    avg_response_time = sum(response_times) / max(1, len(response_times))
    
    stats = {
        "thread_id": thread_id,
        "service": service.name,
        "success_count": success_count,
        "error_count": error_count,
        "rate_limited_count": rate_limited_count,
        "total_calls": success_count + error_count + rate_limited_count,
        "avg_response_time": avg_response_time
    }
    
    logger.info(f"Thread {thread_id} completed with {success_count} successes, {error_count} errors, {rate_limited_count} rate limited")
    return stats

def print_health_metrics(rate_limiter: HealthAwareRateLimiter, service_ids: List[str]) -> None:
    """Print current health metrics for services."""
    logger.info("=== Current Health Metrics ===")
    
    for service_id in service_ids:
        metrics = rate_limiter.get_health_metrics(service_id)
        if not metrics:
            logger.info(f"{service_id}: No metrics available")
            continue
        
        # Format metrics nicely
        error_rate = metrics.get("error_rate", 0) * 100
        avg_time = metrics.get("average_response_time", 0) * 1000
        p95_time = metrics.get("p95_response_time", 0) * 1000
        health_state = metrics.get("health_state", "unknown")
        
        logger.info(
            f"{service_id}: {health_state.upper()} - "
            f"Error rate: {error_rate:.1f}%, "
            f"Avg response: {avg_time:.1f}ms, "
            f"P95 response: {p95_time:.1f}ms, "
            f"Requests: {metrics.get('total_requests', 0)}"
        )
    
    logger.info("=============================")

def main():
    """Run the rate limiter example."""
    logger.info("Starting Health-Aware Rate Limiter Example")
    
    # Create rate limiter
    rate_limiter = HealthAwareRateLimiter(default_capacity=20, default_refill_rate=5.0)
    
    # Create mock services
    services = {
        "service_a": MockService("service_a", error_rate=0.01, base_latency=0.1),
        "service_b": MockService("service_b", error_rate=0.05, base_latency=0.2),
        "service_c": MockService("service_c", error_rate=0.02, base_latency=0.15)
    }
    
    # Configure rate limits for each service
    rate_limiter.configure_limit("service_a", capacity=50, refill_rate=10.0)  # 10 TPS
    rate_limiter.configure_limit("service_b", capacity=30, refill_rate=5.0)   # 5 TPS
    rate_limiter.configure_limit("service_c", capacity=20, refill_rate=2.0)   # 2 TPS
    
    # Configure health thresholds for each service
    rate_limiter.configure_health_thresholds("service_a", {
        "error_rate_degraded": 0.05,   # 5% errors -> degraded
        "error_rate_critical": 0.15,   # 15% errors -> critical
        "response_time_degraded": 0.5, # 500ms -> degraded
        "response_time_critical": 1.0  # 1s -> critical
    })
    
    rate_limiter.configure_health_thresholds("service_b", {
        "error_rate_degraded": 0.10,   # 10% errors -> degraded (more lenient)
        "error_rate_critical": 0.20,   # 20% errors -> critical
        "response_time_degraded": 0.7, # 700ms -> degraded
        "response_time_critical": 1.5  # 1.5s -> critical
    })
    
    # Service C uses default thresholds
    
    # Create a thread pool
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=15)
    futures = []
    
    # Start caller threads (5 threads per service)
    for service_id, service in services.items():
        for i in range(5):
            future = executor.submit(
                service_caller_thread,
                service,
                rate_limiter,
                i + 1,
                call_count=100,  # Each thread makes 100 calls
                delay=0.1        # 100ms between calls
            )
            futures.append(future)
    
    # Start metrics printer thread
    stop_printer = threading.Event()
    
    def metrics_printer():
        while not stop_printer.is_set():
            print_health_metrics(rate_limiter, list(services.keys()))
            stop_printer.wait(3.0)  # Print every 3 seconds
    
    printer_thread = threading.Thread(target=metrics_printer)
    printer_thread.daemon = True
    printer_thread.start()
    
    # Simulate service degradation after 10 seconds
    def degrade_service():
        logger.info("=== Starting service degradation scenario ===")
        time.sleep(10)
        
        # Degrade service B (higher error rate)
        logger.info("Degrading service_b with higher error rate")
        services["service_b"].set_error_rate(0.15)
        time.sleep(10)
        
        # Degrade service C (higher latency)
        logger.info("Degrading service_c with higher latency")
        services["service_c"].set_base_latency(0.8)
        time.sleep(10)
        
        # Critical failure of service A
        logger.info("Critical failure for service_a")
        services["service_a"].set_error_rate(0.3)
        time.sleep(10)
        
        # Start recovery
        logger.info("=== Starting service recovery scenario ===")
        
        # Recover service B
        logger.info("Recovering service_b")
        services["service_b"].set_error_rate(0.03)
        time.sleep(5)
        
        # Recover service C
        logger.info("Recovering service_c")
        services["service_c"].set_base_latency(0.15)
        time.sleep(5)
        
        # Recover service A
        logger.info("Recovering service_a")
        services["service_a"].set_error_rate(0.01)
        
        logger.info("=== Service scenarios complete ===")
    
    # Start the degradation scenario in a separate thread
    scenario_thread = threading.Thread(target=degrade_service)
    scenario_thread.daemon = True
    scenario_thread.start()
    
    # Wait for all caller threads to complete
    all_stats = []
    for future in concurrent.futures.as_completed(futures):
        try:
            stats = future.result()
            all_stats.append(stats)
        except Exception as e:
            logger.error(f"Thread error: {str(e)}")
    
    # Stop the metrics printer
    stop_printer.set()
    printer_thread.join(timeout=1.0)
    
    # Print final statistics
    logger.info("=== Final Statistics ===")
    
    # Group by service
    service_stats = {}
    for stat in all_stats:
        service_id = stat["service"]
        if service_id not in service_stats:
            service_stats[service_id] = []
        service_stats[service_id].append(stat)
    
    for service_id, stats_list in service_stats.items():
        total_success = sum(s["success_count"] for s in stats_list)
        total_error = sum(s["error_count"] for s in stats_list)
        total_rate_limited = sum(s["rate_limited_count"] for s in stats_list)
        total_calls = sum(s["total_calls"] for s in stats_list)
        
        service_stats = services[service_id].get_stats()
        
        logger.info(f"Service {service_id}:")
        logger.info(f"  Total calls attempted: {total_calls}")
        logger.info(f"  Successful calls: {total_success} ({total_success/max(1,total_calls)*100:.1f}%)")
        logger.info(f"  Failed calls: {total_error} ({total_error/max(1,total_calls)*100:.1f}%)")
        logger.info(f"  Rate limited calls: {total_rate_limited} ({total_rate_limited/max(1,total_calls)*100:.1f}%)")
        logger.info(f"  Service internal stats: {service_stats}")
    
    # Get final health metrics
    logger.info("=== Final Health Metrics ===")
    for service_id in services.keys():
        metrics = rate_limiter.get_health_metrics(service_id)
        if metrics:
            logger.info(f"Service {service_id} health metrics: {metrics}")
    
    # Shut down the rate limiter
    rate_limiter.shutdown()
    
    logger.info("Example completed successfully")

if __name__ == "__main__":
    main()
