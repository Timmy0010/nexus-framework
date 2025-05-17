"""
Validation rules for the Verification Agent.

This module defines the validation rules used by the VerificationAgent
to check messages for security and validity.
"""

import json
import re
import logging
from typing import Dict, Any, Optional, Tuple, List

# Import base class and Message class
from .verification_agent import ValidationRule
from ..core.message import Message

# Import the schema validator
from ..validation.schema_validator import SchemaValidator as CoreSchemaValidator
from ..core.schemas import BASE_MESSAGE_SCHEMA_V1, PAYLOAD_SCHEMA_REGISTRY

logger = logging.getLogger(__name__)

class SchemaValidator(ValidationRule):
    """
    Validates messages against JSON schemas.
    """
    
    def __init__(self, name: str = "SchemaValidator", 
                 description: str = "Validates messages against JSON schemas",
                 schema_validator: Optional[CoreSchemaValidator] = None):
        """
        Initialize schema validator.
        
        Args:
            name: The name of the validator
            description: Description of the validator
            schema_validator: Optional schema validator instance to use
        """
        super().__init__(name, description)
        self.schema_validator = schema_validator or CoreSchemaValidator(
            base_schema=BASE_MESSAGE_SCHEMA_V1,
            payload_schema_registry=PAYLOAD_SCHEMA_REGISTRY
        )
    
    def validate(self, message: Message) -> Tuple[bool, Optional[str]]:
        """
        Validate a message against its schema.
        
        Args:
            message: The message to validate
            
        Returns:
            A tuple of (is_valid, error_message)
        """
        # Convert Message to dict for schema validation
        message_dict = message.to_dict()
        
        try:
            # Use the schema validator
            is_valid, errors = self.schema_validator.validate_message(message_dict)
            
            if not is_valid:
                return False, "; ".join(errors)
                
            return True, None
        except Exception as e:
            return False, f"Schema validation error: {str(e)}"

class SizeValidator(ValidationRule):
    """
    Validates messages against size constraints.
    """
    
    def __init__(self, name: str = "SizeValidator", 
                 description: str = "Validates message size constraints",
                 max_message_size: int = 1048576,  # 1MB
                 max_content_size: int = 524288,   # 512KB
                 max_metadata_size: int = 16384):  # 16KB
        """
        Initialize size validator.
        
        Args:
            name: The name of the validator
            description: Description of the validator
            max_message_size: Maximum total message size in bytes
            max_content_size: Maximum content size in bytes
            max_metadata_size: Maximum metadata size in bytes
        """
        super().__init__(name, description)
        self.max_message_size = max_message_size
        self.max_content_size = max_content_size
        self.max_metadata_size = max_metadata_size
    
    def validate(self, message: Message) -> Tuple[bool, Optional[str]]:
        """
        Validate a message against size constraints.
        
        Args:
            message: The message to validate
            
        Returns:
            A tuple of (is_valid, error_message)
        """
        # Check content size
        content_size = len(json.dumps(message.content))
        if content_size > self.max_content_size:
            return False, f"Content size ({content_size} bytes) exceeds maximum ({self.max_content_size} bytes)"
        
        # Check metadata size if present
        if message.metadata:
            metadata_size = len(json.dumps(message.metadata))
            if metadata_size > self.max_metadata_size:
                return False, f"Metadata size ({metadata_size} bytes) exceeds maximum ({self.max_metadata_size} bytes)"
        
        # Check total message size
        message_size = len(json.dumps(message.to_dict()))
        if message_size > self.max_message_size:
            return False, f"Total message size ({message_size} bytes) exceeds maximum ({self.max_message_size} bytes)"
        
        return True, None

