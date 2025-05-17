"""
Message authentication middleware for the Nexus Framework.

This module provides middleware components that integrate with the messaging
system to automatically sign outgoing messages and verify incoming messages.
"""

import logging
import threading
from typing import Dict, Any, Optional, Callable, List, Tuple

from .auth_service import AuthenticationService, AuthenticationError
from ...core.message import Message

logger = logging.getLogger(__name__)

class AuthMiddleware:
    """
    Middleware for message authentication.
    
    This middleware can be inserted into the message processing pipeline
    to automatically sign outgoing messages and verify incoming messages.
    """
    
    def __init__(self, auth_service: Optional[AuthenticationService] = None,
                strict_mode: bool = False,
                exempt_paths: Optional[List[str]] = None):
        """
        Initialize the authentication middleware.
        
        Args:
            auth_service: Authentication service for signing and verification.
            strict_mode: If True, reject messages with invalid signatures.
                       If False, accept them but log a warning.
            exempt_paths: List of message paths that are exempt from authentication.
                        Format: "sender_id:recipient_id"
        """
        self.auth_service = auth_service or AuthenticationService()
        self.strict_mode = strict_mode
        self.exempt_paths = exempt_paths or [
            # Common exempt paths
            "verification_agent:*",  # Messages from verification agent to anyone
            "*:verification_agent",  # Messages to verification agent from anyone
            "user_agent:*",          # Messages from user agent to anyone (user input)
            "*:user_agent"           # Messages to user agent from anyone (final output)
        ]
        
        # Compile exempt path patterns
        self.exempt_patterns = []
        for path in self.exempt_paths:
            parts = path.split(':')
            if len(parts) != 2:
                logger.warning(f"Invalid exempt path format: {path}")
                continue
                
            sender_pattern, recipient_pattern = parts
            self.exempt_patterns.append((sender_pattern, recipient_pattern))
        
        logger.info(f"Authentication middleware initialized (strict_mode={strict_mode})")
    
    def _is_exempt(self, message: Message) -> bool:
        """
        Check if a message is exempt from authentication.
        
        Args:
            message: The message to check.
            
        Returns:
            True if the message is exempt, False otherwise.
        """
        sender_id = message.sender_id
        recipient_id = message.recipient_id
        
        for sender_pattern, recipient_pattern in self.exempt_patterns:
            # Check sender match
            sender_match = (sender_pattern == '*' or sender_pattern == sender_id)
            
            # Check recipient match
            recipient_match = (recipient_pattern == '*' or recipient_pattern == recipient_id)
            
            if sender_match and recipient_match:
                return True
                
        return False
    
    def sign_outgoing_message(self, message: Message) -> Message:
        """
        Sign an outgoing message.
        
        Args:
            message: The message to sign.
            
        Returns:
            The signed message.
        """
        # Check if message is exempt
        if self._is_exempt(message):
            logger.debug(f"Message exempt from signing: {message.message_id}")
            return message
        
        try:
            # Convert message to dict for signing
            message_dict = message.to_dict()
            
            # Sign the message
            signed_dict = self.auth_service.sign_message(message_dict)
            
            # Convert back to Message
            return Message.from_dict(signed_dict)
        except Exception as e:
            logger.error(f"Failed to sign message {message.message_id}: {e}")
            # Return the original message in case of error
            return message
    
    def verify_incoming_message(self, message: Message) -> Tuple[bool, Message]:
        """
        Verify an incoming message.
        
        Args:
            message: The message to verify.
            
        Returns:
            Tuple of (is_valid, message).
            If strict_mode is False, message is always the original message.
            If strict_mode is True and verification fails, message is None.
        """
        # Check if message is exempt
        if self._is_exempt(message):
            logger.debug(f"Message exempt from verification: {message.message_id}")
            return True, message
        
        # Convert message to dict for verification
        message_dict = message.to_dict()
        
        # Check if message has a signature
        if "signature" not in message_dict or "signature_metadata" not in message_dict:
            logger.warning(f"Message {message.message_id} has no signature")
            return not self.strict_mode, message
        
        try:
            # Verify the message
            is_valid = self.auth_service.verify_message(message_dict)
            
            if not is_valid:
                logger.warning(f"Invalid signature for message {message.message_id}")
                if self.strict_mode:
                    return False, None
            else:
                logger.debug(f"Signature verified for message {message.message_id}")
                
            return is_valid, message
        except Exception as e:
            logger.error(f"Error verifying message {message.message_id}: {e}")
            if self.strict_mode:
                return False, None
                
            return False, message
    
    def wrap_message_handler(self, handler: Callable[[Message], Optional[Message]]) -> Callable[[Message], Optional[Message]]:
        """
        Wrap a message handler to automatically verify incoming messages
        and sign outgoing messages.
        
        Args:
            handler: The original message handler function.
            
        Returns:
            A wrapped handler function.
        """
        def wrapped_handler(message: Message) -> Optional[Message]:
            # Verify incoming message
            is_valid, verified_message = self.verify_incoming_message(message)
            
            if not is_valid and self.strict_mode:
                logger.warning(f"Rejected message {message.message_id} due to invalid signature")
                return None
            
            # Process the message
            response = handler(verified_message)
            
            # Sign outgoing message if there is one
            if response is not None:
                response = self.sign_outgoing_message(response)
                
            return response
            
        return wrapped_handler

