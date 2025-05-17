"""
Example demonstrating the Schema Validation functionality.

This script shows how to set up and use the Schema Validation system
to validate messages in the Nexus Framework.
"""

import logging
import os
import json
import uuid
from typing import Dict, Any

from nexus_framework.core.message import Message
from nexus_framework.validation.schema_registry import SchemaRegistry
from nexus_framework.validation.schema_validator import SchemaValidator, SchemaValidationError
from nexus_framework.middleware.schema_validation_middleware import (
    SchemaValidationMiddleware,
    validate_outgoing,
    validate_incoming
)
from nexus_framework.core.additional_schemas import *

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger("schema_validation_example")

def print_separator(title: str = None):
    """Print a separator line for better readability."""
    width = 80
    if title:
        padding = (width - len(title) - 4) // 2
        print("\n" + "=" * padding + f"[ {title} ]" + "=" * padding + "\n")
    else:
        print("\n" + "=" * width + "\n")

def create_messages():
    """Create a set of test messages, including valid and invalid ones."""
    messages = []
    
    # Valid text message
    messages.append({
        "name": "Valid Text Message",
        "message": Message(
            message_id=str(uuid.uuid4()),
            content="This is a valid text message",
            sender_id="test_sender",
            recipient_id="test_recipient",
            message_type="text_message",
            payload={
                "text": "Hello World!",
                "language": "en"
            }
        ),
        "expected_result": True  # Should pass validation
    })
    
    # Valid command message
    messages.append({
        "name": "Valid Command Message",
        "message": Message(
            message_id=str(uuid.uuid4()),
            content="This is a valid command message",
            sender_id="test_sender",
            recipient_id="test_recipient",
            message_type="command_message",
            payload={
                "command": "calculate",
                "parameters": {
                    "operation": "add",
                    "values": [1, 2, 3]
                }
            }
        ),
        "expected_result": True  # Should pass validation
    })
    
    # Invalid text message (missing required field)
    messages.append({
        "name": "Invalid Text Message",
        "message": Message(
            message_id=str(uuid.uuid4()),
            content="This message has an invalid schema",
            sender_id="test_sender",
            recipient_id="test_recipient",
            message_type="text_message",
            payload={
                # Missing required "text" field
                "language": "en"
            }
        ),
        "expected_result": False  # Should fail validation
    })
    
    # Invalid command message (missing required field)
    messages.append({
        "name": "Invalid Command Message",
        "message": Message(
            message_id=str(uuid.uuid4()),
            content="This command message has an invalid schema",
            sender_id="test_sender",
            recipient_id="test_recipient",
            message_type="command_message",
            payload={
                # Missing required "command" field
                "parameters": {
                    "operation": "add",
                    "values": [1, 2, 3]
                }
            }
        ),
        "expected_result": False  # Should fail validation
    })
    
    # Message with unknown type
    messages.append({
        "name": "Unknown Message Type",
        "message": Message(
            message_id=str(uuid.uuid4()),
            content="This message has an unknown type",
            sender_id="test_sender",
            recipient_id="test_recipient",
            message_type="unknown_type",
            payload={
                "some_field": "some_value"
            }
        ),
        "expected_result": False  # Should fail validation
    })
    
    # Valid event message
    messages.append({
        "name": "Valid Event Message",
        "message": Message(
            message_id=str(uuid.uuid4()),
            content="This is a valid event message",
            sender_id="test_sender",
            recipient_id="test_recipient",
            message_type="event_message",
            payload={
                "event_type": "user_login",
                "event_data": {
                    "user_id": "12345",
                    "ip_address": "192.168.1.1"
                },
                "event_time": "2025-05-16T10:30:00Z",
                "source": "auth_service"
            }
        ),
        "expected_result": True  # Should pass validation
    })
    
    # Valid error message
    messages.append({
        "name": "Valid Error Message",
        "message": Message(
            message_id=str(uuid.uuid4()),
            content="This is a valid error message",
            sender_id="test_sender",
            recipient_id="test_recipient",
            message_type="error_message",
            payload={
                "error_code": "AUTH_FAILED",
                "error_message": "Authentication failed",
                "severity": "error"
            }
        ),
        "expected_result": True  # Should pass validation
    })
    
    return messages

def create_schema_registry():
    """Create and configure a schema registry."""
    # Create schema registry
    registry = SchemaRegistry()
    
    # Register additional schemas from the additional_schemas module
    registry.register_payload_schema("command_message", "1.0", COMMAND_MESSAGE_PAYLOAD_SCHEMA_V1)
    registry.register_payload_schema("event_message", "1.0", EVENT_MESSAGE_PAYLOAD_SCHEMA_V1)
    registry.register_payload_schema("error_message", "1.0", ERROR_MESSAGE_PAYLOAD_SCHEMA_V1)
    registry.register_payload_schema("data_message", "1.0", DATA_MESSAGE_PAYLOAD_SCHEMA_V1)
    registry.register_payload_schema("status_message", "1.0", STATUS_MESSAGE_PAYLOAD_SCHEMA_V1)
    registry.register_payload_schema("verification_result", "1.0", VERIFICATION_RESULT_PAYLOAD_SCHEMA_V1)
    
    return registry

