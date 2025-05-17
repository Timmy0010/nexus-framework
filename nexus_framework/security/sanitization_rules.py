"""
Sanitization rules for the Verification Agent.

This module defines the sanitization rules used by the VerificationAgent
to sanitize messages for security.
"""

import json
import re
import logging
import html
from typing import Dict, Any, List, Set, Optional

# Import base class and Message class
from .verification_agent import SanitizationRule
from ..core.message import Message

logger = logging.getLogger(__name__)

class SizeLimitSanitizer(SanitizationRule):
    """
    Sanitizes messages by applying size limits.
    """
    
    def __init__(self, name: str = "SizeLimitSanitizer", 
                 description: str = "Limits message sizes",
                 max_content_length: int = 10000,
                 max_field_lengths: Optional[Dict[str, int]] = None):
        """
        Initialize size limit sanitizer.
        
        Args:
            name: The name of the sanitizer
            description: Description of the sanitizer
            max_content_length: Maximum content string length
            max_field_lengths: Dict mapping field paths to max lengths
        """
        super().__init__(name, description)
        self.max_content_length = max_content_length
        self.max_field_lengths = max_field_lengths or {
            "content.text": 5000,  # Example field path for text messages
            "content.subject": 200,
            "metadata.description": 1000
        }
    
    def sanitize(self, message: Message) -> Message:
        """
        Sanitize a message by applying size limits.
        
        Args:
            message: The message to sanitize
            
        Returns:
            The sanitized message
        """
        # Create a copy to avoid modifying the original
        sanitized_message = message.copy()
        
        # Limit overall content size for string content
        if isinstance(sanitized_message.content, str) and len(sanitized_message.content) > self.max_content_length:
            sanitized_message.content = sanitized_message.content[:self.max_content_length] + "..."
            logger.info(f"Truncated message content for {message.message_id}")
        
        # Apply field-specific limits
        message_dict = sanitized_message.to_dict()
        
        for field_path, max_length in self.max_field_lengths.items():
            value = self._get_value_by_path(message_dict, field_path)
            
            if isinstance(value, str) and len(value) > max_length:
                # Truncate the field
                self._set_value_by_path(
                    message_dict, 
                    field_path, 
                    value[:max_length] + "..."
                )
                logger.info(f"Truncated field {field_path} for {message.message_id}")
        
        # Convert back to Message
        return Message.from_dict(message_dict)
    
    def _get_value_by_path(self, obj: Dict[str, Any], path: str) -> Any:
        """
        Get a value from a nested dictionary by dot-separated path.
        
        Args:
            obj: The dictionary to search
            path: Dot-separated path to the value
            
        Returns:
            The value at the path, or None if not found
        """
        parts = path.split('.')
        current = obj
        
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
                
        return current
    
    def _set_value_by_path(self, obj: Dict[str, Any], path: str, value: Any) -> None:
        """
        Set a value in a nested dictionary by dot-separated path.
        
        Args:
            obj: The dictionary to modify
            path: Dot-separated path to the value
            value: The value to set
        """
        parts = path.split('.')
        current = obj
        
        # Navigate to the parent object
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        
        # Set the value
        current[parts[-1]] = value

