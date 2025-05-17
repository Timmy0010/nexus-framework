"""
Example demonstrating the VerificationAgent functionality.

This script shows how to set up and use the VerificationAgent to 
validate and sanitize messages in the Nexus Framework.
"""

import logging
import os
import json
import uuid
from typing import Dict, Any

from nexus_framework.core.message import Message
from nexus_framework.agents.verification.verification_agent import VerificationAgent
from nexus_framework.agents.verification.rules.content_rule import ContentVerificationRule
from nexus_framework.agents.verification.rules.schema_rule import SchemaVerificationRule
from nexus_framework.agents.verification.rules.size_rule import SizeVerificationRule
from nexus_framework.agents.verification.sanitizers.content_sanitizer import ContentSanitizer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger("verification_example")

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
            content="This is a valid message",
            sender_id="test_sender",
            recipient_id="test_recipient",
            message_type="text_message",
            payload={
                "text": "Hello World!",
                "language": "en"
            }
        ),
        "expected_result": True  # Should pass verification
    })
    
    # Message with invalid schema (missing required field)
    messages.append({
        "name": "Invalid Schema Message",
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
        "expected_result": False  # Should fail verification
    })
    
    # Message with malicious content
    messages.append({
        "name": "Malicious Content Message",
        "message": Message(
            message_id=str(uuid.uuid4()),
            content="This message has potentially malicious content",
            sender_id="test_sender",
            recipient_id="test_recipient",
            message_type="text_message",
            payload={
                "text": "Hello <script>alert('XSS')</script>",
                "language": "en"
            }
        ),
        "expected_result": False  # Should fail verification
    })
    
    # Message with SQL injection attempt
    messages.append({
        "name": "SQL Injection Message",
        "message": Message(
            message_id=str(uuid.uuid4()),
            content="This message has an SQL injection attempt",
            sender_id="test_sender",
            recipient_id="test_recipient",
            message_type="text_message",
            payload={
                "text": "User'; DROP TABLE users; --",
                "language": "en"
            }
        ),
        "expected_result": False  # Should fail verification
    })
    
    # Message with oversized payload
    large_text = "A" * 50000  # 50KB string
    messages.append({
        "name": "Oversized Message",
        "message": Message(
            message_id=str(uuid.uuid4()),
            content="This message has an oversized payload",
            sender_id="test_sender",
            recipient_id="test_recipient",
            message_type="text_message",
            payload={
                "text": large_text,
                "language": "en"
            }
        ),
        "expected_result": False  # Should fail verification
    })
    
    # Message with content that can be sanitized
    messages.append({
        "name": "Sanitizable Message",
        "message": Message(
            message_id=str(uuid.uuid4()),
            content="This message has content that can be sanitized",
            sender_id="test_sender",
            recipient_id="test_recipient",
            message_type="text_message",
            payload={
                "text": "Hello <script>alert('XSS')</script> World",
                "language": "en"
            }
        ),
        "expected_result": False,  # Should fail verification
        "can_sanitize": True       # But should be sanitizable
    })
    
    return messages

def main():
    """Run the verification agent example."""
    logger.info("Starting Verification Agent Example")
    
    # Create temporary directory for verification config
    config_dir = "verification_example_config"
    os.makedirs(config_dir, exist_ok=True)
    
    # Create verification agent
    print_separator("Creating Verification Agent")
    verification_agent = VerificationAgent()
    logger.info(f"Created verification agent with {len(verification_agent.rules)} rules")
    
    # Log registered rules and sanitizers
    for rule_name in verification_agent.rules:
        logger.info(f"Registered rule: {rule_name}")
    
    for sanitizer_name in verification_agent.sanitizers:
        logger.info(f"Registered sanitizer: {sanitizer_name}")
    
    # Create test messages
    print_separator("Creating Test Messages")
    test_messages = create_messages()
    logger.info(f"Created {len(test_messages)} test messages")
    
    # Process each message
    print_separator("Processing Messages")
    for test_case in test_messages:
        logger.info(f"Processing message: {test_case['name']}")
        
        # Process the message
        message = test_case["message"]
        
        # Verify the message directly first
        passed, results = verification_agent.verify_message(message)
        
        # Log verification results
        if passed:
            logger.info(f"Message passed verification")
        else:
            logger.warning(f"Message failed verification with risk level: {results['risk_level']}")
            
            # Log detailed results
            for rule_name, rule_result in results.get("rule_results", {}).items():
                if not rule_result.get("passed", True):
                    logger.warning(f"  Failed rule '{rule_name}': {rule_result.get('reason', 'No reason provided')}")
        
        # Check if result matches expectation
        expected = test_case["expected_result"]
        if passed == expected:
            logger.info(f"Result matches expectation: {expected}")
        else:
            logger.error(f"Result does NOT match expectation: expected={expected}, actual={passed}")
        
        # If message failed verification, try sanitization if applicable
        if not passed and test_case.get("can_sanitize", False):
            logger.info("Attempting to sanitize message")
            
            # Sanitize the message
            sanitized_message, sanitized = verification_agent.sanitize_message(message, results)
            
            if sanitized:
                logger.info(f"Message was successfully sanitized")
                
                # Verify the sanitized message
                sanitized_passed, sanitized_results = verification_agent.verify_message(sanitized_message)
                
                if sanitized_passed:
                    logger.info(f"Sanitized message now passes verification")
                else:
                    logger.warning(f"Sanitized message still fails verification: {sanitized_results.get('risk_level', 'unknown')}")
            else:
                logger.warning(f"Message could not be sanitized")
        
        print("-" * 40)
    
    # Process messages using the agent's main entry point
    print_separator("Processing Messages via Agent API")
    for test_case in test_messages:
        logger.info(f"Processing message via agent: {test_case['name']}")
        
        # Process the message
        message = test_case["message"]
        result_message = verification_agent.process_message(message)
        
        if result_message is message:
            logger.info(f"Message passed verification and was returned unchanged")
        elif result_message:
            logger.info(f"Message was processed and transformed")
            
            # Check if it's a verification result message
            if hasattr(result_message, 'message_type') and result_message.message_type == "verification_result":
                logger.warning(f"Verification result message was returned with summary:")
                if hasattr(result_message, 'payload'):
                    payload = result_message.payload
                    logger.warning(f"  Verified: {payload.get('verified', False)}")
                    logger.warning(f"  Risk level: {payload.get('risk_level', 'unknown')}")
                    logger.warning(f"  Actions taken: {', '.join(payload.get('actions_taken', []))}")
            else:
                logger.info(f"Message was sanitized and now passes verification")
        else:
            logger.warning(f"Message was rejected (None returned)")
        
        print("-" * 40)
    
    print_separator("Example Completed")
    logger.info("Verification Agent Example completed successfully")

if __name__ == "__main__":
    main()
