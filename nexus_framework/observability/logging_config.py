"""
Logging configuration for the Nexus framework.

This module provides enhanced utilities for configuring and managing logging
throughout the Nexus framework, with support for structured logging,
log correlation with trace IDs, and various output formats.
"""

import logging
import sys
import os
from typing import Dict, Optional, Union, List, TextIO, Any, Set, Callable, Iterator
import json
from datetime import datetime
import inspect
import threading
import traceback
import uuid
import io
import socket
import platform
import copy
from functools import wraps
from contextlib import contextmanager

# Import tracing support if available
try:
    from nexus_framework.observability.tracing import TracingManager
    TRACING_AVAILABLE = True
except ImportError:
    TRACING_AVAILABLE = False
    
try:
    # For integration with external log aggregation systems
    import structlog
    STRUCTLOG_AVAILABLE = True
except ImportError:
    STRUCTLOG_AVAILABLE = False
    
# Constants
DEFAULT_LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
DEFAULT_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
DEFAULT_JSON_FORMAT = {
    "timestamp": "%(asctime)s",
    "level": "%(levelname)s",
    "logger": "%(name)s",
    "message": "%(message)s",
    "module": "%(module)s",
    "function": "%(funcName)s",
    "line": "%(lineno)d"
}

# Environment variable constants
ENV_LOG_LEVEL = "NEXUS_LOG_LEVEL"
ENV_LOG_FORMAT = "NEXUS_LOG_FORMAT"
ENV_LOG_JSON = "NEXUS_LOG_JSON"
ENV_LOG_FILE = "NEXUS_LOG_FILE"

# Global tracing manager instance
_tracing_manager = None

# Thread local storage for context values
_thread_local = threading.local()


def _get_thread_local_dict() -> Dict[str, Any]:
    """Get thread local context dictionary, creating it if it doesn't exist."""
    if not hasattr(_thread_local, 'context'):
        _thread_local.context = {}
    return _thread_local.context


def _get_trace_id() -> Optional[str]:
    """Get trace ID from current trace context if available."""
    global _tracing_manager
    
    if not TRACING_AVAILABLE or not _tracing_manager:
        return None
    
    # Try to get current span
    current_span = _tracing_manager.get_current_span()
    if not current_span:
        return None
    
    # For OpenTelemetry spans
    if hasattr(current_span, 'get_span_context'):
        context = current_span.get_span_context()
        if hasattr(context, 'trace_id'):
            # Format trace ID as hex
            return format(context.trace_id, '032x')
    
    # For fallback tracing implementation, span might be a string (span_id)
    if isinstance(current_span, str):
        # Find trace_id for this span_id by searching traces
        for trace_id, spans in _tracing_manager._traces.items():
            if current_span in spans:
                return trace_id
    
    return None


def _get_correlation_id() -> str:
    """Get or create a correlation ID for the current thread."""
    context = _get_thread_local_dict()
    if 'correlation_id' not in context:
        # Try to get trace ID
        trace_id = _get_trace_id()
        if trace_id:
            context['correlation_id'] = trace_id
        else:
            # Generate a new unique ID
            context['correlation_id'] = str(uuid.uuid4())
    
    return context['correlation_id']


