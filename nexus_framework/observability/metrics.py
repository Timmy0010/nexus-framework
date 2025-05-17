"""
Metrics collection utilities for the Nexus framework.

This module provides utilities for collecting and tracking metrics
related to agent performance and system health within the Nexus framework.
It includes integration with OpenTelemetry for metrics export and
dashboard capabilities.
"""

import logging
import time
import threading
import statistics
import math
import os
import json
import collections
from typing import Dict, Optional, Any, List, Callable, Union, Deque, Set, Tuple, Iterator
from enum import Enum
from dataclasses import dataclass, field, asdict
from datetime import datetime
from contextlib import contextmanager
from functools import wraps

# Set up logging
logger = logging.getLogger(__name__)

# Try to import OpenTelemetry metrics
try:
    from opentelemetry import metrics
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import (
        PeriodicExportingMetricReader,
        ConsoleMetricExporter
    )
    from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
    from opentelemetry.sdk.resources import SERVICE_NAME, Resource
    
    OPENTELEMETRY_AVAILABLE = True
except ImportError:
    OPENTELEMETRY_AVAILABLE = False
    logger.warning(
        "OpenTelemetry metrics packages not found. Using fallback metrics implementation. "
        "Install with 'pip install opentelemetry-api opentelemetry-sdk "
        "opentelemetry-exporter-otlp' for full metrics capabilities."
    )

# Default service name
DEFAULT_SERVICE_NAME = "nexus-framework"

# Types of metrics
class MetricType(Enum):
    """Types of metrics supported by the metrics system."""
    COUNTER = "counter"  # Monotonically increasing value
    GAUGE = "gauge"      # Current value that can go up or down
    HISTOGRAM = "histogram"  # Distribution of values


@dataclass
class MetricDefinition:
    """Definition of a metric for standard reporting."""
    name: str
    type: MetricType
    description: str
    unit: str = ""
    tags: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = asdict(self)
        result["type"] = self.type.value
        return result