class JWTAuthMiddleware:
    """
    Middleware for JWT-based authentication and authorization.
    
    This middleware uses JWT tokens for more complex authorization scenarios.
    """
    
    def __init__(self, auth_service: Optional[AuthenticationService] = None,
                strict_mode: bool = True,
                exempt_paths: Optional[List[str]] = None,
                required_claims: Optional[List[str]] = None):
        """
        Initialize the JWT authentication middleware.
        
        Args:
            auth_service: Authentication service for JWT operations.
            strict_mode: If True, reject messages without valid tokens.
            exempt_paths: List of message paths exempt from JWT auth.
            required_claims: List of claims that must be present in the token.
        """
        self.auth_service = auth_service or AuthenticationService()
        self.strict_mode = strict_mode
        self.exempt_paths = exempt_paths or [
            "verification_agent:*",
            "*:verification_agent",
            "user_agent:*",
            "*:user_agent"
        ]
        self.required_claims = required_claims or ["sub", "exp"]
        
        # Compile exempt path patterns
        self.exempt_patterns = []
        for path in self.exempt_paths:
            parts = path.split(':')
            if len(parts) != 2:
                logger.warning(f"Invalid exempt path format: {path}")
                continue
                
            sender_pattern, recipient_pattern = parts
            self.exempt_patterns.append((sender_pattern, recipient_pattern))
        
        logger.info(f"JWT authentication middleware initialized (strict_mode={strict_mode})")
    
    def _is_exempt(self, message: Message) -> bool:
        """
        Check if a message is exempt from JWT authentication.
        
        Args:
            message: The message to check.
            
        Returns:
            True if the message is exempt, False otherwise.
        """
        sender_id = message.sender_id
        recipient_id = message.recipient_id
        
        for sender_pattern, recipient_pattern in self.exempt_patterns:
            # Check sender match
            sender_match = (sender_pattern == '*' or sender_pattern == sender_id)
            
            # Check recipient match
            recipient_match = (recipient_pattern == '*' or recipient_pattern == recipient_id)
            
            if sender_match and recipient_match:
                return True
                
        return False
    
    def validate_token(self, message: Message) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Validate the JWT token in a message.
        
        Args:
            message: The message containing the token.
            
        Returns:
            Tuple of (is_valid, claims). If not valid, claims is None.
        """
        # Check if message is exempt
        if self._is_exempt(message):
            logger.debug(f"Message exempt from JWT validation: {message.message_id}")
            return True, {}
        
        # Check if message has a token
        token = None
        if message.metadata and "auth_token" in message.metadata:
            token = message.metadata["auth_token"]
        
        if not token:
            logger.warning(f"Message {message.message_id} has no JWT token")
            return not self.strict_mode, None
        
        # Validate the token
        is_valid, claims = self.auth_service.validate_token(token)
        
        if not is_valid:
            logger.warning(f"Invalid JWT token in message {message.message_id}")
            return False, None
        
        # Check required claims
        for claim in self.required_claims:
            if claim not in claims:
                logger.warning(f"Missing required claim '{claim}' in token for message {message.message_id}")
                return False, None
        
        logger.debug(f"JWT token validated for message {message.message_id}")
        return True, claims
    
    def add_token(self, message: Message, subject: str, claims: Optional[Dict[str, Any]] = None) -> Message:
        """
        Add a JWT token to a message.
        
        Args:
            message: The message to add the token to.
            subject: Subject for the token (usually sender ID).
            claims: Additional claims to include in the token.
            
        Returns:
            The message with the added token.
        """
        # Check if message is exempt
        if self._is_exempt(message):
            logger.debug(f"Message exempt from JWT addition: {message.message_id}")
            return message
        
        try:
            # Create a copy to avoid modifying the original
            message_copy = message.copy()
            
            # Create the token
            token = self.auth_service.create_token(subject, claims)
            
            # Add the token to metadata
            if not message_copy.metadata:
                message_copy.metadata = {}
                
            message_copy.metadata["auth_token"] = token
            
            return message_copy
        except Exception as e:
            logger.error(f"Failed to add JWT token to message {message.message_id}: {e}")
            # Return the original message in case of error
            return message
    
    def wrap_message_handler(self, handler: Callable[[Message, Optional[Dict[str, Any]]], Optional[Message]]) -> Callable[[Message], Optional[Message]]:
        """
        Wrap a message handler to automatically validate JWT tokens
        and add tokens to outgoing messages.
        
        Args:
            handler: The original message handler function, which takes
                   a message and optional claims as arguments.
            
        Returns:
            A wrapped handler function.
        """
        def wrapped_handler(message: Message) -> Optional[Message]:
            # Validate the token
            is_valid, claims = self.validate_token(message)
            
            if not is_valid and self.strict_mode:
                logger.warning(f"Rejected message {message.message_id} due to invalid JWT token")
                return None
            
            # Process the message
            response = handler(message, claims)
            
            # Add token to outgoing message if there is one
            if response is not None:
                # Use the sender ID as the subject
                subject = response.sender_id
                
                # Create claims based on the message
                response_claims = {
                    "msg_id": response.message_id,
                    "sender": response.sender_id,
                    "recipient": response.recipient_id
                }
                
                # Add the token
                response = self.add_token(response, subject, response_claims)
                
            return response
            
        return wrapped_handler

class AuthenticationProcessor:
    """
    Message processor that handles both HMAC and JWT authentication.
    
    This class combines both authentication approaches and can be used
    as a standalone processor or integrated with the communication bus.
    """
    
    def __init__(self, auth_service: Optional[AuthenticationService] = None,
                strict_mode: bool = False,
                use_jwt: bool = False,
                exempt_paths: Optional[List[str]] = None):
        """
        Initialize the authentication processor.
        
        Args:
            auth_service: Authentication service for crypto operations.
            strict_mode: If True, reject messages with invalid authentication.
            use_jwt: If True, use JWT tokens instead of HMAC signatures.
            exempt_paths: List of message paths exempt from authentication.
        """
        self.auth_service = auth_service or AuthenticationService()
        self.hmac_middleware = AuthMiddleware(auth_service, strict_mode, exempt_paths)
        self.jwt_middleware = JWTAuthMiddleware(auth_service, strict_mode, exempt_paths)
        self.use_jwt = use_jwt
        
        logger.info(f"Authentication processor initialized (strict_mode={strict_mode}, use_jwt={use_jwt})")
    
    def process_outgoing_message(self, message: Message) -> Message:
        """
        Process an outgoing message by adding authentication.
        
        Args:
            message: The message to process.
            
        Returns:
            The processed message.
        """
        if self.use_jwt:
            # Use the sender ID as the subject
            subject = message.sender_id
            
            # Create claims based on the message
            claims = {
                "msg_id": message.message_id,
                "sender": message.sender_id,
                "recipient": message.recipient_id
            }
            
            # Add the token
            return self.jwt_middleware.add_token(message, subject, claims)
        else:
            # Sign the message
            return self.hmac_middleware.sign_outgoing_message(message)
    
    def process_incoming_message(self, message: Message) -> Tuple[bool, Optional[Message]]:
        """
        Process an incoming message by verifying authentication.
        
        Args:
            message: The message to process.
            
        Returns:
            Tuple of (is_valid, processed_message).
            If is_valid is False and strict_mode is True, processed_message is None.
        """
        if self.use_jwt:
            # Validate the token
            is_valid, _ = self.jwt_middleware.validate_token(message)
            
            if not is_valid and self.jwt_middleware.strict_mode:
                return False, None
                
            return is_valid, message
        else:
            # Verify the signature
            return self.hmac_middleware.verify_incoming_message(message)
    
    def wrap_message_handler(self, handler: Callable[[Message], Optional[Message]]) -> Callable[[Message], Optional[Message]]:
        """
        Wrap a message handler to automatically handle authentication.
        
        Args:
            handler: The original message handler function.
            
        Returns:
            A wrapped handler function.
        """
        if self.use_jwt:
            # Wrap with JWT middleware
            # Adapt the handler to work with the JWT middleware
            def jwt_handler(message: Message, claims: Optional[Dict[str, Any]]) -> Optional[Message]:
                return handler(message)
                
            return self.jwt_middleware.wrap_message_handler(jwt_handler)
        else:
            # Wrap with HMAC middleware
            return self.hmac_middleware.wrap_message_handler(handler)