class JsonFormatter(logging.Formatter):
    """
    Custom log formatter that outputs log records as JSON.
    
    This is useful for structured logging and for integration with
    log management systems that can parse JSON.
    """
    
    def __init__(self, fmt: Optional[Dict[str, str]] = None):
        """
        Initialize a JSON formatter.
        
        Args:
            fmt: Optional dictionary mapping field names to log record format strings.
                 If not provided, DEFAULT_JSON_FORMAT will be used.
        """
        super().__init__()
        self.fmt = fmt or DEFAULT_JSON_FORMAT
        self.hostname = socket.gethostname()
        
    def format(self, record: logging.LogRecord) -> str:
        """
        Format a log record as JSON.
        
        Args:
            record: The log record to format.
            
        Returns:
            A JSON string representing the log record.
        """
        # Process format strings
        output = {}
        for key, format_str in self.fmt.items():
            try:
                value = format_str % record.__dict__
                output[key] = value
            except (KeyError, TypeError, ValueError):
                output[key] = format_str

        # Base log record data (not in format strings)
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "filename": record.filename,
            "lineno": record.lineno,
            "funcName": record.funcName,
            "process": record.process,
            "thread": record.thread,
            "threadName": record.threadName,
            "hostname": self.hostname,
            "app": "nexus-framework",
        }
        
        # Update with formatted values
        log_data.update(output)
        
        # Add trace/correlation ID if available
        correlation_id = _get_correlation_id()
        if correlation_id:
            log_data["correlation_id"] = correlation_id
        
        # Add trace ID specifically if available
        trace_id = _get_trace_id()
        if trace_id:
            log_data["trace_id"] = trace_id
        
        # Add context fields
        context = _get_thread_local_dict()
        for key, value in context.items():
            if key not in log_data and key != 'correlation_id':
                log_data[f"ctx_{key}"] = value
        
        # Add exception info if present
        if record.exc_info:
            log_data['exc_info'] = self.formatException(record.exc_info)
            if record.exc_text:
                log_data['exc_text'] = record.exc_text
        
        # Process any extra attributes from the record
        for key, value in record.__dict__.items():
            if key not in log_data and not key.startswith('_'):
                try:
                    # Try to serialize the value to JSON
                    json.dumps({key: value})
                    log_data[key] = value
                except (TypeError, OverflowError):
                    # If the value can't be serialized, convert it to a string
                    log_data[key] = str(value)
        
        # Return the log record as a JSON string
        return json.dumps(log_data)


class StructuredLogRecord(logging.LogRecord):
    """
    Extended LogRecord class that supports additional structured data.
    
    This allows log records to include structured data that can be
    properly serialized to JSON or other formats.
    """
    
    def __init__(self, *args, **kwargs):
        """Initialize a structured log record."""
        super().__init__(*args, **kwargs)
        self.structured_data = {}
    
    def set_structured_data(self, data: Dict[str, Any]) -> None:
        """
        Set structured data for this log record.
        
        Args:
            data: Dictionary of structured data.
        """
        self.structured_data = data