class MetricsCollector:
    """
    Collects and manages metrics for the Nexus framework.
    
    This class provides utilities for tracking various metrics related to
    agent performance, system health, and usage statistics.
    """
    
    def __init__(self):
        """Initialize a new metrics collector."""
        # Whether metrics collection is enabled
        self.enabled = True
        
        # Counters for various metrics
        self._counters: Dict[str, Dict[str, int]] = {}
        
        # Gauges for current values
        self._gauges: Dict[str, Dict[str, float]] = {}
        
        # Histograms for value distributions
        self._histograms: Dict[str, Dict[str, List[float]]] = {}
        
        # Metric definitions
        self._definitions: Dict[str, MetricDefinition] = {}
        
        # OpenTelemetry integration
        self._otel_meter = None
        self._otel_metrics = {}
        
        # Initialize OpenTelemetry if available
        if OPENTELEMETRY_AVAILABLE:
            # Create a resource to identify the service
            resource = Resource(attributes={
                SERVICE_NAME: DEFAULT_SERVICE_NAME
            })
            
            # Create meter provider
            reader = PeriodicExportingMetricReader(ConsoleMetricExporter())
            provider = MeterProvider(resource=resource, metric_readers=[reader])
            metrics.set_meter_provider(provider)
            
            # Get meter
            self._otel_meter = metrics.get_meter(__name__, "1.0.0")
            logger.info("OpenTelemetry metrics initialized")
        
        # Lock for thread safety
        self._lock = threading.Lock()
    
    def _get_or_create_counter(self, name: str, description: str = "") -> None:
        """
        Get or create a counter by name.
        
        Args:
            name: Name of the counter
            description: Description of the counter
        """
        with self._lock:
            if name not in self._counters:
                self._counters[name] = {}
                
                # Register definition
                if name not in self._definitions:
                    self._definitions[name] = MetricDefinition(
                        name=name,
                        type=MetricType.COUNTER,
                        description=description
                    )
                
                # Create OpenTelemetry counter if available
                if OPENTELEMETRY_AVAILABLE and self._otel_meter and name not in self._otel_metrics:
                    self._otel_metrics[name] = self._otel_meter.create_counter(
                        name=name,
                        description=description or f"Counter metric: {name}"
                    )
    
    def _get_or_create_gauge(self, name: str, description: str = "") -> None:
        """
        Get or create a gauge by name.
        
        Args:
            name: Name of the gauge
            description: Description of the gauge
        """
        with self._lock:
            if name not in self._gauges:
                self._gauges[name] = {}
                
                # Register definition
                if name not in self._definitions:
                    self._definitions[name] = MetricDefinition(
                        name=name,
                        type=MetricType.GAUGE,
                        description=description
                    )
    
    def _get_or_create_histogram(self, name: str, description: str = "", unit: str = "") -> None:
        """
        Get or create a histogram by name.
        
        Args:
            name: Name of the histogram
            description: Description of the histogram
            unit: Unit of measurement
        """
        with self._lock:
            if name not in self._histograms:
                self._histograms[name] = {}
                
                # Register definition
                if name not in self._definitions:
                    self._definitions[name] = MetricDefinition(
                        name=name,
                        type=MetricType.HISTOGRAM,
                        description=description,
                        unit=unit
                    )
                
                # Create OpenTelemetry histogram if available
                if OPENTELEMETRY_AVAILABLE and self._otel_meter and name not in self._otel_metrics:
                    self._otel_metrics[name] = self._otel_meter.create_histogram(
                        name=name,
                        description=description or f"Histogram metric: {name}",
                        unit=unit
                    )
    
    def _get_tag_key(self, tags: Optional[Dict[str, str]] = None) -> str:
        """
        Convert tags dictionary to a string key for storage.
        
        Args:
            tags: Dictionary of tags or None
            
        Returns:
            String key for the tags
        """
        if not tags:
            return "default"
        
        return ".".join(f"{k}={v}" for k, v in sorted(tags.items()))
    
    def increment_counter(
        self, 
        name: str, 
        value: int = 1, 
        tags: Optional[Dict[str, str]] = None,
        description: str = ""
    ) -> None:
        """
        Increment a counter metric.
        
        Args:
            name: Name of the counter
            value: Amount to increment by
            tags: Optional dictionary of tags
            description: Description of the counter
        """
        if not self.enabled:
            return
        
        # Get or create the counter
        self._get_or_create_counter(name, description)
        
        # Convert tags to string key
        tag_key = self._get_tag_key(tags)
        
        with self._lock:
            # Initialize counter for this tag combination if needed
            if tag_key not in self._counters[name]:
                self._counters[name][tag_key] = 0
            
            # Increment the counter
            self._counters[name][tag_key] += value
            
            # Update OpenTelemetry counter if available
            if OPENTELEMETRY_AVAILABLE and name in self._otel_metrics:
                self._otel_metrics[name].add(value, tags or {})
    
    def set_gauge(
        self, 
        name: str, 
        value: float, 
        tags: Optional[Dict[str, str]] = None,
        description: str = ""
    ) -> None:
        """
        Set a gauge metric to a specific value.
        
        Args:
            name: Name of the gauge
            value: Value to set
            tags: Optional dictionary of tags
            description: Description of the gauge
        """
        if not self.enabled:
            return
        
        # Get or create the gauge
        self._get_or_create_gauge(name, description)
        
        # Convert tags to string key
        tag_key = self._get_tag_key(tags)
        
        with self._lock:
            self._gauges[name][tag_key] = value
    
    def observe_histogram(
        self, 
        name: str, 
        value: float, 
        tags: Optional[Dict[str, str]] = None,
        description: str = "",
        unit: str = ""
    ) -> None:
        """
        Add a value observation to a histogram metric.
        
        Args:
            name: Name of the histogram
            value: Value to observe
            tags: Optional dictionary of tags
            description: Description of the histogram
            unit: Unit of measurement
        """
        if not self.enabled:
            return
        
        # Get or create the histogram
        self._get_or_create_histogram(name, description, unit)
        
        # Convert tags to string key
        tag_key = self._get_tag_key(tags)
        
        with self._lock:
            # Initialize histogram for this tag combination if needed
            if tag_key not in self._histograms[name]:
                self._histograms[name][tag_key] = []
            
            # Add the observation
            self._histograms[name][tag_key].append(value)
            
            # Trim to keep a reasonable history size
            if len(self._histograms[name][tag_key]) > 1000:
                self._histograms[name][tag_key] = self._histograms[name][tag_key][-1000:]
            
            # Update OpenTelemetry histogram if available
            if OPENTELEMETRY_AVAILABLE and name in self._otel_metrics:
                self._otel_metrics[name].record(value, tags or {})
    
    def get_counter(self, name: str, tags: Optional[Dict[str, str]] = None) -> int:
        """
        Get the current value of a counter metric.
        
        Args:
            name: Name of the counter
            tags: Optional dictionary of tags
            
        Returns:
            The current value of the counter, or 0 if it doesn't exist
        """
        if not self.enabled or name not in self._counters:
            return 0
        
        tag_key = self._get_tag_key(tags)
        
        with self._lock:
            return self._counters[name].get(tag_key, 0)
    
    def get_gauge(self, name: str, tags: Optional[Dict[str, str]] = None) -> float:
        """
        Get the current value of a gauge metric.
        
        Args:
            name: Name of the gauge
            tags: Optional dictionary of tags
            
        Returns:
            The current value of the gauge, or 0.0 if it doesn't exist
        """
        if not self.enabled or name not in self._gauges:
            return 0.0
        
        tag_key = self._get_tag_key(tags)
        
        with self._lock:
            return self._gauges[name].get(tag_key, 0.0)
    
    def get_histogram_stats(
        self, 
        name: str, 
        tags: Optional[Dict[str, str]] = None
    ) -> Dict[str, float]:
        """
        Get statistics for a histogram metric.
        
        Args:
            name: Name of the histogram
            tags: Optional dictionary of tags
            
        Returns:
            Dictionary of statistics (count, min, max, mean, p95, etc.)
        """
        if not self.enabled or name not in self._histograms:
            return {
                "count": 0,
                "min": 0.0,
                "max": 0.0,
                "mean": 0.0,
                "p95": 0.0
            }
        
        tag_key = self._get_tag_key(tags)
        
        with self._lock:
            if tag_key not in self._histograms[name] or not self._histograms[name][tag_key]:
                return {
                    "count": 0,
                    "min": 0.0,
                    "max": 0.0,
                    "mean": 0.0,
                    "p95": 0.0
                }
            
            values = self._histograms[name][tag_key]
            
            result = {
                "count": len(values),
                "min": min(values),
                "max": max(values),
                "mean": statistics.mean(values)
            }
            
            # Calculate percentiles if enough data points
            if len(values) >= 10:
                sorted_values = sorted(values)
                p95_index = int(len(sorted_values) * 0.95)
                result["p95"] = sorted_values[p95_index]
            else:
                result["p95"] = result["max"]
            
            return result
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """
        Get all metrics data.
        
        Returns:
            Dictionary containing all metrics data
        """
        if not self.enabled:
            return {}
        
        with self._lock:
            result = {
                "counters": {},
                "gauges": {},
                "histograms": {}
            }
            
            # Copy counters
            for name, counters in self._counters.items():
                result["counters"][name] = counters.copy()
            
            # Copy gauges
            for name, gauges in self._gauges.items():
                result["gauges"][name] = gauges.copy()
            
            # Compute histogram statistics
            for name, histograms in self._histograms.items():
                result["histograms"][name] = {}
                for tag_key, values in histograms.items():
                    if not values:
                        continue
                    
                    # Calculate basic statistics
                    stats = {
                        "count": len(values),
                        "min": min(values),
                        "max": max(values),
                        "mean": statistics.mean(values)
                    }
                    
                    # Calculate percentiles if enough data
                    if len(values) >= 10:
                        sorted_values = sorted(values)
                        p95_index = int(len(sorted_values) * 0.95)
                        stats["p95"] = sorted_values[p95_index]
                    else:
                        stats["p95"] = stats["max"]
                    
                    result["histograms"][name][tag_key] = stats
            
            return result
    
    def get_all_definitions(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all metric definitions.
        
        Returns:
            Dictionary of metric definitions
        """
        with self._lock:
            return {name: defn.to_dict() for name, defn in self._definitions.items()}
    
    def save_metrics_to_file(self, filename: str) -> None:
        """
        Save current metrics to a JSON file.
        
        Args:
            filename: Path to the output file
        """
        metrics_data = {
            "timestamp": datetime.now().isoformat(),
            "metrics": self.get_all_metrics(),
            "definitions": self.get_all_definitions()
        }
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)
        
        with open(filename, 'w') as f:
            json.dump(metrics_data, f, indent=2)
            
        logger.info(f"Saved metrics to {filename}")
    
    def clear_metrics(self) -> None:
        """Clear all metrics."""
        with self._lock:
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()
    
    def track_function_execution_time(self, name: str) -> Callable:
        """
        Decorator to track the execution time of a function.
        
        Args:
            name: The prefix for the metrics names
            
        Returns:
            A decorator function
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                if not self.enabled:
                    return func(*args, **kwargs)
                
                # Track function calls
                self.increment_counter(
                    f"{name}_calls",
                    description=f"Number of calls to {func.__name__}"
                )
                
                # Track execution time
                start_time = time.time()
                
                try:
                    result = func(*args, **kwargs)
                    
                    # Track successful executions
                    self.increment_counter(
                        f"{name}_success",
                        description=f"Number of successful executions of {func.__name__}"
                    )
                    
                    return result
                
                except Exception:
                    # Track failures
                    self.increment_counter(
                        f"{name}_failure",
                        description=f"Number of failed executions of {func.__name__}"
                    )
                    
                    # Re-raise the exception
                    raise
                
                finally:
                    # Record execution time
                    execution_time = time.time() - start_time
                    self.observe_histogram(
                        f"{name}_time",
                        execution_time * 1000,  # Convert to ms
                        description=f"Execution time of {func.__name__}",
                        unit="ms"
                    )
            
            return wrapper
        
        return decorator


@contextmanager
def metrics_context(
    metrics_collector: MetricsCollector,
    name: str,
    tags: Optional[Dict[str, str]] = None
) -> Iterator[None]:
    """
    Context manager for tracking execution time of a block of code.
    
    Args:
        metrics_collector: The MetricsCollector to use for tracking
        name: The name of the metric to record
        tags: Optional dictionary of tags
        
    Yields:
        Nothing, just provides context
    """
    if not metrics_collector.enabled:
        yield
        return
    
    # Increment executions counter
    metrics_collector.increment_counter(
        f"{name}_executions",
        tags=tags,
        description=f"Number of executions of {name}"
    )
    
    # Track execution time
    start_time = time.time()
    
    try:
        # Execute the block
        yield
        
        # Track success
        metrics_collector.increment_counter(
            f"{name}_successes",
            tags=tags,
            description=f"Number of successful executions of {name}"
        )
    
    except Exception:
        # Track failure
        metrics_collector.increment_counter(
            f"{name}_failures",
            tags=tags,
            description=f"Number of failed executions of {name}"
        )
        
        # Re-raise the exception
        raise
    
    finally:
        # Record execution time
        execution_time = time.time() - start_time
        metrics_collector.observe_histogram(
            f"{name}_time",
            execution_time * 1000,  # Convert to ms
            tags=tags,
            description=f"Execution time of {name}",
            unit="ms"
        )


class CommonMetrics:
    """
    Common metrics related to agents and tools in the Nexus framework.
    
    This class provides utility methods for tracking common metrics
    within the framework.
    """
    
    @staticmethod
    def track_agent_message_processing(
        metrics_collector: MetricsCollector,
        agent_id: str,
        message_content_type: str,
        success: bool,
        duration_ms: float
    ) -> None:
        """
        Track metrics related to agent message processing.
        
        Args:
            metrics_collector: The MetricsCollector to use for tracking
            agent_id: The ID of the agent
            message_content_type: The content type of the message
            success: Whether the processing was successful
            duration_ms: The duration of the processing in milliseconds
        """
        if not metrics_collector.enabled:
            return
        
        # Track total messages processed
        metrics_collector.increment_counter(
            "agent_messages_processed",
            description="Total number of messages processed by agents"
        )
        
        # Track messages by agent
        metrics_collector.increment_counter(
            f"agent_{agent_id}_messages_processed",
            description=f"Messages processed by agent {agent_id}"
        )
        
        # Track messages by content type
        metrics_collector.increment_counter(
            f"message_type_{message_content_type}_processed",
            description=f"Messages of type {message_content_type} processed"
        )
        
        # Track success/failure
        if success:
            metrics_collector.increment_counter(
                "agent_messages_success",
                description="Successfully processed messages"
            )
            metrics_collector.increment_counter(
                f"agent_{agent_id}_messages_success",
                description=f"Messages successfully processed by agent {agent_id}"
            )
        else:
            metrics_collector.increment_counter(
                "agent_messages_failure",
                description="Failed message processing attempts"
            )
            metrics_collector.increment_counter(
                f"agent_{agent_id}_messages_failure",
                description=f"Messages that failed processing by agent {agent_id}"
            )
        
        # Track processing time
        metrics_collector.observe_histogram(
            "agent_message_processing_time",
            duration_ms,
            description="Time to process a message",
            unit="ms"
        )
        metrics_collector.observe_histogram(
            f"agent_{agent_id}_processing_time",
            duration_ms,
            description=f"Time for agent {agent_id} to process a message",
            unit="ms"
        )
    
    @staticmethod
    def track_tool_invocation(
        metrics_collector: MetricsCollector,
        tool_name: str,
        agent_id: str,
        success: bool,
        duration_ms: float
    ) -> None:
        """
        Track metrics related to tool invocation.
        
        Args:
            metrics_collector: The MetricsCollector to use for tracking
            tool_name: The name of the tool
            agent_id: The ID of the agent invoking the tool
            success: Whether the invocation was successful
            duration_ms: The duration of the invocation in milliseconds
        """
        if not metrics_collector.enabled:
            return
        
        # Track total tool invocations
        metrics_collector.increment_counter(
            "tool_invocations",
            description="Total number of tool invocations"
        )
        
        # Track invocations by tool
        metrics_collector.increment_counter(
            f"tool_{tool_name}_invocations",
            description=f"Invocations of tool {tool_name}"
        )
        
        # Track invocations by agent
        metrics_collector.increment_counter(
            f"agent_{agent_id}_tool_invocations",
            description=f"Tool invocations by agent {agent_id}"
        )
        
        # Track success/failure
        if success:
            metrics_collector.increment_counter(
                "tool_invocations_success",
                description="Successful tool invocations"
            )
            metrics_collector.increment_counter(
                f"tool_{tool_name}_invocations_success",
                description=f"Successful invocations of tool {tool_name}"
            )
        else:
            metrics_collector.increment_counter(
                "tool_invocations_failure",
                description="Failed tool invocations"
            )
            metrics_collector.increment_counter(
                f"tool_{tool_name}_invocations_failure",
                description=f"Failed invocations of tool {tool_name}"
            )
        
        # Track invocation time
        metrics_collector.observe_histogram(
            "tool_invocation_time",
            duration_ms,
            description="Time to invoke a tool",
            unit="ms"
        )
        metrics_collector.observe_histogram(
            f"tool_{tool_name}_invocation_time",
            duration_ms,
            description=f"Time to invoke tool {tool_name}",
            unit="ms"
        )
