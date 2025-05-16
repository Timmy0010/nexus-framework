"""
Metrics collection utilities for the Nexus framework.

This module provides utilities for collecting and tracking metrics
related to agent performance and system health within the Nexus framework.
"""

import logging
import time
from typing import Dict, Optional, Any, List, Callable, Union
from datetime import datetime
import threading
import statistics
from functools import wraps

# Set up logging
logger = logging.getLogger(__name__)


class MetricsCollector:
    """
    Collects and manages metrics for the Nexus framework.
    
    This class provides utilities for tracking various metrics related to
    agent performance, system health, and usage statistics.
    """
    
    def __init__(self):
        """Initialize a new metrics collector."""
        # Counters for various metrics
        self._counters: Dict[str, int] = {}
        
        # Gauges for current values
        self._gauges: Dict[str, float] = {}
        
        # Histograms for value distributions
        self._histograms: Dict[str, List[float]] = {}
        
        # Whether metrics collection is enabled
        self.enabled = True
        
        # Lock for thread safety
        self._lock = threading.Lock()
    
    def increment_counter(self, name: str, value: int = 1) -> None:
        """
        Increment a counter metric.
        
        Args:
            name: The name of the counter.
            value: The amount to increment by.
        """
        if not self.enabled:
            return
        
        with self._lock:
            if name not in self._counters:
                self._counters[name] = 0
            
            self._counters[name] += value
    
    def decrement_counter(self, name: str, value: int = 1) -> None:
        """
        Decrement a counter metric.
        
        Args:
            name: The name of the counter.
            value: The amount to decrement by.
        """
        if not self.enabled:
            return
        
        with self._lock:
            if name not in self._counters:
                self._counters[name] = 0
            
            self._counters[name] -= value
    
    def set_counter(self, name: str, value: int) -> None:
        """
        Set a counter metric to a specific value.
        
        Args:
            name: The name of the counter.
            value: The value to set.
        """
        if not self.enabled:
            return
        
        with self._lock:
            self._counters[name] = value
    
    def get_counter(self, name: str) -> int:
        """
        Get the current value of a counter metric.
        
        Args:
            name: The name of the counter.
            
        Returns:
            The current value of the counter, or 0 if it does not exist.
        """
        with self._lock:
            return self._counters.get(name, 0)
    
    def set_gauge(self, name: str, value: float) -> None:
        """
        Set a gauge metric to a specific value.
        
        Args:
            name: The name of the gauge.
            value: The value to set.
        """
        if not self.enabled:
            return
        
        with self._lock:
            self._gauges[name] = value
    
    def get_gauge(self, name: str) -> float:
        """
        Get the current value of a gauge metric.
        
        Args:
            name: The name of the gauge.
            
        Returns:
            The current value of the gauge, or 0.0 if it does not exist.
        """
        with self._lock:
            return self._gauges.get(name, 0.0)
    
    def observe_histogram(self, name: str, value: float) -> None:
        """
        Add a value observation to a histogram metric.
        
        Args:
            name: The name of the histogram.
            value: The value to observe.
        """
        if not self.enabled:
            return
        
        with self._lock:
            if name not in self._histograms:
                self._histograms[name] = []
            
            self._histograms[name].append(value)
    
    def get_histogram_stats(self, name: str) -> Dict[str, float]:
        """
        Get statistics for a histogram metric.
        
        Args:
            name: The name of the histogram.
            
        Returns:
            A dictionary containing statistics (count, min, max, mean, median)
            for the histogram, or an empty dictionary if it does not exist.
        """
        with self._lock:
            if name not in self._histograms or not self._histograms[name]:
                return {}
            
            values = self._histograms[name]
            
            return {
                "count": len(values),
                "min": min(values),
                "max": max(values),
                "mean": statistics.mean(values),
                "median": statistics.median(values)
            }
    
    def clear_metrics(self) -> None:
        """Clear all metrics."""
        with self._lock:
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """
        Get all metrics.
        
        Returns:
            A dictionary containing all metrics.
        """
        with self._lock:
            result = {
                "counters": self._counters.copy(),
                "gauges": self._gauges.copy(),
                "histograms": {}
            }
            
            # Compute histogram statistics
            for name in self._histograms:
                result["histograms"][name] = self.get_histogram_stats(name)
            
            return result
    
    def track_function_execution_time(self, name: str) -> Callable:
        """
        Decorator to track the execution time of a function.
        
        Args:
            name: The prefix for the metrics names.
            
        Returns:
            A decorator function.
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                if not self.enabled:
                    return func(*args, **kwargs)
                
                # Track function calls
                self.increment_counter(f"{name}_calls")
                
                # Track execution time
                start_time = time.time()
                
                try:
                    result = func(*args, **kwargs)
                    
                    # Track successful executions
                    self.increment_counter(f"{name}_success")
                    
                    return result
                
                except Exception:
                    # Track failures
                    self.increment_counter(f"{name}_failure")
                    
                    # Re-raise the exception
                    raise
                
                finally:
                    # Record execution time
                    execution_time = time.time() - start_time
                    self.observe_histogram(f"{name}_time", execution_time * 1000)  # Convert to ms
            
            return wrapper
        
        return decorator


class MetricsContext:
    """
    A context manager for tracking execution time of a block of code.
    
    This class is used with the 'with' statement to track the execution time
    of a block of code and record it as a histogram metric.
    """
    
    def __init__(self, metrics_collector: MetricsCollector, name: str):
        """
        Initialize a new metrics context.
        
        Args:
            metrics_collector: The MetricsCollector to use for tracking.
            name: The name of the metric to record.
        """
        self.metrics_collector = metrics_collector
        self.name = name
        self.start_time = None
    
    def __enter__(self) -> 'MetricsContext':
        """
        Enter the metrics context, starting the execution timer.
        
        Returns:
            The MetricsContext instance.
        """
        if not self.metrics_collector.enabled:
            return self
        
        self.start_time = time.time()
        self.metrics_collector.increment_counter(f"{self.name}_executions")
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Exit the metrics context, recording the execution time.
        
        Args:
            exc_type: The exception type if an exception was raised.
            exc_val: The exception value if an exception was raised.
            exc_tb: The traceback if an exception was raised.
        """
        if not self.metrics_collector.enabled or self.start_time is None:
            return
        
        execution_time = time.time() - self.start_time
        
        # Record execution time
        self.metrics_collector.observe_histogram(
            f"{self.name}_time",
            execution_time * 1000  # Convert to ms
        )
        
        if exc_type is not None:
            # Record failure
            self.metrics_collector.increment_counter(f"{self.name}_failures")
        else:
            # Record success
            self.metrics_collector.increment_counter(f"{self.name}_successes")