class StructuredLogger(logging.Logger):
    """
    Logger class that supports structured logging.
    
    This extends the standard Python logger with methods for
    structured logging and context propagation.
    """
    
    def makeRecord(self, name, level, fn, lno, msg, args, exc_info, func=None, extra=None, sinfo=None):
        """
        Create a LogRecord with additional structured data.
        
        This overrides the standard makeRecord method to create
        a StructuredLogRecord instead of a standard LogRecord.
        """
        # Create a structured log record instead of a standard log record
        if extra is None:
            extra = {}
        
        # Add correlation/trace ID if available
        correlation_id = _get_correlation_id()
        if correlation_id:
            extra['correlation_id'] = correlation_id
        
        trace_id = _get_trace_id()
        if trace_id:
            extra['trace_id'] = trace_id
        
        # Add thread-local context if available
        context = _get_thread_local_dict()
        for key, value in context.items():
            if key not in extra and key != 'correlation_id':
                extra[f"ctx_{key}"] = value
        
        # Create the record
        record = super().makeRecord(name, level, fn, lno, msg, args, exc_info, func, extra, sinfo)
        
        # Add structured data
        record.structured_data = {}
        
        return record
    
    def structure(self, level: int, msg: str, structured_data: Dict[str, Any], *args, **kwargs) -> None:
        """
        Log a message with structured data.
        
        Args:
            level: Log level (e.g. logging.INFO)
            msg: Log message
            structured_data: Dictionary of structured data
            *args, **kwargs: Additional arguments to pass to the logger
        """
        if not self.isEnabledFor(level):
            return
        
        # Create log record
        try:
            # Get caller information
            frame = inspect.currentframe().f_back
            filename = frame.f_code.co_filename
            lineno = frame.f_lineno
            func_name = frame.f_code.co_name
        except (AttributeError, ValueError):
            filename = "(unknown file)"
            lineno = 0
            func_name = "(unknown function)"
        
        # Create record with extra fields for structured data
        if self.findCaller.__code__ is not logging.Logger.findCaller.__code__:
            ci = self.findCaller()  # Python 3.8+
            fn, lno, func, sinfo = ci
        else:
            fn, lno, func = filename, lineno, func_name
            sinfo = None
        
        # Add structured data to record
        if kwargs.get('extra') is None:
            kwargs['extra'] = {}
        
        for key, value in structured_data.items():
            kwargs['extra'][key] = value
        
        # Create record with structured data
        record = self.makeRecord(
            self.name, level, fn, lno, msg, args,
            kwargs.get('exc_info'), func, None, sinfo
        )
        
        # Add structured data to record
        record.structured_data = structured_data
        
        # Log the record
        self.handle(record)
    
    def info_structure(self, msg: str, structured_data: Dict[str, Any], *args, **kwargs) -> None:
        """
        Log an INFO message with structured data.
        
        Args:
            msg: Log message
            structured_data: Dictionary of structured data
            *args, **kwargs: Additional arguments to pass to the logger
        """
        self.structure(logging.INFO, msg, structured_data, *args, **kwargs)
    
    def debug_structure(self, msg: str, structured_data: Dict[str, Any], *args, **kwargs) -> None:
        """
        Log a DEBUG message with structured data.
        
        Args:
            msg: Log message
            structured_data: Dictionary of structured data
            *args, **kwargs: Additional arguments to pass to the logger
        """
        self.structure(logging.DEBUG, msg, structured_data, *args, **kwargs)
    
    def warning_structure(self, msg: str, structured_data: Dict[str, Any], *args, **kwargs) -> None:
        """
        Log a WARNING message with structured data.
        
        Args:
            msg: Log message
            structured_data: Dictionary of structured data
            *args, **kwargs: Additional arguments to pass to the logger
        """
        self.structure(logging.WARNING, msg, structured_data, *args, **kwargs)
    
    def error_structure(self, msg: str, structured_data: Dict[str, Any], *args, **kwargs) -> None:
        """
        Log an ERROR message with structured data.
        
        Args:
            msg: Log message
            structured_data: Dictionary of structured data
            *args, **kwargs: Additional arguments to pass to the logger
        """
        self.structure(logging.ERROR, msg, structured_data, *args, **kwargs)
    
    def critical_structure(self, msg: str, structured_data: Dict[str, Any], *args, **kwargs) -> None:
        """
        Log a CRITICAL message with structured data.
        
        Args:
            msg: Log message
            structured_data: Dictionary of structured data
            *args, **kwargs: Additional arguments to pass to the logger
        """
        self.structure(logging.CRITICAL, msg, structured_data, *args, **kwargs)


