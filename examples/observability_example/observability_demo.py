"""
Example demonstrating the Observability features of the Nexus Framework.

This script shows how to use the Tracing, Metrics, and Structured Logging 
components for comprehensive observability in the Nexus Framework.
"""

import logging
import time
import random
import os
import sys
import json
import uuid
import threading
from typing import Dict, Any, List, Optional
from datetime import datetime

# Add the parent directory to the Python path to allow importing
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import Nexus Framework observability components
from nexus_framework.observability.tracing import TracingManager
from nexus_framework.observability.metrics import MetricsCollector, metrics_context
from nexus_framework.observability.logging_config import (
    configure_logging, 
    log_context, 
    log_event,
    JsonFormatter
)

# Import core message components for demonstration
from nexus_framework.core.message import Message


def print_separator(title: str = None):
    """Print a separator line for better readability."""
    width = 80
    if title:
        padding = (width - len(title) - 4) // 2
        print("\n" + "=" * padding + f"[ {title} ]" + "=" * padding + "\n")
    else:
        print("\n" + "=" * width + "\n")


class MockAgent:
    """
    Mock agent for demonstrating observability features.
    
    This simulates a simple agent that can process messages with
    different observability instrumentation.
    """
    
    def __init__(
        self, 
        agent_id: str, 
        tracing_manager: TracingManager, 
        metrics_collector: MetricsCollector,
        logger: logging.Logger
    ):
        """
        Initialize the mock agent.
        
        Args:
            agent_id: ID of the agent
            tracing_manager: Tracing manager for trace context
            metrics_collector: Metrics collector for recording metrics
            logger: Logger for structured logging
        """
        self.agent_id = agent_id
        self.tracing_manager = tracing_manager
        self.metrics_collector = metrics_collector
        self.logger = logger
        
        # Simple state for demonstration
        self.messages_processed = 0
        self.successful_messages = 0
        self.failed_messages = 0
    
    @property
    def success_rate(self) -> float:
        """Calculate the success rate of message processing."""
        if self.messages_processed == 0:
            return 0.0
        return self.successful_messages / self.messages_processed
    
    # Decorate with tracing to automatically create trace spans
    @tracing_manager.trace_method()
    def process_message(self, message: Message) -> bool:
        """
        Process a message with full observability instrumentation.
        
        Args:
            message: The message to process
            
        Returns:
            True if processing was successful, False otherwise
        """
        # Start a trace span and get the current trace ID
        start_time = time.time()
        
        # Use structured logging with context
        with log_context(agent_id=self.agent_id, message_id=message.message_id):
            self.logger.info(f"Processing message: {message.message_id} from {message.sender_id}")
            
            # Add trace context to logs
            trace_id = self.tracing_manager.add_span_tag(
                self.tracing_manager.get_current_span(),
                "message_id", 
                message.message_id
            )
            
            # Simulate processing time
            processing_time = random.uniform(0.05, 0.3)  # 50-300ms
            time.sleep(processing_time)
            
            # Simulate occasional failures
            self.messages_processed += 1
            success = random.random() > 0.2  # 20% failure rate
            
            if success:
                self.successful_messages += 1
                self.logger.info(f"Successfully processed message: {message.message_id}")
                
                # Add success event to trace
                self.tracing_manager.add_span_event(
                    self.tracing_manager.get_current_span(),
                    "message_processed",
                    {"outcome": "success", "processing_time_ms": processing_time * 1000}
                )
            else:
                self.failed_messages += 1
                error_reason = random.choice(["validation_error", "timeout", "processing_error"])
                
                # Log error with structured data
                self.logger.error_structure(
                    f"Failed to process message: {message.message_id}",
                    {
                        "error_reason": error_reason,
                        "message_type": message.message_type,
                        "processing_time_ms": processing_time * 1000
                    }
                )
                
                # Add failure event to trace
                self.tracing_manager.add_span_event(
                    self.tracing_manager.get_current_span(),
                    "message_processing_failed",
                    {"error_reason": error_reason, "processing_time_ms": processing_time * 1000}
                )
            
            # Record metrics
            duration_ms = (time.time() - start_time) * 1000
            self.metrics_collector.increment_counter(
                "messages_processed", 
                tags={"agent_id": self.agent_id, "message_type": message.message_type}
            )
            
            if success:
                self.metrics_collector.increment_counter(
                    "messages_success", 
                    tags={"agent_id": self.agent_id, "message_type": message.message_type}
                )
            else:
                self.metrics_collector.increment_counter(
                    "messages_failure", 
                    tags={"agent_id": self.agent_id, "message_type": message.message_type}
                )
            
            self.metrics_collector.observe_histogram(
                "message_processing_time",
                duration_ms,
                tags={"agent_id": self.agent_id, "message_type": message.message_type}
            )
            
            return success
    
    # A simpler method that uses the metrics_context manager
    def invoke_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Invoke a mock tool with metrics tracking.
        
        Args:
            tool_name: Name of the tool to invoke
            params: Parameters for the tool
            
        Returns:
            Tool result
        """
        # Use metrics_context for automatic timing and success/failure tracking
        with metrics_context(
            self.metrics_collector, 
            "tool_invocation", 
            tags={"agent_id": self.agent_id, "tool_name": tool_name}
        ):
            self.logger.info(f"Invoking tool: {tool_name}")
            
            # Simulate tool processing
            time.sleep(random.uniform(0.1, 0.5))
            
            # Generate result
            result = {
                "tool": tool_name,
                "timestamp": datetime.now().isoformat(),
                "result": f"Result of {tool_name} with {len(params)} parameters"
            }
            
            self.logger.info(f"Tool {tool_name} invocation completed")
            return result


def create_test_messages(count: int = 10) -> List[Message]:
    """Create a list of test messages with different types."""
    message_types = ["text", "command", "query", "event"]
    
    messages = []
    for i in range(count):
        msg_type = random.choice(message_types)
        messages.append(Message(
            message_id=str(uuid.uuid4()),
            sender_id=f"sender-{random.randint(1, 5)}",
            recipient_id=f"recipient-{random.randint(1, 3)}",
            content=f"Test message {i+1}",
            message_type=msg_type,
            metadata={
                "priority": random.choice(["high", "medium", "low"]),
                "timestamp": datetime.now().isoformat()
            }
        ))
    
    return messages


def background_metrics_reporter(
    metrics_collector: MetricsCollector, 
    stop_event: threading.Event,
    interval: float = 5.0
):
    """
    Background thread that periodically reports metrics.
    
    Args:
        metrics_collector: Metrics collector to report from
        stop_event: Event to signal thread to stop
        interval: Reporting interval in seconds
    """
    logger = logging.getLogger("metrics_reporter")
    
    while not stop_event.is_set():
        # Get all metrics data
        metrics_data = metrics_collector.get_all_metrics()
        
        # Log summary
        logger.info("----- Metrics Summary -----")
        
        # Report counters
        if "counters" in metrics_data:
            for name, values in metrics_data["counters"].items():
                for tag_key, value in values.items():
                    logger.info(f"Counter: {name} [{tag_key}] = {value}")
        
        # Report histograms
        if "histograms" in metrics_data:
            for name, values in metrics_data["histograms"].items():
                for tag_key, stats in values.items():
                    logger.info(
                        f"Histogram: {name} [{tag_key}] = "
                        f"count={stats.get('count', 0)}, "
                        f"mean={stats.get('mean', 0):.2f}, "
                        f"p95={stats.get('p95', 0):.2f}"
                    )
        
        logger.info("---------------------------")
        
        # Wait for next interval or until stopped
        stop_event.wait(interval)


def main():
    """Run the observability example."""
    print_separator("Nexus Framework Observability Example")
    
    # Initialize logging
    configure_logging(
        log_level=logging.INFO,
        log_file="observability_example.log",
        console=True,
        json_logs=True
    )
    
    logger = logging.getLogger("observability_example")
    logger.info("Starting Observability Example")
    
    # Initialize tracing
    tracing_manager = TracingManager(
        service_name="observability-example",
        enable_console_export=True
    )
    logger.info("Initialized tracing manager")
    
    # Initialize metrics collection
    metrics_collector = MetricsCollector()
    logger.info("Initialized metrics collector")
    
    # Create mock agents
    agents = [
        MockAgent("agent-1", tracing_manager, metrics_collector, logging.getLogger("agent-1")),
        MockAgent("agent-2", tracing_manager, metrics_collector, logging.getLogger("agent-2"))
    ]
    logger.info(f"Created {len(agents)} mock agents")
    
    # Create test messages
    messages = create_test_messages(20)
    logger.info(f"Created {len(messages)} test messages")
    
    # Start metrics reporter thread
    stop_reporter = threading.Event()
    reporter_thread = threading.Thread(
        target=background_metrics_reporter, 
        args=(metrics_collector, stop_reporter)
    )
    reporter_thread.daemon = True
    reporter_thread.start()
    
    # Process messages with tracing
    print_separator("Processing Messages")
    
    with tracing_manager.trace_context("process_all_messages"):
        for i, message in enumerate(messages):
            # Log with trace correlation
            logger.info(f"Processing message {i+1}/{len(messages)}")
            
            # Select an agent
            agent = random.choice(agents)
            
            # Process the message (with automatic tracing via decorator)
            success = agent.process_message(message)
            
            # Occasionally invoke a tool
            if random.random() < 0.3:
                tool_name = random.choice(["calculator", "translator", "search", "validator"])
                agent.invoke_tool(tool_name, {"param1": "value1", "param2": "value2"})
            
            # Add a small delay between messages
            time.sleep(random.uniform(0.1, 0.3))
    
    # Stop the metrics reporter
    stop_reporter.set()
    reporter_thread.join(timeout=1.0)
    
    # Summarize results
    print_separator("Results Summary")
    
    # Log agent statistics
    for agent in agents:
        logger.info(
            f"Agent {agent.agent_id}: "
            f"Processed {agent.messages_processed} messages, "
            f"Success rate: {agent.success_rate:.1%}"
        )
    
    # Save metrics to file
    metrics_file = "observability_metrics.json"
    metrics_collector.save_metrics_to_file(metrics_file)
    logger.info(f"Saved metrics to {metrics_file}")
    
    print_separator("Example Complete")
    logger.info("Observability example completed successfully")


if __name__ == "__main__":
    main()