class ContentFilterSanitizer(SanitizationRule):
    """
    Sanitizes message content by filtering out inappropriate content.
    """
    
    def __init__(self, name: str = "ContentFilterSanitizer", 
                 description: str = "Filters message content",
                 filtered_terms: Optional[List[str]] = None,
                 replacement: str = "[FILTERED]",
                 filter_urls: bool = False,
                 allowed_domains: Optional[List[str]] = None):
        """
        Initialize content filter sanitizer.
        
        Args:
            name: The name of the sanitizer
            description: Description of the sanitizer
            filtered_terms: List of terms to filter out
            replacement: Replacement for filtered terms
            filter_urls: Whether to filter out URLs
            allowed_domains: List of allowed domains (if filter_urls is True)
        """
        super().__init__(name, description)
        self.filtered_terms = filtered_terms or []
        self.replacement = replacement
        self.filter_urls = filter_urls
        self.allowed_domains = allowed_domains or []
        
        # Compile regex patterns for terms to filter
        self.patterns = [
            re.compile(rf'\b{re.escape(term)}\b', re.IGNORECASE) 
            for term in self.filtered_terms
        ]
        
        # URL pattern for detecting URLs in text
        self.url_pattern = re.compile(r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+')
    
    def sanitize(self, message: Message) -> Message:
        """
        Sanitize message content by filtering inappropriate content.
        
        Args:
            message: The message to sanitize
            
        Returns:
            The sanitized message
        """
        # Create a copy to avoid modifying the original
        sanitized_message = message.copy()
        
        # Check if content is a string
        if isinstance(sanitized_message.content, str):
            content = sanitized_message.content
            
            # Apply term filters
            for pattern in self.patterns:
                content = pattern.sub(self.replacement, content)
            
            # Filter URLs if enabled
            if self.filter_urls:
                content = self._filter_urls(content)
            
            sanitized_message.content = content
        elif isinstance(sanitized_message.content, dict):
            # For dictionary content, recursively process string values
            sanitized_content = self._filter_dict(sanitized_message.content)
            sanitized_message.content = sanitized_content
        
        return sanitized_message
    
    def _filter_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recursively filter string values in a dictionary.
        
        Args:
            data: The dictionary to filter
            
        Returns:
            Filtered dictionary
        """
        result = {}
        
        for key, value in data.items():
            if isinstance(value, str):
                filtered_value = value
                
                # Apply term filters
                for pattern in self.patterns:
                    filtered_value = pattern.sub(self.replacement, filtered_value)
                
                # Filter URLs if enabled
                if self.filter_urls:
                    filtered_value = self._filter_urls(filtered_value)
                
                result[key] = filtered_value
            elif isinstance(value, dict):
                result[key] = self._filter_dict(value)
            elif isinstance(value, list):
                result[key] = self._filter_list(value)
            else:
                result[key] = value
                
        return result
    
    def _filter_list(self, data: List[Any]) -> List[Any]:
        """
        Recursively filter string values in a list.
        
        Args:
            data: The list to filter
            
        Returns:
            Filtered list
        """
        result = []
        
        for item in data:
            if isinstance(item, str):
                filtered_item = item
                
                # Apply term filters
                for pattern in self.patterns:
                    filtered_item = pattern.sub(self.replacement, filtered_item)
                
                # Filter URLs if enabled
                if self.filter_urls:
                    filtered_item = self._filter_urls(filtered_item)
                
                result.append(filtered_item)
            elif isinstance(item, dict):
                result.append(self._filter_dict(item))
            elif isinstance(item, list):
                result.append(self._filter_list(item))
            else:
                result.append(item)
                
        return result
    
    def _filter_urls(self, text: str) -> str:
        """
        Filter URLs in text, keeping only allowed domains.
        
        Args:
            text: The text to filter
            
        Returns:
            Filtered text
        """
        def process_url(match):
            url = match.group(0)
            domain = url.split('://')[1].split('/')[0]
            
            if any(domain.endswith(allowed_domain) for allowed_domain in self.allowed_domains):
                return url
                
            return self.replacement
        
        return self.url_pattern.sub(process_url, text)

class JsonSanitizer(SanitizationRule):
    """
    Sanitizes JSON content for security.
    """
    
    def __init__(self, name: str = "JsonSanitizer", 
                 description: str = "Sanitizes JSON content",
                 allowed_keys: Optional[Set[str]] = None,
                 disallowed_keys: Optional[Set[str]] = None,
                 max_depth: int = 10,
                 escape_html: bool = True):
        """
        Initialize JSON sanitizer.
        
        Args:
            name: The name of the sanitizer
            description: Description of the sanitizer
            allowed_keys: Set of allowed keys (if None, all keys allowed)
            disallowed_keys: Set of disallowed keys (if None, no keys disallowed)
            max_depth: Maximum nesting depth for JSON objects
            escape_html: Whether to escape HTML in string values
        """
        super().__init__(name, description)
        self.allowed_keys = allowed_keys
        self.disallowed_keys = disallowed_keys or set()
        self.max_depth = max_depth
        self.escape_html = escape_html
    
    def sanitize(self, message: Message) -> Message:
        """
        Sanitize JSON content in the message.
        
        Args:
            message: The message to sanitize
            
        Returns:
            The sanitized message
        """
        # Create a copy to avoid modifying the original
        sanitized_message = message.copy()
        
        # Only process if content is a dict
        if isinstance(sanitized_message.content, dict):
            sanitized_content = self._sanitize_json(
                sanitized_message.content, 
                depth=0
            )
            sanitized_message.content = sanitized_content
        
        return sanitized_message
    
    def _sanitize_json(self, data: Dict[str, Any], depth: int) -> Dict[str, Any]:
        """
        Recursively sanitize a JSON object.
        
        Args:
            data: The JSON object to sanitize
            depth: Current nesting depth
            
        Returns:
            Sanitized JSON object
        """
        # Limit recursion depth
        if depth > self.max_depth:
            return {}
            
        result = {}
        
        for key, value in data.items():
            # Skip disallowed keys
            if key in self.disallowed_keys:
                logger.info(f"Removed disallowed key: {key}")
                continue
                
            # Skip keys not in allowed_keys (if specified)
            if self.allowed_keys is not None and key not in self.allowed_keys:
                logger.info(f"Removed non-allowed key: {key}")
                continue
                
            # Process values based on type
            if isinstance(value, dict):
                result[key] = self._sanitize_json(value, depth + 1)
            elif isinstance(value, list):
                result[key] = self._sanitize_list(value, depth + 1)
            elif isinstance(value, str):
                result[key] = self._sanitize_string(value)
            else:
                # Preserve other types (numbers, booleans, null)
                result[key] = value
                
        return result
    
    def _sanitize_list(self, data: List[Any], depth: int) -> List[Any]:
        """
        Recursively sanitize a JSON array.
        
        Args:
            data: The JSON array to sanitize
            depth: Current nesting depth
            
        Returns:
            Sanitized JSON array
        """
        # Limit recursion depth
        if depth > self.max_depth:
            return []
            
        result = []
        
        for item in data:
            if isinstance(item, dict):
                result.append(self._sanitize_json(item, depth + 1))
            elif isinstance(item, list):
                result.append(self._sanitize_list(item, depth + 1))
            elif isinstance(item, str):
                result.append(self._sanitize_string(item))
            else:
                # Preserve other types (numbers, booleans, null)
                result.append(item)
                
        return result
    
    def _sanitize_string(self, value: str) -> str:
        """
        Sanitize a string value.
        
        Args:
            value: The string to sanitize
            
        Returns:
            Sanitized string
        """
        # Escape HTML if enabled
        if self.escape_html:
            return html.escape(value)
            
        return value

class RecursiveDepthSanitizer(SanitizationRule):
    """
    Limits the nesting depth of recursive structures to prevent DoS attacks.
    """
    
    def __init__(self, name: str = "RecursiveDepthSanitizer", 
                 description: str = "Limits nesting depth",
                 max_depth: int = 5):
        """
        Initialize recursive depth sanitizer.
        
        Args:
            name: The name of the sanitizer
            description: Description of the sanitizer
            max_depth: Maximum allowed nesting depth
        """
        super().__init__(name, description)
        self.max_depth = max_depth
    
    def sanitize(self, message: Message) -> Message:
        """
        Sanitize a message by limiting nesting depth.
        
        Args:
            message: The message to sanitize
            
        Returns:
            The sanitized message
        """
        # Create a copy to avoid modifying the original
        sanitized_message = message.copy()
        
        # Only process if content is a complex structure
        if isinstance(sanitized_message.content, (dict, list)):
            sanitized_content = self._limit_depth(
                sanitized_message.content, 
                depth=0
            )
            sanitized_message.content = sanitized_content
        
        return sanitized_message
    
    def _limit_depth(self, data: Any, depth: int) -> Any:
        """
        Recursively limit the nesting depth of data.
        
        Args:
            data: The data to process
            depth: Current nesting depth
            
        Returns:
            Processed data with limited depth
        """
        # Return placeholder if max depth exceeded
        if depth >= self.max_depth:
            if isinstance(data, dict):
                return {"__max_depth_exceeded__": True}
            elif isinstance(data, list):
                return ["__max_depth_exceeded__"]
            return data
            
        # Process based on type
        if isinstance(data, dict):
            result = {}
            for key, value in data.items():
                result[key] = self._limit_depth(value, depth + 1)
            return result
        elif isinstance(data, list):
            return [self._limit_depth(item, depth + 1) for item in data]
        
        # Return primitive values as is
        return data