class LoggingContext:
    """
    A context manager for temporarily modifying a logger's configuration.
    
    This is useful for capturing the logs from a specific operation
    or for changing the log level for a section of code.
    """
    
    def __init__(
        self,
        logger: Union[logging.Logger, str],
        level: Optional[int] = None,
        handler: Optional[logging.Handler] = None,
        close: bool = True
    ):
        """
        Initialize a logging context.
        
        Args:
            logger: The logger to modify or the name of a logger.
            level: Optional log level to set during the context.
            handler: Optional additional handler to add during the context.
            close: Whether to close the handler when exiting the context.
        """
        if isinstance(logger, str):
            self.logger = logging.getLogger(logger)
        else:
            self.logger = logger
        
        self.level = level
        self.handler = handler
        self.close = close
        
        # Store original settings
        self.old_level = self.logger.level
        self.old_handlers = self.logger.handlers.copy()
    
    def __enter__(self) -> logging.Logger:
        """
        Enter the logging context, modifying the logger as specified.
        
        Returns:
            The modified logger.
        """
        if self.level is not None:
            self.logger.setLevel(self.level)
        
        if self.handler is not None:
            self.logger.addHandler(self.handler)
        
        return self.logger
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Exit the logging context, restoring the logger to its original state.
        
        Args:
            exc_type: The exception type if an exception was raised.
            exc_val: The exception value if an exception was raised.
            exc_tb: The traceback if an exception was raised.
        """
        if self.level is not None:
            self.logger.setLevel(self.old_level)
        
        if self.handler is not None:
            self.logger.removeHandler(self.handler)
            if self.close:
                self.handler.close()
        
        # Restore original handlers
        self.logger.handlers = self.old_handlers


@contextmanager
def capture_logs(
    logger_name: str = 'nexus_framework',
    level: int = logging.DEBUG
) -> Iterator[List[str]]:
    """
    Capture logs from a logger as a list of strings.
    
    This is useful for testing or for capturing logs that need to be
    processed or displayed in a specific way.
    
    Args:
        logger_name: The name of the logger to capture logs from.
        level: The logging level to capture.
        
    Yields:
        A list of captured log messages.
    """
    log_messages = []
    
    class ListHandler(logging.Handler):
        def emit(self, record):
            log_messages.append(self.format(record))
    
    handler = ListHandler()
    handler.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))
    
    with LoggingContext(logger_name, level=level, handler=handler):
        yield log_messages


def configure_logging(
    log_level: int = logging.INFO,
    log_file: Optional[str] = None,
    console: bool = True,
    log_format: str = DEFAULT_LOG_FORMAT,
    date_format: str = DEFAULT_DATE_FORMAT,
    json_logs: bool = False,
    tracing_manager: Optional[Any] = None,
    log_context: Optional[Dict[str, Any]] = None,
    log_aggregation_url: Optional[str] = None
) -> logging.Logger:
    """
    Configure logging for the Nexus framework.
    
    Args:
        log_level: The logging level to use.
        log_file: Optional path to a log file for file-based logging.
        console: Whether to log to the console.
        log_format: The log message format.
        date_format: The date format for log messages.
        json_logs: Whether to format logs as JSON.
        tracing_manager: Optional tracing manager for log correlation.
        log_context: Optional global context values to include in all logs.
        log_aggregation_url: Optional URL for log aggregation system.
        
    Returns:
        The configured root logger.
    """
    # Check environment variables for overrides
    env_level = os.environ.get(ENV_LOG_LEVEL)
    if env_level:
        try:
            log_level = getattr(logging, env_level.upper())
        except (AttributeError, TypeError):
            # Invalid level, ignore
            pass
    
    env_format = os.environ.get(ENV_LOG_FORMAT)
    if env_format:
        log_format = env_format
    
    env_json = os.environ.get(ENV_LOG_JSON)
    if env_json and env_json.lower() in ('1', 'true', 'yes', 'on'):
        json_logs = True
    
    env_file = os.environ.get(ENV_LOG_FILE)
    if env_file:
        log_file = env_file
    
    # Reset root logger
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Set the root logger level
    root_logger.setLevel(log_level)
    
    # Register our custom logger class
    logging.setLoggerClass(StructuredLogger)
    
    # Store tracing manager for log correlation
    global _tracing_manager
    _tracing_manager = tracing_manager
    
    # Add global context values
    if log_context:
        context = _get_thread_local_dict()
        context.update(log_context)
    
    # Create formatters
    if json_logs:
        formatter = JsonFormatter()
    else:
        formatter = logging.Formatter(log_format, datefmt=date_format)
    
    # Set up console logging if requested
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    # Set up file logging if a log file is specified
    if log_file:
        # Create the directory if it doesn't exist
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Set up structlog integration if available
    if STRUCTLOG_AVAILABLE and log_aggregation_url:
        try:
            # This is a placeholder - actual implementation would depend on specific log aggregation system
            # For example, setting up structlog with a processor for the chosen system
            pass
        except Exception as e:
            root_logger.warning(f"Failed to configure log aggregation: {str(e)}")
    
    # Configure Nexus framework loggers
    framework_logger = logging.getLogger('nexus_framework')
    framework_logger.setLevel(log_level)
    
    # Log startup message
    framework_logger.info(f"Nexus framework logging configured. Level: {logging.getLevelName(log_level)}")
    
    return root_logger


def with_context(**context_vars):
    """
    Decorator that adds context variables to logs within a function.
    
    Args:
        **context_vars: Context variables to add to logs.
        
    Returns:
        Decorator function.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            old_context = _get_thread_local_dict().copy()
            context = _get_thread_local_dict()
            
            # Add context variables
            context.update(context_vars)
            
            try:
                return func(*args, **kwargs)
            finally:
                # Restore original context
                _thread_local.context = old_context
        
        return wrapper
    
    return decorator


