"""
Logging configuration for the Nexus framework.

This module provides utilities for configuring and managing logging
throughout the Nexus framework.
"""

import logging
import sys
import os
from typing import Dict, Optional, Union, List, TextIO
import json
from datetime import datetime

# Default log format for handlers that use a formatter
DEFAULT_LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# Default date format for formatters
DEFAULT_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'


def configure_logging(
    log_level: int = logging.INFO,
    log_file: Optional[str] = None,
    console: bool = True,
    log_format: str = DEFAULT_LOG_FORMAT,
    date_format: str = DEFAULT_DATE_FORMAT,
    json_logs: bool = False
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
        
    Returns:
        The configured root logger.
    """
    # Reset root logger
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Set the root logger level
    root_logger.setLevel(log_level)
    
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
    
    # Configure Nexus framework loggers
    framework_logger = logging.getLogger('nexus_framework')
    framework_logger.setLevel(log_level)
    
    # Log startup message
    framework_logger.info(f"Nexus framework logging configured. Level: {logging.getLevelName(log_level)}")
    
    return root_logger


class JsonFormatter(logging.Formatter):
    """
    Custom log formatter that outputs log records as JSON.
    
    This is useful for structured logging and for integration with
    log management systems that can parse JSON.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format a log record as JSON.
        
        Args:
            record: The log record to format.
            
        Returns:
            A JSON string representing the log record.
        """
        # Base log record data
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'filename': record.filename,
            'lineno': record.lineno,
            'funcName': record.funcName,
            'process': record.process,
            'thread': record.thread,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data['exc_info'] = self.formatException(record.exc_info)
        
        # Add any extra attributes from the record
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


def capture_logs(
    logger_name: str = 'nexus_framework',
    level: int = logging.DEBUG
) -> List[str]:
    """
    Capture logs from a logger as a list of strings.
    
    This is useful for testing or for capturing logs that need to be
    processed or displayed in a specific way.
    
    Args:
        logger_name: The name of the logger to capture logs from.
        level: The logging level to capture.
        
    Returns:
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
