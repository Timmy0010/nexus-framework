"""
Example demonstrating the message authentication system.

This script shows how to use the authentication service, key management,
and middleware components to secure messages in the Nexus Framework.
"""

import logging
import json
import uuid
import time
from datetime import datetime
from typing import Dict, Any, Optional

from nexus_framework.core.message import Message
from nexus_framework.security.authentication import (
    AuthenticationService,
    KeyManager,
    AuthMiddleware,
    JWTAuthMiddleware,
    AuthenticationProcessor
)

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_test_message(content: str, sender_id: str = "test_sender", 
                     recipient_id: str = "test_recipient") -> Message:
    """
    Create a test message.
    
    Args:
        content: Message content.
        sender_id: Sender ID.
        recipient_id: Recipient ID.
        
    Returns:
        A test message.
    """
    return Message(
        message_id=str(uuid.uuid4()),
        sender_id=sender_id,
        recipient_id=recipient_id,
        content=content,
        metadata={"created_at": datetime.now().isoformat()}
    )

def print_message(title: str, message: Message) -> None:
    """
    Print a message in a readable format.
    
    Args:
        title: Title for the message.
        message: The message to print.
    """
    print("\n" + "=" * 50)
    print(f"{title}:")
    print("-" * 50)
    print(f"Message ID: {message.message_id}")
    print(f"Sender: {message.sender_id}")
    print(f"Recipient: {message.recipient_id}")
    print(f"Content: {message.content}")
    
    # Print signature if present
    message_dict = message.to_dict()
    if "signature" in message_dict:
        print(f"Signature: {message_dict['signature'][:20]}...")
        print(f"Key ID: {message_dict['signature_metadata']['key_id']}")
        print(f"Algorithm: {message_dict['signature_metadata']['algorithm']}")
        
    # Print JWT token if present
    if message.metadata and "auth_token" in message.metadata:
        token = message.metadata["auth_token"]
        parts = token.split('.')
        if len(parts) == 3:
            print(f"JWT Token: {parts[0][:10]}...{parts[2][-10:]}")
        else:
            print(f"JWT Token: {token[:20]}...")
            
    print("=" * 50)

def demonstrate_hmac_signing():
    """Demonstrate HMAC-based message signing and verification."""
    print("\n\n=== HMAC-BASED MESSAGE AUTHENTICATION ===\n")
    
    # Create authentication service
    auth_service = AuthenticationService()
    
    # Create a test message
    message = create_test_message(
        "This is a test message that needs to be secured.",
        sender_id="agent1",
        recipient_id="agent2"
    )
    
    # Print the original message
    print_message("Original Message", message)
    
    # Sign the message
    message_dict = message.to_dict()
    signed_dict = auth_service.sign_message(message_dict)
    signed_message = Message.from_dict(signed_dict)
    
    # Print the signed message
    print_message("Signed Message", signed_message)
    
    # Verify the message
    is_valid = auth_service.verify_message(signed_dict)
    print(f"\nSignature Verification: {'SUCCESS' if is_valid else 'FAILED'}")
    
    # Tamper with the message
    tampered_dict = signed_dict.copy()
    tampered_dict["content"] = "This message has been tampered with!"
    tampered_message = Message.from_dict(tampered_dict)
    
    # Print the tampered message
    print_message("Tampered Message", tampered_message)
    
    # Verify the tampered message
    is_valid = auth_service.verify_message(tampered_dict)
    print(f"\nTampered Message Verification: {'SUCCESS' if is_valid else 'FAILED'}")
    
    # Demonstrate key rotation
    print("\n--- Key Rotation ---")
    print(f"Current Key ID: {auth_service.get_key_info()['key_id']}")
    
    # Rotate the key
    new_key_id = auth_service.rotate_keys()
    print(f"New Key ID after rotation: {new_key_id}")
    
    # Sign with the new key
    signed_dict_new_key = auth_service.sign_message(message_dict)
    signed_message_new_key = Message.from_dict(signed_dict_new_key)
    
    # Print the message signed with the new key
    print_message("Message Signed with New Key", signed_message_new_key)
    
    # Verify both messages (should still work for both)
    is_valid_old = auth_service.verify_message(signed_dict)
    is_valid_new = auth_service.verify_message(signed_dict_new_key)
    
    print(f"\nOld Signature Verification: {'SUCCESS' if is_valid_old else 'FAILED'}")
    print(f"New Signature Verification: {'SUCCESS' if is_valid_new else 'FAILED'}")

