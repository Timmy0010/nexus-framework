"""
Example demonstrating the usage of the VerificationAgent.

This script shows how to set up a VerificationAgent with custom validators and
sanitizers, and how to integrate it into the Nexus messaging pipeline.
"""

import logging
import uuid
import json
import yaml
from typing import Dict, Any, Optional

from nexus_framework.core.message import Message
from nexus_framework.security import (
    VerificationAgent,
    SchemaValidator,
    SizeValidator,
    ContentValidator,
    PermissionValidator,
    SizeLimitSanitizer,
    ContentFilterSanitizer,
    JsonSanitizer
)

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_config(config_path: str) -> Dict[str, Any]:
    """
    Load configuration from a YAML file.
    
    Args:
        config_path: Path to the configuration file
        
    Returns:
        Configuration dictionary
    """
    try:
        with open(config_path, 'r') as file:
            return yaml.safe_load(file)
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        return {}

def create_verification_agent_from_config(config: Dict[str, Any]) -> VerificationAgent:
    """
    Create a VerificationAgent from configuration.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Configured VerificationAgent
    """
    # Create a verification agent
    agent = VerificationAgent(agent_name=config.get("agent_name", "VerificationAgent"))
    
    # Load validators
    for validator_config in config.get("validators", []):
        validator_type = validator_config.get("type")
        validator_params = validator_config.get("params", {})
        
        if validator_type == "schema":
            validator = SchemaValidator(**validator_params)
        elif validator_type == "size":
            validator = SizeValidator(**validator_params)
        elif validator_type == "content":
            validator = ContentValidator(**validator_params)
        elif validator_type == "permission":
            validator = PermissionValidator(**validator_params)
        else:
            logger.warning(f"Unknown validator type: {validator_type}")
            continue
            
        agent.register_validator(validator)
        logger.info(f"Registered {validator_type} validator")
    
    # Load sanitizers
    for sanitizer_config in config.get("sanitizers", []):
        sanitizer_type = sanitizer_config.get("type")
        sanitizer_params = sanitizer_config.get("params", {})
        
        if sanitizer_type == "size_limit":
            sanitizer = SizeLimitSanitizer(**sanitizer_params)
        elif sanitizer_type == "content_filter":
            sanitizer = ContentFilterSanitizer(**sanitizer_params)
        elif sanitizer_type == "json":
            sanitizer = JsonSanitizer(**sanitizer_params)
        else:
            logger.warning(f"Unknown sanitizer type: {sanitizer_type}")
            continue
            
        agent.register_sanitizer(sanitizer)
        logger.info(f"Registered {sanitizer_type} sanitizer")
    
    return agent

def create_test_message(content: Any, sender_id: str = "test_sender", 
                      recipient_id: str = "test_recipient", 
                      message_type: str = "text_message") -> Message:
    """
    Create a test message.
    
    Args:
        content: Message content
        sender_id: Sender ID
        recipient_id: Recipient ID
        message_type: Message type
        
    Returns:
        A test message
    """
    return Message(
        message_id=str(uuid.uuid4()),
        sender_id=sender_id,
        recipient_id=recipient_id,
        content=content,
        metadata={
            "message_type": message_type,
            "schema_version": "1.0"
        }
    )