def main():
    """Run the schema validation example."""
    logger.info("Starting Schema Validation Example")
    
    # Create schema registry
    print_separator("Creating Schema Registry")
    registry = create_schema_registry()
    logger.info(f"Created schema registry with schemas for message types: {', '.join(registry.list_message_types())}")
    
    # Create schema validator
    print_separator("Creating Schema Validator")
    validator = SchemaValidator(
        registry.get_base_schema("1.0"),
        registry.get_all_payload_schemas()
    )
    logger.info(f"Created schema validator")
    
    # Create messages for testing
    print_separator("Creating Test Messages")
    test_messages = create_messages()
    logger.info(f"Created {len(test_messages)} test messages")
    
    # Test direct validation
    print_separator("Testing Direct Validation")
    for test_case in test_messages:
        logger.info(f"Validating message: {test_case['name']}")
        
        # Convert message to dict for validation
        message = test_case["message"]
        message_dict = message.to_dict()
        
        # Validate using schema validator
        try:
            is_valid, errors = validator.validate_message(message_dict)
            
            if is_valid:
                logger.info(f"Message passed validation")
            else:
                logger.warning(f"Message failed validation with errors:")
                for error in errors:
                    logger.warning(f"  - {error}")
            
            # Check if result matches expectation
            expected = test_case["expected_result"]
            if is_valid == expected:
                logger.info(f"Result matches expectation: {expected}")
            else:
                logger.error(f"Result does NOT match expectation: expected={expected}, actual={is_valid}")
        
        except Exception as e:
            logger.error(f"Error during validation: {str(e)}")
        
        print("-" * 40)
    
    # Test validation middleware
    print_separator("Testing Validation Middleware")
    middleware = SchemaValidationMiddleware(registry, strict_mode=True)
    
    for test_case in test_messages:
        logger.info(f"Processing with middleware: {test_case['name']}")
        message = test_case["message"]
        expected = test_case["expected_result"]
        
        try:
            # Process message with middleware
            result_message = middleware.process_incoming_message(message)
            logger.info(f"Message passed middleware validation")
            
            if expected:
                logger.info(f"Result matches expectation: expected=pass, actual=pass")
            else:
                logger.error(f"Result does NOT match expectation: expected=fail, actual=pass")
        
        except SchemaValidationError as e:
            logger.warning(f"Message failed middleware validation: {str(e)}")
            
            if not expected:
                logger.info(f"Result matches expectation: expected=fail, actual=fail")
            else:
                logger.error(f"Result does NOT match expectation: expected=pass, actual=fail")
        
        except Exception as e:
            logger.error(f"Error during middleware processing: {str(e)}")
        
        print("-" * 40)
    
    # Test decorators
    print_separator("Testing Validation Decorators")
    
    # Define handler functions with validation decorators
    @validate_incoming(registry, strict=True)
    def handle_incoming(message):
        logger.info(f"Handler received validated message: {message.message_id}")
        return message
    
    @validate_outgoing(registry, strict=True)
    def handle_outgoing(message):
        logger.info(f"Handler sending validated message: {message.message_id}")
        return message
    
    # Test decorators with messages
    for test_case in test_messages:
        logger.info(f"Testing decorated handler with: {test_case['name']}")
        message = test_case["message"]
        expected = test_case["expected_result"]
        
        # Test incoming handler
        try:
            result = handle_incoming(message)
            logger.info(f"Incoming handler succeeded")
            
            if expected:
                logger.info(f"Result matches expectation: expected=pass, actual=pass")
            else:
                logger.error(f"Result does NOT match expectation: expected=fail, actual=pass")
        
        except SchemaValidationError as e:
            logger.warning(f"Incoming handler failed validation: {str(e)}")
            
            if not expected:
                logger.info(f"Result matches expectation: expected=fail, actual=fail")
            else:
                logger.error(f"Result does NOT match expectation: expected=pass, actual=fail")
        
        except Exception as e:
            logger.error(f"Error in incoming handler: {str(e)}")
        
        print("-" * 20)
        
        # Test outgoing handler
        try:
            result = handle_outgoing(message)
            logger.info(f"Outgoing handler succeeded")
            
            if expected:
                logger.info(f"Result matches expectation: expected=pass, actual=pass")
            else:
                logger.error(f"Result does NOT match expectation: expected=fail, actual=pass")
        
        except SchemaValidationError as e:
            logger.warning(f"Outgoing handler failed validation: {str(e)}")
            
            if not expected:
                logger.info(f"Result matches expectation: expected=fail, actual=fail")
            else:
                logger.error(f"Result does NOT match expectation: expected=pass, actual=fail")
        
        except Exception as e:
            logger.error(f"Error in outgoing handler: {str(e)}")
        
        print("-" * 40)
    
    # Test with non-strict mode
    print_separator("Testing Non-Strict Mode")
    non_strict_middleware = SchemaValidationMiddleware(registry, strict_mode=False)
    
    for test_case in test_messages:
        logger.info(f"Processing with non-strict middleware: {test_case['name']}")
        message = test_case["message"]
        
        try:
            # Process message with non-strict middleware
            result_message = non_strict_middleware.process_incoming_message(message)
            
            # All messages should pass in non-strict mode
            logger.info(f"Message processed in non-strict mode (validation issues are logged but not raised)")
        
        except Exception as e:
            logger.error(f"Unexpected error in non-strict mode: {str(e)}")
        
        print("-" * 40)
    
    print_separator("Example Completed")
    logger.info("Schema Validation Example completed successfully")

if __name__ == "__main__":
    main()