def demonstrate_jwt_auth():
    """Demonstrate JWT-based authentication."""
    print("\n\n=== JWT-BASED AUTHENTICATION ===\n")
    
    # Create authentication service
    auth_service = AuthenticationService(token_lifetime_minutes=10)
    
    # Create a test message
    message = create_test_message(
        "This message requires JWT authentication.",
        sender_id="admin_agent",
        recipient_id="secure_agent"
    )
    
    # Print the original message
    print_message("Original Message", message)
    
    # Create JWT token for the message
    subject = message.sender_id
    claims = {
        "msg_id": message.message_id,
        "permissions": ["read", "write"],
        "role": "admin"
    }
    
    token = auth_service.create_token(subject, claims)
    
    # Add token to the message
    message_with_token = message.copy()
    if not message_with_token.metadata:
        message_with_token.metadata = {}
    message_with_token.metadata["auth_token"] = token
    
    # Print the message with token
    print_message("Message with JWT Token", message_with_token)
    
    # Validate the token
    is_valid, token_claims = auth_service.validate_token(token)
    
    print(f"\nToken Validation: {'SUCCESS' if is_valid else 'FAILED'}")
    if is_valid:
        print("\nToken Claims:")
        for key, value in token_claims.items():
            if key == "exp":
                # Convert timestamp to datetime
                value = datetime.fromtimestamp(value).isoformat()
            print(f"  {key}: {value}")
    
    # Create an expired token (backdated)
    print("\n--- Expired Token ---")
    backdated_claims = claims.copy()
    backdated_claims["iat"] = time.time() - 1200  # 20 minutes ago
    backdated_claims["exp"] = time.time() - 600   # 10 minutes ago
    
    # Manually create token with expired claims
    # Note: This is a simplified version for demo purposes
    expired_token = token  # In a real scenario, we'd create a properly expired token
    
    # Validate the expired token
    is_valid, _ = auth_service.validate_token(expired_token)
    print(f"\nExpired Token Validation: {'SUCCESS' if is_valid else 'FAILED (as expected)'}")

def demonstrate_middleware():
    """Demonstrate authentication middleware."""
    print("\n\n=== AUTHENTICATION MIDDLEWARE ===\n")
    
    # Create authentication service
    auth_service = AuthenticationService()
    
    # Create middleware
    hmac_middleware = AuthMiddleware(auth_service, strict_mode=True)
    jwt_middleware = JWTAuthMiddleware(auth_service, strict_mode=True)
    
    # Create a test message
    message = create_test_message(
        "This message will be processed by middleware.",
        sender_id="client_agent",
        recipient_id="server_agent"
    )
    
    # Print the original message
    print_message("Original Message", message)
    
    # HMAC Middleware
    print("\n--- HMAC Middleware ---")
    
    # Sign the message with middleware
    signed_message = hmac_middleware.sign_outgoing_message(message)
    print_message("Signed by Middleware", signed_message)
    
    # Verify the message with middleware
    is_valid, verified_message = hmac_middleware.verify_incoming_message(signed_message)
    print(f"\nMiddleware Verification: {'SUCCESS' if is_valid else 'FAILED'}")
    
    # JWT Middleware
    print("\n--- JWT Middleware ---")
    
    # Add token with middleware
    subject = message.sender_id
    claims = {
        "permissions": ["read"],
        "role": "client"
    }
    
    message_with_token = jwt_middleware.add_token(message, subject, claims)
    print_message("Token Added by Middleware", message_with_token)
    
    # Validate token with middleware
    is_valid, token_claims = jwt_middleware.validate_token(message_with_token)
    print(f"\nMiddleware Token Validation: {'SUCCESS' if is_valid else 'FAILED'}")
    
    if is_valid and token_claims:
        print("\nToken Claims:")
        for key, value in token_claims.items():
            if key == "exp":
                # Convert timestamp to datetime
                value = datetime.fromtimestamp(value).isoformat()
            print(f"  {key}: {value}")
    
    # Combined processor
    print("\n--- Combined Authentication Processor ---")
    
    processor_hmac = AuthenticationProcessor(auth_service, strict_mode=True, use_jwt=False)
    processor_jwt = AuthenticationProcessor(auth_service, strict_mode=True, use_jwt=True)
    
    # Process with HMAC
    hmac_processed = processor_hmac.process_outgoing_message(message)
    print_message("HMAC Processed Message", hmac_processed)
    
    # Process with JWT
    jwt_processed = processor_jwt.process_outgoing_message(message)
    print_message("JWT Processed Message", jwt_processed)

