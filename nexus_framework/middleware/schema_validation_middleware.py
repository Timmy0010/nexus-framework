# nexus_framework/middleware/schema_validation_middleware.py
from typing import Dict, Any, Optional, Callable
import logging
from functools import wraps

from nexus_framework.validation.schema_validator import SchemaValidator, SchemaValidationError
from nexus_framework.validation.schema_registry import SchemaRegistry
from nexus_framework.core.message import Message

logger = logging.getLogger(__name__)

class SchemaValidationMiddleware:
    """Middleware for validating message schemas in the Nexus Framework."""
    
    def __init__(self, schema_registry: SchemaRegistry, strict_mode: bool = True):
        """
        Initialize the schema validation middleware.
        
        Args:
            schema_registry: Registry containing schemas for validation
            strict_mode: If True, invalid messages will be rejected.
                        If False, validation failures will be logged but messages will still be processed.
        """
        self.schema_registry = schema_registry
        self.strict_mode = strict_mode
        
        # Create validator with all registered schemas
        self.validator = SchemaValidator(
            schema_registry.get_base_schema("1.0"),
            schema_registry.get_all_payload_schemas()
        )
    
    def process_outgoing_message(self, message: Message) -> Message:
        """
        Validate an outgoing message before sending.
        
        Args:
            message: The message to validate
            
        Returns:
            The original message if valid or if in non-strict mode
            
        Raises:
            SchemaValidationError: If validation fails and strict_mode is True
        """
        try:
            # Convert message to dict for validation
            message_dict = message.to_dict()
            
            # Validate against schema
            valid, errors = self.validator.validate_message(message_dict)
            
            if not valid:
                error_message = f"Outgoing message {message.message_id} failed schema validation: {', '.join(errors)}"
                if self.strict_mode:
                    logger.error(error_message)
                    raise SchemaValidationError(error_message, errors)
                else:
                    logger.warning(error_message)
            
            return message
        except Exception as e:
            if not isinstance(e, SchemaValidationError) and self.strict_mode:
                logger.error(f"Error during schema validation of outgoing message: {str(e)}")
                raise
            if not self.strict_mode:
                logger.warning(f"Error during schema validation of outgoing message (ignored in non-strict mode): {str(e)}")
            return message
    
    def process_incoming_message(self, message: Message) -> Message:
        """
        Validate an incoming message before processing.
        
        Args:
            message: The message to validate
            
        Returns:
            The original message if valid or if in non-strict mode
            
        Raises:
            SchemaValidationError: If validation fails and strict_mode is True
        """
        try:
            # Convert message to dict for validation
            message_dict = message.to_dict()
            
            # Validate against schema
            valid, errors = self.validator.validate_message(message_dict)
            
            if not valid:
                error_message = f"Incoming message {message.message_id} failed schema validation: {', '.join(errors)}"
                if self.strict_mode:
                    logger.error(error_message)
                    raise SchemaValidationError(error_message, errors)
                else:
                    logger.warning(error_message)
            
            return message
        except Exception as e:
            if not isinstance(e, SchemaValidationError) and self.strict_mode:
                logger.error(f"Error during schema validation of incoming message: {str(e)}")
                raise
            if not self.strict_mode:
                logger.warning(f"Error during schema validation of incoming message (ignored in non-strict mode): {str(e)}")
            return message

def validate_outgoing(registry: SchemaRegistry, strict: bool = True):
    """
    Decorator for validating outgoing messages.
    
    Args:
        registry: Schema registry to use for validation
        strict: Whether to enforce strict validation
        
    Returns:
        Decorator function that validates messages
    """
    middleware = SchemaValidationMiddleware(registry, strict)
    
    def decorator(func):
        @wraps(func)
        def wrapper(message, *args, **kwargs):
            # Validate message before passing to handler
            validated_message = middleware.process_outgoing_message(message)
            return func(validated_message, *args, **kwargs)
        return wrapper
    return decorator

def validate_incoming(registry: SchemaRegistry, strict: bool = True):
    """
    Decorator for validating incoming messages.
    
    Args:
        registry: Schema registry to use for validation
        strict: Whether to enforce strict validation
        
    Returns:
        Decorator function that validates messages
    """
    middleware = SchemaValidationMiddleware(registry, strict)
    
    def decorator(func):
        @wraps(func)
        def wrapper(message, *args, **kwargs):
            # Validate message before passing to handler
            validated_message = middleware.process_incoming_message(message)
            return func(validated_message, *args, **kwargs)
        return wrapper
    return decorator