# Common metrics related to agents and tools
class CommonMetrics:
    """
    Common metrics related to agents and tools in the Nexus framework.
    
    This class provides utility methods for tracking common metrics
    within the framework.
    """
    
    @classmethod
    def track_agent_message_processing(
        cls,
        metrics_collector: MetricsCollector,
        agent_id: str,
        message_content_type: str,
        success: bool,
        duration_ms: float
    ) -> None:
        """
        Track metrics related to agent message processing.
        
        Args:
            metrics_collector: The MetricsCollector to use for tracking.
            agent_id: The ID of the agent.
            message_content_type: The content type of the message.
            success: Whether the processing was successful.
            duration_ms: The duration of the processing in milliseconds.
        """
        if not metrics_collector.enabled:
            return
        
        # Track total messages processed
        metrics_collector.increment_counter("agent_messages_processed")
        
        # Track messages by agent
        metrics_collector.increment_counter(f"agent_{agent_id}_messages_processed")
        
        # Track messages by content type
        metrics_collector.increment_counter(f"message_type_{message_content_type}_processed")
        
        # Track success/failure
        if success:
            metrics_collector.increment_counter("agent_messages_success")
            metrics_collector.increment_counter(f"agent_{agent_id}_messages_success")
        else:
            metrics_collector.increment_counter("agent_messages_failure")
            metrics_collector.increment_counter(f"agent_{agent_id}_messages_failure")
        
        # Track processing time
        metrics_collector.observe_histogram("agent_message_processing_time", duration_ms)
        metrics_collector.observe_histogram(f"agent_{agent_id}_processing_time", duration_ms)
    
    @classmethod
    def track_tool_invocation(
        cls,
        metrics_collector: MetricsCollector,
        tool_name: str,
        agent_id: str,
        success: bool,
        duration_ms: float
    ) -> None:
        """
        Track metrics related to tool invocation.
        
        Args:
            metrics_collector: The MetricsCollector to use for tracking.
            tool_name: The name of the tool.
            agent_id: The ID of the agent invoking the tool.
            success: Whether the invocation was successful.
            duration_ms: The duration of the invocation in milliseconds.
        """
        if not metrics_collector.enabled:
            return
        
        # Track total tool invocations
        metrics_collector.increment_counter("tool_invocations")
        
        # Track invocations by tool
        metrics_collector.increment_counter(f"tool_{tool_name}_invocations")
        
        # Track invocations by agent
        metrics_collector.increment_counter(f"agent_{agent_id}_tool_invocations")
        
        # Track success/failure
        if success:
            metrics_collector.increment_counter("tool_invocations_success")
            metrics_collector.increment_counter(f"tool_{tool_name}_invocations_success")
            metrics_collector.increment_counter(f"agent_{agent_id}_tool_invocations_success")
        else:
            metrics_collector.increment_counter("tool_invocations_failure")
            metrics_collector.increment_counter(f"tool_{tool_name}_invocations_failure")
            metrics_collector.increment_counter(f"agent_{agent_id}_tool_invocations_failure")
        
        # Track invocation time
        metrics_collector.observe_histogram("tool_invocation_time", duration_ms)
        metrics_collector.observe_histogram(f"tool_{tool_name}_invocation_time", duration_ms)
        metrics_collector.observe_histogram(f"agent_{agent_id}_tool_invocation_time", duration_ms)
    
    @classmethod
    def track_llm_call(
        cls,
        metrics_collector: MetricsCollector,
        llm_model: str,
        agent_id: str,
        tokens_in: int,
        tokens_out: int,
        success: bool,
        duration_ms: float
    ) -> None:
        """
        Track metrics related to LLM API calls.
        
        Args:
            metrics_collector: The MetricsCollector to use for tracking.
            llm_model: The name/version of the LLM model.
            agent_id: The ID of the agent making the call.
            tokens_in: The number of input tokens.
            tokens_out: The number of output tokens.
            success: Whether the call was successful.
            duration_ms: The duration of the call in milliseconds.
        """
        if not metrics_collector.enabled:
            return
        
        # Track total LLM calls
        metrics_collector.increment_counter("llm_calls")
        
        # Track calls by model
        metrics_collector.increment_counter(f"llm_{llm_model}_calls")
        
        # Track calls by agent
        metrics_collector.increment_counter(f"agent_{agent_id}_llm_calls")
        
        # Track success/failure
        if success:
            metrics_collector.increment_counter("llm_calls_success")
            metrics_collector.increment_counter(f"llm_{llm_model}_calls_success")
            metrics_collector.increment_counter(f"agent_{agent_id}_llm_calls_success")
        else:
            metrics_collector.increment_counter("llm_calls_failure")
            metrics_collector.increment_counter(f"llm_{llm_model}_calls_failure")
            metrics_collector.increment_counter(f"agent_{agent_id}_llm_calls_failure")
        
        # Track call time
        metrics_collector.observe_histogram("llm_call_time", duration_ms)
        metrics_collector.observe_histogram(f"llm_{llm_model}_call_time", duration_ms)
        metrics_collector.observe_histogram(f"agent_{agent_id}_llm_call_time", duration_ms)
        
        # Track token usage
        metrics_collector.increment_counter("llm_tokens_in", tokens_in)
        metrics_collector.increment_counter("llm_tokens_out", tokens_out)
        metrics_collector.increment_counter(f"llm_{llm_model}_tokens_in", tokens_in)
        metrics_collector.increment_counter(f"llm_{llm_model}_tokens_out", tokens_out)
        metrics_collector.increment_counter(f"agent_{agent_id}_llm_tokens_in", tokens_in)
        metrics_collector.increment_counter(f"agent_{agent_id}_llm_tokens_out", tokens_out)
    
    @classmethod
    def track_task_execution(
        cls,
        metrics_collector: MetricsCollector,
        task_id: str,
        agent_id: str,
        success: bool,
        duration_ms: float
    ) -> None:
        """
        Track metrics related to task execution.
        
        Args:
            metrics_collector: The MetricsCollector to use for tracking.
            task_id: The ID of the task.
            agent_id: The ID of the agent executing the task.
            success: Whether the execution was successful.
            duration_ms: The duration of the execution in milliseconds.
        """
        if not metrics_collector.enabled:
            return
        
        # Track total tasks executed
        metrics_collector.increment_counter("tasks_executed")
        
        # Track tasks by agent
        metrics_collector.increment_counter(f"agent_{agent_id}_tasks_executed")
        
        # Track success/failure
        if success:
            metrics_collector.increment_counter("tasks_success")
            metrics_collector.increment_counter(f"agent_{agent_id}_tasks_success")
        else:
            metrics_collector.increment_counter("tasks_failure")
            metrics_collector.increment_counter(f"agent_{agent_id}_tasks_failure")
        
        # Track execution time
        metrics_collector.observe_histogram("task_execution_time", duration_ms)
        metrics_collector.observe_histogram(f"agent_{agent_id}_task_execution_time", duration_ms)