def demonstrate_verification_agent():
    """
    Demonstrate the usage of the VerificationAgent with various message types.
    """
    # Configuration for the verification agent
    config = {
        "agent_name": "SecurityVerifier",
        "validators": [
            {
                "type": "size",
                "params": {
                    "max_message_size": 1048576,  # 1MB
                    "max_content_size": 524288,   # 512KB
                    "max_metadata_size": 16384    # 16KB
                }
            },
            {
                "type": "content",
                "params": {
                    "forbidden_patterns": [
                        "password\\s*=",
                        "api[-_]?key\\s*=",
                        "exec\\s*\\(",
                        "eval\\s*\\("
                    ],
                    "allowed_domains": [
                        "example.com",
                        "nexus-framework.org",
                        "github.com"
                    ],
                    "max_url_count": 5
                }
            },
            {
                "type": "permission",
                "params": {
                    "acl": {
                        "user_agent": {
                            "assistant_agent": True,
                            "verification_agent": True,
                            "*": False
                        },
                        "assistant_agent": {
                            "user_agent": True,
                            "tool_agent": True,
                            "*": False
                        }
                    }
                }
            }
        ],
        "sanitizers": [
            {
                "type": "size_limit",
                "params": {
                    "max_content_length": 10000,
                    "max_field_lengths": {
                        "content.text": 5000,
                        "content.subject": 200,
                        "metadata.description": 1000
                    }
                }
            },
            {
                "type": "content_filter",
                "params": {
                    "filtered_terms": [
                        "badword1",
                        "badword2",
                        "malicioustag"
                    ],
                    "replacement": "[FILTERED]",
                    "filter_urls": True,
                    "allowed_domains": [
                        "example.com",
                        "nexus-framework.org",
                        "github.com"
                    ]
                }
            },
            {
                "type": "json",
                "params": {
                    "disallowed_keys": [
                        "password",
                        "api_key",
                        "secret",
                        "token"
                    ],
                    "max_depth": 5,
                    "escape_html": True
                }
            }
        ]
    }
    
    # Create a verification agent from configuration
    agent = create_verification_agent_from_config(config)
    logger.info(f"Created {agent.agent_name} with {len(agent.validators)} validators and {len(agent.sanitizers)} sanitizers")
    
    # Test message 1: Valid text message
    message1 = create_test_message(
        content="Hello, world! This is a test message.",
        sender_id="user_agent",
        recipient_id="assistant_agent",
        message_type="text_message"
    )
    
    logger.info("-" * 50)
    logger.info("Test 1: Valid text message")
    result1 = agent.process_message(message1)
    logger.info(f"Processed message: {result1.message_id if result1 else 'Rejected'}")
    
    # Test message 2: Message with forbidden content
    message2 = create_test_message(
        content="Hello, please use password=secret123 to access the system.",
        sender_id="user_agent",
        recipient_id="assistant_agent",
        message_type="text_message"
    )
    
    logger.info("-" * 50)
    logger.info("Test 2: Message with forbidden content")
    result2 = agent.process_message(message2)
    if result2:
        logger.info(f"Message sanitized: {result2.content}")
    else:
        logger.info("Message rejected")
    
    # Test message 3: Oversized message
    large_content = "A" * 20000
    message3 = create_test_message(
        content=large_content,
        sender_id="user_agent",
        recipient_id="assistant_agent",
        message_type="text_message"
    )
    
    logger.info("-" * 50)
    logger.info("Test 3: Oversized message")
    result3 = agent.process_message(message3)
    if result3:
        logger.info(f"Message sanitized: content length {len(result3.content)} (original: {len(large_content)})")
    else:
        logger.info("Message rejected")
    
    # Test message 4: JSON message with sensitive keys
    message4 = create_test_message(
        content={
            "username": "testuser",
            "password": "secret123",
            "data": {
                "api_key": "abc123",
                "settings": {
                    "theme": "dark",
                    "notifications": True
                }
            }
        },
        sender_id="user_agent",
        recipient_id="assistant_agent",
        message_type="json_message"
    )
    
    logger.info("-" * 50)
    logger.info("Test 4: JSON message with sensitive keys")
    result4 = agent.process_message(message4)
    if result4:
        logger.info(f"Message sanitized: {json.dumps(result4.content)}")
    else:
        logger.info("Message rejected")
    
    # Test message 5: Message with unauthorized sender/recipient
    message5 = create_test_message(
        content="Hello from unauthorized sender",
        sender_id="unknown_agent",
        recipient_id="assistant_agent",
        message_type="text_message"
    )
    
    logger.info("-" * 50)
    logger.info("Test 5: Message with unauthorized sender/recipient")
    result5 = agent.process_message(message5)
    if result5:
        logger.info(f"Message allowed: {result5.content}")
    else:
        logger.info("Message rejected as expected")

if __name__ == "__main__":
    demonstrate_verification_agent()