@contextmanager
def log_context(**context_vars):
    """
    Context manager that adds context variables to logs within a block.
    
    Args:
        **context_vars: Context variables to add to logs.
        
    Yields:
        Nothing, just provides context.
    """
    old_context = _get_thread_local_dict().copy()
    context = _get_thread_local_dict()
    
    # Add context variables
    context.update(context_vars)
    
    try:
        yield
    finally:
        # Restore original context
        _thread_local.context = old_context


def set_correlation_id(correlation_id: str) -> None:
    """
    Set the correlation ID for the current thread.
    
    Args:
        correlation_id: The correlation ID to set.
    """
    context = _get_thread_local_dict()
    context['correlation_id'] = correlation_id


def get_logger(name: str) -> StructuredLogger:
    """
    Get a structured logger with the given name.
    
    Args:
        name: The name of the logger.
        
    Returns:
        A StructuredLogger instance.
    """
    return logging.getLogger(name)


def log_event(
    logger: Union[logging.Logger, str],
    event_name: str,
    level: int = logging.INFO,
    **event_data
) -> None:
    """
    Log a structured event.
    
    Args:
        logger: The logger to use or logger name.
        event_name: The name of the event.
        level: The log level to use.
        **event_data: Additional event data.
    """
    if isinstance(logger, str):
        logger = logging.getLogger(logger)
    
    # Ensure we have a structured logger
    if not isinstance(logger, StructuredLogger):
        # Use standard logging as fallback
        event_str = f"{event_name}: " + ", ".join(f"{k}={v}" for k, v in event_data.items())
        logger.log(level, event_str)
        return
    
    # Create event data
    data = {
        "event": event_name,
        **event_data
    }
    
    # Log structured event
    logger.structure(level, f"Event: {event_name}", data)


def init_logging_from_config(config: Dict[str, Any]) -> logging.Logger:
    """
    Initialize logging from a configuration dictionary.
    
    Args:
        config: Configuration dictionary with logging settings.
        
    Returns:
        The configured root logger.
    """
    log_level = config.get('log_level', 'INFO')
    if isinstance(log_level, str):
        log_level = getattr(logging, log_level.upper(), logging.INFO)
    
    log_file = config.get('log_file')
    console = config.get('console_logging', True)
    log_format = config.get('log_format', DEFAULT_LOG_FORMAT)
    date_format = config.get('date_format', DEFAULT_DATE_FORMAT)
    json_logs = config.get('json_logs', False)
    log_context = config.get('log_context', {})
    log_aggregation_url = config.get('log_aggregation_url')
    
    return configure_logging(
        log_level=log_level,
        log_file=log_file,
        console=console,
        log_format=log_format,
        date_format=date_format,
        json_logs=json_logs,
        log_context=log_context,
        log_aggregation_url=log_aggregation_url
    )