class ContentValidator(ValidationRule):
    """
    Validates message content against patterns and rules.
    """
    
    def __init__(self, name: str = "ContentValidator", 
                 description: str = "Validates message content against patterns",
                 forbidden_patterns: Optional[List[str]] = None,
                 allowed_domains: Optional[List[str]] = None,
                 max_url_count: int = 10):
        """
        Initialize content validator.
        
        Args:
            name: The name of the validator
            description: Description of the validator
            forbidden_patterns: List of regex patterns that are forbidden
            allowed_domains: List of allowed domains in URLs
            max_url_count: Maximum number of URLs allowed in a message
        """
        super().__init__(name, description)
        self.forbidden_patterns = forbidden_patterns or []
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.forbidden_patterns]
        
        self.allowed_domains = allowed_domains
        self.max_url_count = max_url_count
        
        # URL pattern for detecting URLs in text
        self.url_pattern = re.compile(r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+')
    
    def validate(self, message: Message) -> Tuple[bool, Optional[str]]:
        """
        Validate message content against patterns and rules.
        
        Args:
            message: The message to validate
            
        Returns:
            A tuple of (is_valid, error_message)
        """
        # Check for forbidden patterns in content
        content_str = json.dumps(message.content)
        
        for i, pattern in enumerate(self.compiled_patterns):
            if pattern.search(content_str):
                return False, f"Content contains forbidden pattern {i+1}"
        
        # Check URL count and domains
        urls = self.url_pattern.findall(content_str)
        
        if len(urls) > self.max_url_count:
            return False, f"Message contains too many URLs ({len(urls)} > {self.max_url_count})"
        
        if self.allowed_domains and urls:
            for url in urls:
                domain = url.split('://')[1].split('/')[0]
                if not any(domain.endswith(allowed_domain) for allowed_domain in self.allowed_domains):
                    return False, f"URL contains disallowed domain: {domain}"
        
        return True, None

class PermissionValidator(ValidationRule):
    """
    Validates sender permissions for accessing specific resources or recipients.
    """
    
    def __init__(self, name: str = "PermissionValidator", 
                 description: str = "Validates sender permissions",
                 acl: Optional[Dict[str, Dict[str, bool]]] = None):
        """
        Initialize permission validator.
        
        Args:
            name: The name of the validator
            description: Description of the validator
            acl: Access control list mapping sender_id to {recipient_id: bool}
        """
        super().__init__(name, description)
        self.acl = acl or {}
    
    def validate(self, message: Message) -> Tuple[bool, Optional[str]]:
        """
        Validate sender permissions.
        
        Args:
            message: The message to validate
            
        Returns:
            A tuple of (is_valid, error_message)
        """
        sender_id = message.sender_id
        recipient_id = message.recipient_id
        
        # Check if sender is in ACL
        if sender_id not in self.acl:
            # Default to allowing same-agent communication
            return sender_id == recipient_id, f"Sender {sender_id} not in ACL"
        
        # Check if sender has permission to send to recipient
        sender_acl = self.acl[sender_id]
        
        if recipient_id not in sender_acl:
            # Check for wildcard permission
            if "*" in sender_acl and sender_acl["*"]:
                return True, None
                
            return False, f"Sender {sender_id} has no permission for recipient {recipient_id}"
        
        # Return whether sender has permission for this specific recipient
        has_permission = sender_acl[recipient_id]
        
        if not has_permission:
            return False, f"Sender {sender_id} explicitly denied for recipient {recipient_id}"
            
        return True, None

class RateLimitValidator(ValidationRule):
    """
    Validates messages against rate limits for senders.
    """
    
    def __init__(self, name: str = "RateLimitValidator", 
                 description: str = "Validates against rate limits",
                 default_rate_limit: int = 100,
                 rate_limits: Optional[Dict[str, int]] = None,
                 window_seconds: int = 60):
        """
        Initialize rate limit validator.
        
        Args:
            name: The name of the validator
            description: Description of the validator
            default_rate_limit: Default messages per window
            rate_limits: Dict mapping sender_id to message limit
            window_seconds: Time window in seconds
        """
        super().__init__(name, description)
        self.default_rate_limit = default_rate_limit
        self.rate_limits = rate_limits or {}
        self.window_seconds = window_seconds
        
        # Store message counts per sender
        self.message_counts: Dict[str, List[float]] = {}
    
    def validate(self, message: Message) -> Tuple[bool, Optional[str]]:
        """
        Validate message against rate limits.
        
        Args:
            message: The message to validate
            
        Returns:
            A tuple of (is_valid, error_message)
        """
        sender_id = message.sender_id
        current_time = message.timestamp or 0
        
        # Initialize message counts for sender if not present
        if sender_id not in self.message_counts:
            self.message_counts[sender_id] = []
        
        # Remove old messages outside the window
        window_start = current_time - self.window_seconds
        self.message_counts[sender_id] = [
            t for t in self.message_counts[sender_id] if t >= window_start
        ]
        
        # Get rate limit for sender
        rate_limit = self.rate_limits.get(sender_id, self.default_rate_limit)
        
        # Check if sender is over rate limit
        if len(self.message_counts[sender_id]) >= rate_limit:
            return False, f"Rate limit exceeded for {sender_id}: {rate_limit} messages per {self.window_seconds}s"
        
        # Add current message to counts
        self.message_counts[sender_id].append(current_time)
        
        return True, None