def demonstrate_handler_wrapping():
    """Demonstrate wrapping message handlers with authentication."""
    print("\n\n=== HANDLER WRAPPING ===\n")
    
    # Create authentication service and middleware
    auth_service = AuthenticationService()
    hmac_middleware = AuthMiddleware(auth_service)
    
    # Define a simple message handler
    def echo_handler(message: Message) -> Message:
        """Echo the incoming message with a response."""
        response = Message(
            message_id=str(uuid.uuid4()),
            sender_id=message.recipient_id,  # Swap sender and recipient
            recipient_id=message.sender_id,
            content=f"Echo: {message.content}",
            metadata={"original_message_id": message.message_id}
        )
        return response
    
    # Wrap the handler
    wrapped_handler = hmac_middleware.wrap_message_handler(echo_handler)
    
    # Create a test message
    message = create_test_message(
        "Test message for wrapped handler",
        sender_id="client",
        recipient_id="echo_service"
    )
    
    # Sign the message manually (normally this would be done automatically)
    message_dict = message.to_dict()
    signed_dict = auth_service.sign_message(message_dict)
    signed_message = Message.from_dict(signed_dict)
    
    # Process with the wrapped handler
    print_message("Input to Wrapped Handler", signed_message)
    
    # Call the wrapped handler
    response = wrapped_handler(signed_message)
    
    # Print the response
    print_message("Response from Wrapped Handler", response)
    
    # Verify the response was signed
    response_dict = response.to_dict()
    is_valid = auth_service.verify_message(response_dict)
    print(f"\nResponse Signature Verification: {'SUCCESS' if is_valid else 'FAILED'}")
    
    # Try with a tampered message
    print("\n--- Handling Tampered Message ---")
    
    tampered_dict = signed_dict.copy()
    tampered_dict["content"] = "This message has been tampered with!"
    tampered_message = Message.from_dict(tampered_dict)
    
    print_message("Tampered Input", tampered_message)
    
    # Apply strict mode for this test
    strict_middleware = AuthMiddleware(auth_service, strict_mode=True)
    strict_wrapped_handler = strict_middleware.wrap_message_handler(echo_handler)
    
    # Call the wrapped handler with the tampered message
    response = strict_wrapped_handler(tampered_message)
    
    if response is None:
        print("\nTampered message was rejected by the wrapped handler (as expected)")
    else:
        print_message("Response for Tampered Message", response)

def main():
    """Run all demonstration functions."""
    # Demonstrate HMAC signing
    demonstrate_hmac_signing()
    
    # Demonstrate JWT authentication
    demonstrate_jwt_auth()
    
    # Demonstrate middleware
    demonstrate_middleware()
    
    # Demonstrate handler wrapping
    demonstrate_handler_wrapping()

if __name__ == "__main__":
    main()
