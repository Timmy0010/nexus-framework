# Nexus Framework Observability Example

This example demonstrates the comprehensive observability features of the Nexus Framework:

1. **Distributed Tracing** - Track requests as they flow through the system
2. **Structured Logging** - Enhanced logging with context and correlation
3. **Metrics Collection** - Measurements of system behavior and performance

## Overview

The observability components in Nexus Framework provide:

- Complete request lifecycle visibility
- Correlation between logs, traces, and metrics
- Performance monitoring and troubleshooting
- Health and operational insights

## Observability Components

### Distributed Tracing

The tracing system uses OpenTelemetry to provide distributed tracing capabilities:

- Track request flows across system boundaries
- Measure latency at each step
- Visualize execution paths
- Identify bottlenecks and errors

### Structured Logging

The enhanced logging system provides:

- JSON-formatted logs for better parsing
- Context propagation (trace IDs, correlation IDs)
- Structured data for easier filtering and analysis
- Integration with log aggregation systems

### Metrics Collection

The metrics collection system tracks:

- Counters for operations and events
- Gauges for current state values
- Histograms for measuring distributions
- Tagged dimensions for detailed analysis

## Running the Example

To run the example, make sure you have the required dependencies:

```bash
pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp
```

Then run the example script:

```bash
python observability_demo.py
```

## Example Output

The example demonstrates:

1. Creating and processing mock messages with trace context
2. Recording metrics for message processing and tool invocation
3. Logging with structured data and trace correlation
4. Exporting metrics to JSON for visualization

## Integrating Observability in Your Application

To add observability to your Nexus Framework application:

### 1. Initialize Components

```python
# Initialize tracing
tracing_manager = TracingManager(service_name="your-service")

# Initialize metrics
metrics_collector = MetricsCollector()

# Initialize logging
configure_logging(json_logs=True, log_file="application.log")
```

### 2. Add Tracing to Functions

```python
# Using decorator
@tracing_manager.trace_function()
def your_function():
    # Function code

# Using context manager
with tracing_manager.trace_context("operation_name"):
    # Your code
```

### 3. Record Metrics

```python
# Increment counters
metrics_collector.increment_counter("operation_count", tags={"service": "auth"})

# Set gauge values
metrics_collector.set_gauge("queue_depth", queue.size())

# Record histogram values
metrics_collector.observe_histogram("response_time", duration_ms)

# Using context manager for timing
with metrics_context(metrics_collector, "operation_time"):
    # Your code
```

### 4. Use Structured Logging

```python
# Add context to logs
with log_context(user_id="user123", request_id="req456"):
    logger.info("Processing request")

# Log with structured data
logger.info_structure(
    "User authenticated", 
    {
        "user_id": "user123",
        "auth_method": "oauth"
    }
)
```

### 5. Correlate Data

The observability components automatically correlate logs, traces, and metrics using:

- Trace IDs included in logs
- Correlation IDs for request tracking
- Common tags/dimensions across metrics

## Dashboard Integration

The observability components can export data to popular monitoring systems:

- **Jaeger** or **Zipkin** for distributed tracing visualization
- **Prometheus** for metrics collection and alerting
- **ELK Stack** (Elasticsearch, Logstash, Kibana) for log aggregation

See the Nexus Framework documentation for detailed setup instructions.
