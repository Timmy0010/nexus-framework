"""
Tracing utilities for the Nexus framework.

This module provides utilities for distributed tracing and monitoring
of agent activities within the Nexus framework.
"""

import logging
import time
import uuid
from typing import Dict, Optional, Any, List, Callable, TypeVar, Generic
from functools import wraps
from datetime import datetime

# Set up logging
logger = logging.getLogger(__name__)

# Define a type variable for generic functions
T = TypeVar('T')


class TracingManager:
    """
    Manages distributed tracing for the Nexus framework.
    
    This is a placeholder for future integration with OpenTelemetry.
    For now, it provides basic tracing capabilities through logging.
    """
    
    def __init__(self):
        """Initialize a new tracing manager."""
        # Maps trace_id -> span_id -> span_data
        self._traces: Dict[str, Dict[str, Dict[str, Any]]] = {}
        
        # Whether tracing is enabled
        self.enabled = True
    
    def start_trace(self, operation_name: str) -> str:
        """
        Start a new trace.
        
        Args:
            operation_name: The name of the operation being traced.
            
        Returns:
            The ID of the created trace.
        """
        if not self.enabled:
            return ""
        
        trace_id = str(uuid.uuid4())
        span_id = str(uuid.uuid4())
        
        span_data = {
            "operation_name": operation_name,
            "span_id": span_id,
            "parent_span_id": None,
            "trace_id": trace_id,
            "start_time": time.time(),
            "end_time": None,
            "status": "started",
            "events": [],
            "tags": {}
        }
        
        self._traces[trace_id] = {span_id: span_data}
        
        logger.debug(f"Started trace: {trace_id} for operation: {operation_name}")
        
        return trace_id
    
    def start_span(
        self, 
        operation_name: str, 
        trace_id: str, 
        parent_span_id: Optional[str] = None
    ) -> str:
        """
        Start a new span within an existing trace.
        
        Args:
            operation_name: The name of the operation being traced.
            trace_id: The ID of the trace to add the span to.
            parent_span_id: Optional ID of the parent span.
            
        Returns:
            The ID of the created span.
        """
        if not self.enabled or not trace_id or trace_id not in self._traces:
            return ""
        
        span_id = str(uuid.uuid4())
        
        span_data = {
            "operation_name": operation_name,
            "span_id": span_id,
            "parent_span_id": parent_span_id,
            "trace_id": trace_id,
            "start_time": time.time(),
            "end_time": None,
            "status": "started",
            "events": [],
            "tags": {}
        }
        
        self._traces[trace_id][span_id] = span_data
        
        logger.debug(f"Started span: {span_id} for operation: {operation_name} in trace: {trace_id}")
        
        return span_id
    
    def end_span(self, trace_id: str, span_id: str, status: str = "success") -> None:
        """
        End a span.
        
        Args:
            trace_id: The ID of the trace containing the span.
            span_id: The ID of the span to end.
            status: The final status of the span.
        """
        if not self.enabled or not trace_id or not span_id:
            return
        
        if trace_id not in self._traces or span_id not in self._traces[trace_id]:
            logger.warning(f"Tried to end nonexistent span: {span_id} in trace: {trace_id}")
            return
        
        span_data = self._traces[trace_id][span_id]
        span_data["end_time"] = time.time()
        span_data["status"] = status
        
        duration_ms = (span_data["end_time"] - span_data["start_time"]) * 1000
        
        logger.debug(
            f"Ended span: {span_id} for operation: {span_data['operation_name']} "
            f"in trace: {trace_id} with status: {status} (duration: {duration_ms:.2f}ms)"
        )
    
    def add_span_event(
        self, 
        trace_id: str, 
        span_id: str, 
        event_name: str, 
        attributes: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Add an event to a span.
        
        Args:
            trace_id: The ID of the trace containing the span.
            span_id: The ID of the span to add the event to.
            event_name: The name of the event.
            attributes: Optional attributes describing the event.
        """
        if not self.enabled or not trace_id or not span_id:
            return
        
        if trace_id not in self._traces or span_id not in self._traces[trace_id]:
            logger.warning(f"Tried to add event to nonexistent span: {span_id} in trace: {trace_id}")
            return
        
        event = {
            "name": event_name,
            "timestamp": time.time(),
            "attributes": attributes or {}
        }
        
        self._traces[trace_id][span_id]["events"].append(event)
        
        logger.debug(f"Added event: {event_name} to span: {span_id} in trace: {trace_id}")
    
    def add_span_tag(self, trace_id: str, span_id: str, key: str, value: Any) -> None:
        """
        Add a tag to a span.
        
        Args:
            trace_id: The ID of the trace containing the span.
            span_id: The ID of the span to add the tag to.
            key: The key of the tag.
            value: The value of the tag.
        """
        if not self.enabled or not trace_id or not span_id:
            return
        
        if trace_id not in self._traces or span_id not in self._traces[trace_id]:
            logger.warning(f"Tried to add tag to nonexistent span: {span_id} in trace: {trace_id}")
            return
        
        self._traces[trace_id][span_id]["tags"][key] = value
        
        logger.debug(f"Added tag: {key}={value} to span: {span_id} in trace: {trace_id}")
    
    def get_trace(self, trace_id: str) -> Dict[str, Any]:
        """
        Get a trace by its ID.
        
        Args:
            trace_id: The ID of the trace to get.
            
        Returns:
            A dictionary containing all spans in the trace.
        """
        if not self.enabled or not trace_id or trace_id not in self._traces:
            return {}
        
        return self._traces[trace_id]
    
    def get_span(self, trace_id: str, span_id: str) -> Dict[str, Any]:
        """
        Get a span by its ID and trace ID.
        
        Args:
            trace_id: The ID of the trace containing the span.
            span_id: The ID of the span to get.
            
        Returns:
            A dictionary containing the span data.
        """
        if not self.enabled or not trace_id or not span_id:
            return {}
        
        if trace_id not in self._traces or span_id not in self._traces[trace_id]:
            return {}
        
        return self._traces[trace_id][span_id]
    
    def clear_traces(self) -> None:
        """Clear all stored traces."""
        self._traces.clear()
        logger.debug("Cleared all traces")
    
    def trace_function(self, operation_name: Optional[str] = None) -> Callable:
        """
        Decorator to trace a function.
        
        Args:
            operation_name: Optional name for the operation.
                           If not provided, the function name will be used.
            
        Returns:
            A decorator function.
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Skip tracing if disabled
                if not self.enabled:
                    return func(*args, **kwargs)
                
                # Use function name if no operation name provided
                span_name = operation_name or func.__name__
                
                # Handle OpenTelemetry implementation
                if OPENTELEMETRY_AVAILABLE and self._tracer:
                    # Extract attributes from args/kwargs for better context
                    attributes = {}
                    
                    # Exclude self or cls for methods
                    if args and hasattr(args[0], func.__name__):
                        # This is likely a method call, skip the first argument (self/cls)
                        func_args = args[1:]
                    else:
                        func_args = args
                    
                    # Add basic arg/kwarg info as attributes
                    # Be careful not to include sensitive information
                    attributes["args_count"] = len(func_args)
                    attributes["kwargs_keys"] = str(list(kwargs.keys()))
                    
                    # Start a span
                    with self._tracer.start_as_current_span(span_name, attributes=attributes) as span:
                        try:
                            # Execute the function
                            result = func(*args, **kwargs)
                            
                            # Add result info as a span attribute
                            if result is not None:
                                result_type = type(result).__name__
                                span.set_attribute("result_type", result_type)
                            
                            return result
                        
                        except Exception as e:
                            # Record exception
                            span.record_exception(e)
                            span.set_status(StatusCode.ERROR, str(e))
                            raise
                
                else:
                    # Fallback implementation
                    # Start a new trace or use an existing one
                    trace_id = kwargs.pop("trace_id", None) or self.start_trace(span_name)
                    
                    # Start a new span
                    parent_span_id = kwargs.pop("parent_span_id", None)
                    span_id = self.start_span(span_name, trace_id, parent_span_id)
                    
                    try:
                        # Add function arguments as span tags
                        # Exclude self or cls for methods
                        if args and hasattr(args[0], func.__name__):
                            # This is likely a method call, skip the first argument (self/cls)
                            func_args = args[1:]
                        else:
                            func_args = args
                        
                        # Add basic arg/kwarg info as tags
                        self.add_span_tag(span_id, "args_count", len(func_args))
                        self.add_span_tag(span_id, "kwargs_keys", list(kwargs.keys()))
                        
                        # Execute the function
                        result = func(*args, **kwargs)
                        
                        # Add result info as a span tag
                        if result is not None:
                            result_type = type(result).__name__
                            self.add_span_tag(span_id, "result_type", result_type)
                        
                        # End the span with success status
                        self.end_span(span_id, "success")
                        
                        return result
                    
                    except Exception as e:
                        # Add exception info as a span event
                        self.add_span_event(
                            span_id,
                            "exception",
                            {
                                "exception_type": type(e).__name__,
                                "exception_message": str(e)
                            }
                        )
                        
                        # End the span with error status
                        self.end_span(span_id, "error")
                        
                        # Re-raise the exception
                        raise
            
            return wrapper
        
        return decorator
    
    def trace_method(self, operation_name: Optional[str] = None) -> Callable:
        """
        Decorator to trace a class method.
        
        Args:
            operation_name: Optional name for the operation.
                           If not provided, the method name will be used.
            
        Returns:
            A decorator function.
        """
        # This is essentially the same as trace_function,
        # but can be more specific for methods if needed
        return self.trace_function(operation_name)
    
    def trace_context(self, operation_name: str, attributes: Optional[Dict[str, Any]] = None) -> 'TracingContext':
        """
        Create a context manager for tracing a block of code.
        
        Args:
            operation_name: The name of the operation being traced.
            attributes: Optional attributes for the span.
            
        Returns:
            A TracingContext instance.
        """
        return TracingContext(self, operation_name, attributes)
    
    def inject_trace_context(self, carrier: Dict[str, str]) -> Dict[str, str]:
        """
        Inject current trace context into a carrier.
        
        Args:
            carrier: Dictionary to inject trace context into
            
        Returns:
            Updated carrier with trace context
        """
        return self.propagator.inject_context(carrier)
    
    def extract_trace_context(self, carrier: Dict[str, str]) -> Optional[Any]:
        """
        Extract trace context from a carrier.
        
        Args:
            carrier: Dictionary containing trace context
            
        Returns:
            Extracted context or None if not present/available
        """
        return self.propagator.extract_context(carrier)
    
    def create_trace_context_headers(self) -> Dict[str, str]:
        """
        Create HTTP headers with trace context for the current span.
        
        Returns:
            Dictionary of HTTP headers with trace context
        """
        return self.inject_trace_context({})
    
    def clear_traces(self) -> None:
        """Clear all stored traces."""
        # Only applicable for fallback implementation
        if hasattr(self, '_traces'):
            self._traces.clear()
            logger.debug("Cleared all traces")
    
    @contextmanager
    def start_active_span(self, operation_name: str, attributes: Optional[Dict[str, Any]] = None) -> Iterator[Union[str, Span]]:
        """
        Context manager to create and activate a span for the current execution context.
        
        Args:
            operation_name: The name of the operation being traced.
            attributes: Optional attributes to add to the span.
            
        Yields:
            The created span
        """
        if not self.enabled:
            # Return a no-op context manager
            yield None
            return
        
        # Handle OpenTelemetry implementation
        if OPENTELEMETRY_AVAILABLE and self._tracer:
            with self._tracer.start_as_current_span(operation_name, attributes=attributes) as span:
                try:
                    yield span
                except Exception as e:
                    # Record exception
                    span.record_exception(e)
                    span.set_status(StatusCode.ERROR, str(e))
                    raise
        else:
            # Fallback implementation
            trace_id = self.start_trace(operation_name)
            span_id = next(iter(self.get_trace(trace_id).keys()), None)
            
            # Add attributes if provided
            if attributes and span_id:
                for key, value in attributes.items():
                    self.add_span_tag(span_id, key, value)
            
            try:
                yield span_id
            except Exception as e:
                if span_id:
                    # Add exception info as a span event
                    self.add_span_event(
                        span_id,
                        "exception",
                        {
                            "exception_type": type(e).__name__,
                            "exception_message": str(e)
                        }
                    )
                    
                    # End the span with error status
                    self.end_span(span_id, "error", e)
                
                raise
            else:
                if span_id:
                    # End the span with success status
                    self.end_span(span_id, "success")


class TracingContext:
    """
    A context manager for tracing a block of code.
    
    This class is used with the 'with' statement to trace a block of code.
    """
    
    def __init__(
        self, 
        tracing_manager: TracingManager, 
        operation_name: str,
        attributes: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize a new tracing context.
        
        Args:
            tracing_manager: The TracingManager to use for tracing.
            operation_name: The name of the operation being traced.
            attributes: Optional attributes for the span.
        """
        self.tracing_manager = tracing_manager
        self.operation_name = operation_name
        self.attributes = attributes or {}
        self.trace_id = None
        self.span = None
    
    def __enter__(self) -> 'TracingContext':
        """
        Enter the tracing context, starting a new trace and span.
        
        Returns:
            The TracingContext instance.
        """
        if not self.tracing_manager.enabled:
            return self
        
        # Use OpenTelemetry if available
        if OPENTELEMETRY_AVAILABLE and hasattr(self.tracing_manager, '_tracer') and self.tracing_manager._tracer:
            self.span = self.tracing_manager._tracer.start_span(
                self.operation_name, 
                attributes=self.attributes
            )
            # Set as current span
            context = trace.set_span_in_context(self.span)
            token = context_api.attach(context)
            self._token = token
        else:
            # Fallback implementation
            self.trace_id = self.tracing_manager.start_trace(self.operation_name)
            self.span = next(iter(self.tracing_manager.get_trace(self.trace_id).keys()), None)
            
            # Add attributes
            if self.span and self.attributes:
                for key, value in self.attributes.items():
                    self.tracing_manager.add_span_tag(self.span, key, value)
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Exit the tracing context, ending the span.
        
        Args:
            exc_type: The exception type if an exception was raised.
            exc_val: The exception value if an exception was raised.
            exc_tb: The traceback if an exception was raised.
        """
        if not self.tracing_manager.enabled:
            return
        
        # Handle OpenTelemetry implementation
        if OPENTELEMETRY_AVAILABLE and isinstance(self.span, Span):
            if exc_type is not None:
                # Record exception
                self.span.record_exception(exc_val)
                self.span.set_status(StatusCode.ERROR, str(exc_val) if exc_val else "")
            else:
                # Set success status
                self.span.set_status(StatusCode.OK)
            
            # End the span
            self.span.end()
            
            # Detach context
            if hasattr(self, '_token'):
                context_api.detach(self._token)
            
            return
        
        # Handle fallback implementation
        if not self.trace_id or not self.span:
            return
        
        if exc_type is not None:
            # Add exception info as a span event
            self.tracing_manager.add_span_event(
                self.span,
                "exception",
                {
                    "exception_type": exc_type.__name__,
                    "exception_message": str(exc_val) if exc_val else ""
                }
            )
            
            # End the span with error status
            self.tracing_manager.end_span(self.span, "error")
        else:
            # End the span with success status
            self.tracing_manager.end_span(self.span, "success")
    
    def add_event(self, event_name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
        """
        Add an event to the current span.
        
        Args:
            event_name: The name of the event.
            attributes: Optional attributes describing the event.
        """
        if not self.tracing_manager.enabled or not self.span:
            return
        
        self.tracing_manager.add_span_event(
            self.span,
            event_name,
            attributes
        )
    
    def add_tag(self, key: str, value: Any) -> None:
        """
        Add a tag to the current span.
        
        Args:
            key: The key of the tag.
            value: The value of the tag.
        """
        if not self.tracing_manager.enabled or not self.span:
            return
        
        self.tracing_manager.add_span_tag(
            self.span,
            key,
            value
        )
    
    def new_child_span(self, operation_name: str) -> 'ChildSpanContext':
        """
        Create a new child span context.
        
        Args:
            operation_name: The name of the operation for the child span.
            
        Returns:
            A ChildSpanContext instance.
        """
        return ChildSpanContext(
            self.tracing_manager,
            operation_name,
            self.trace_id,
            self.span
        )


class ChildSpanContext:
    """
    A context manager for creating a child span within an existing trace.
    
    This class is used with the 'with' statement to trace a block of code
    as a child of an existing span.
    """
    
    def __init__(
        self,
        tracing_manager: TracingManager,
        operation_name: str,
        trace_id: Optional[str],
        parent_span: Union[str, Span, None]
    ):
        """
        Initialize a new child span context.
        
        Args:
            tracing_manager: The TracingManager to use for tracing.
            operation_name: The name of the operation being traced.
            trace_id: The ID of the parent trace.
            parent_span: The parent span or span ID.
        """
        self.tracing_manager = tracing_manager
        self.operation_name = operation_name
        self.trace_id = trace_id
        self.parent_span = parent_span
        self.span = None
        self._token = None
    
    def __enter__(self) -> 'ChildSpanContext':
        """
        Enter the child span context, starting a new span.
        
        Returns:
            The ChildSpanContext instance.
        """
        if not self.tracing_manager.enabled:
            return self
        
        # Handle OpenTelemetry implementation
        if OPENTELEMETRY_AVAILABLE and hasattr(self.tracing_manager, '_tracer') and self.tracing_manager._tracer:
            # Get current context with parent span
            if isinstance(self.parent_span, Span):
                context = trace.set_span_in_context(self.parent_span)
            else:
                context = None
            
            # Start a new span as child of current context
            if context:
                self.span = self.tracing_manager._tracer.start_span(
                    self.operation_name,
                    context=context
                )
            else:
                self.span = self.tracing_manager._tracer.start_span(self.operation_name)
            
            # Set as current span
            new_context = trace.set_span_in_context(self.span)
            self._token = context_api.attach(new_context)
        else:
            # Fallback implementation
            if not self.trace_id or not self.parent_span:
                return self
            
            self.span = self.tracing_manager.start_span(
                self.operation_name,
                self.trace_id,
                self.parent_span
            )
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Exit the child span context, ending the span.
        
        Args:
            exc_type: The exception type if an exception was raised.
            exc_val: The exception value if an exception was raised.
            exc_tb: The traceback if an exception was raised.
        """
        if not self.tracing_manager.enabled or not self.span:
            return
        
        # Handle OpenTelemetry implementation
        if OPENTELEMETRY_AVAILABLE and isinstance(self.span, Span):
            if exc_type is not None:
                # Record exception
                self.span.record_exception(exc_val)
                self.span.set_status(StatusCode.ERROR, str(exc_val) if exc_val else "")
            else:
                # Set success status
                self.span.set_status(StatusCode.OK)
            
            # End the span
            self.span.end()
            
            # Detach context
            if self._token:
                context_api.detach(self._token)
            
            return
        
        # Handle fallback implementation
        if exc_type is not None:
            # Add exception info as a span event
            self.tracing_manager.add_span_event(
                self.span,
                "exception",
                {
                    "exception_type": exc_type.__name__,
                    "exception_message": str(exc_val) if exc_val else ""
                }
            )
            
            # End the span with error status
            self.tracing_manager.end_span(self.span, "error")
        else:
            # End the span with success status
            self.tracing_manager.end_span(self.span, "success")
    
    def add_event(self, event_name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
        """
        Add an event to the current span.
        
        Args:
            event_name: The name of the event.
            attributes: Optional attributes describing the event.
        """
        if not self.tracing_manager.enabled or not self.span:
            return
        
        self.tracing_manager.add_span_event(
            self.span,
            event_name,
            attributes
        )
    
    def add_tag(self, key: str, value: Any) -> None:
        """
        Add a tag to the current span.
        
        Args:
            key: The key of the tag.
            value: The value of the tag.
        """
        if not self.tracing_manager.enabled or not self.span:
            return
        
        self.tracing_manager.add_span_tag(
            self.span,
            key,
            value
        )


# Import OpenTelemetry context API if available
if OPENTELEMETRY_AVAILABLE:
    from opentelemetry import context as context_api
else:
    # Stub for context_api
    class ContextAPI:
        def attach(self, context):
            return None
        
        def detach(self, token):
            pass
    
    context_api = ContextAPI() func.__name__
                
                # Start a new trace or use an existing one
                trace_id = kwargs.pop("trace_id", None) or self.start_trace(span_name)
                
                # Start a new span
                parent_span_id = kwargs.pop("parent_span_id", None)
                span_id = self.start_span(span_name, trace_id, parent_span_id)
                
                try:
                    # Add function arguments as span tags
                    # Exclude self or cls for methods
                    if args and hasattr(args[0], func.__name__):
                        # This is likely a method call, skip the first argument (self/cls)
                        func_args = args[1:]
                    else:
                        func_args = args
                    
                    # Add basic arg/kwarg info as tags
                    # Be careful not to include sensitive information
                    self.add_span_tag(trace_id, span_id, "args_count", len(func_args))
                    self.add_span_tag(trace_id, span_id, "kwargs_keys", list(kwargs.keys()))
                    
                    # Execute the function
                    result = func(*args, **kwargs)
                    
                    # Add result info as a span tag
                    # Be careful not to include sensitive information
                    if result is not None:
                        result_type = type(result).__name__
                        self.add_span_tag(trace_id, span_id, "result_type", result_type)
                    
                    # End the span with success status
                    self.end_span(trace_id, span_id, "success")
                    
                    return result
                
                except Exception as e:
                    # Add exception info as a span event
                    self.add_span_event(
                        trace_id,
                        span_id,
                        "exception",
                        {
                            "exception_type": type(e).__name__,
                            "exception_message": str(e)
                        }
                    )
                    
                    # End the span with error status
                    self.end_span(trace_id, span_id, "error")
                    
                    # Re-raise the exception
                    raise
            
            return wrapper
        
        return decorator
    
    def trace_method(self, operation_name: Optional[str] = None) -> Callable:
        """
        Decorator to trace a class method.
        
        Args:
            operation_name: Optional name for the operation.
                           If not provided, the method name will be used.
            
        Returns:
            A decorator function.
        """
        # This is essentially the same as trace_function,
        # but can be more specific for methods if needed
        return self.trace_function(operation_name)
    
    def trace_context(self, operation_name: str) -> 'TracingContext':
        """
        Create a context manager for tracing a block of code.
        
        Args:
            operation_name: The name of the operation being traced.
            
        Returns:
            A TracingContext instance.
        """
        return TracingContext(self, operation_name)


class TracingContext:
    """
    A context manager for tracing a block of code.
    
    This class is used with the 'with' statement to trace a block of code.
    """
    
    def __init__(self, tracing_manager: TracingManager, operation_name: str):
        """
        Initialize a new tracing context.
        
        Args:
            tracing_manager: The TracingManager to use for tracing.
            operation_name: The name of the operation being traced.
        """
        self.tracing_manager = tracing_manager
        self.operation_name = operation_name
        self.trace_id = None
        self.span_id = None
    
    def __enter__(self) -> 'TracingContext':
        """
        Enter the tracing context, starting a new trace and span.
        
        Returns:
            The TracingContext instance.
        """
        if not self.tracing_manager.enabled:
            return self
        
        self.trace_id = self.tracing_manager.start_trace(self.operation_name)
        self.span_id = next(iter(self.tracing_manager.get_trace(self.trace_id).keys()), None)
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Exit the tracing context, ending the span.
        
        Args:
            exc_type: The exception type if an exception was raised.
            exc_val: The exception value if an exception was raised.
            exc_tb: The traceback if an exception was raised.
        """
        if not self.tracing_manager.enabled or not self.trace_id or not self.span_id:
            return
        
        if exc_type is not None:
            # Add exception info as a span event
            self.tracing_manager.add_span_event(
                self.trace_id,
                self.span_id,
                "exception",
                {
                    "exception_type": exc_type.__name__,
                    "exception_message": str(exc_val) if exc_val else ""
                }
            )
            
            # End the span with error status
            self.tracing_manager.end_span(self.trace_id, self.span_id, "error")
        else:
            # End the span with success status
            self.tracing_manager.end_span(self.trace_id, self.span_id, "success")
    
    def add_event(self, event_name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
        """
        Add an event to the current span.
        
        Args:
            event_name: The name of the event.
            attributes: Optional attributes describing the event.
        """
        if not self.tracing_manager.enabled or not self.trace_id or not self.span_id:
            return
        
        self.tracing_manager.add_span_event(
            self.trace_id,
            self.span_id,
            event_name,
            attributes
        )
    
    def add_tag(self, key: str, value: Any) -> None:
        """
        Add a tag to the current span.
        
        Args:
            key: The key of the tag.
            value: The value of the tag.
        """
        if not self.tracing_manager.enabled or not self.trace_id or not self.span_id:
            return
        
        self.tracing_manager.add_span_tag(
            self.trace_id,
            self.span_id,
            key,
            value
        )
    
    def new_child_span(self, operation_name: str) -> 'ChildSpanContext':
        """
        Create a new child span context.
        
        Args:
            operation_name: The name of the operation for the child span.
            
        Returns:
            A ChildSpanContext instance.
        """
        return ChildSpanContext(
            self.tracing_manager,
            operation_name,
            self.trace_id,
            self.span_id
        )


class ChildSpanContext:
    """
    A context manager for creating a child span within an existing trace.
    
    This class is used with the 'with' statement to trace a block of code
    as a child of an existing span.
    """
    
    def __init__(
        self,
        tracing_manager: TracingManager,
        operation_name: str,
        trace_id: str,
        parent_span_id: str
    ):
        """
        Initialize a new child span context.
        
        Args:
            tracing_manager: The TracingManager to use for tracing.
            operation_name: The name of the operation being traced.
            trace_id: The ID of the parent trace.
            parent_span_id: The ID of the parent span.
        """
        self.tracing_manager = tracing_manager
        self.operation_name = operation_name
        self.trace_id = trace_id
        self.parent_span_id = parent_span_id
        self.span_id = None
    
    def __enter__(self) -> 'ChildSpanContext':
        """
        Enter the child span context, starting a new span.
        
        Returns:
            The ChildSpanContext instance.
        """
        if not self.tracing_manager.enabled or not self.trace_id or not self.parent_span_id:
            return self
        
        self.span_id = self.tracing_manager.start_span(
            self.operation_name,
            self.trace_id,
            self.parent_span_id
        )
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Exit the child span context, ending the span.
        
        Args:
            exc_type: The exception type if an exception was raised.
            exc_val: The exception value if an exception was raised.
            exc_tb: The traceback if an exception was raised.
        """
        if not self.tracing_manager.enabled or not self.trace_id or not self.span_id:
            return
        
        if exc_type is not None:
            # Add exception info as a span event
            self.tracing_manager.add_span_event(
                self.trace_id,
                self.span_id,
                "exception",
                {
                    "exception_type": exc_type.__name__,
                    "exception_message": str(exc_val) if exc_val else ""
                }
            )
            
            # End the span with error status
            self.tracing_manager.end_span(self.trace_id, self.span_id, "error")
        else:
            # End the span with success status
            self.tracing_manager.end_span(self.trace_id, self.span_id, "success")
    
    def add_event(self, event_name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
        """
        Add an event to the current span.
        
        Args:
            event_name: The name of the event.
            attributes: Optional attributes describing the event.
        """
        if not self.tracing_manager.enabled or not self.trace_id or not self.span_id:
            return
        
        self.tracing_manager.add_span_event(
            self.trace_id,
            self.span_id,
            event_name,
            attributes
        )
    
    def add_tag(self, key: str, value: Any) -> None:
        """
        Add a tag to the current span.
        
        Args:
            key: The key of the tag.
            value: The value of the tag.
        """
        if not self.tracing_manager.enabled or not self.trace_id or not self.span_id:
            return
        
        self.tracing_manager.add_span_tag(
            self.trace_id,
            self.span_id,
            key,
            value
        )
