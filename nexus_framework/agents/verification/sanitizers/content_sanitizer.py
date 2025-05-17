# nexus_framework/agents/verification/sanitizers/content_sanitizer.py
import re
import html
from typing import Dict, Any, Union, List
import logging

from nexus_framework.core.message import Message
from nexus_framework.agents.verification.verification_agent import MessageSanitizer

logger = logging.getLogger(__name__)

class ContentSanitizer(MessageSanitizer):
    """
    Sanitizer for potentially malicious content in messages.
    """
    
    def __init__(self):
        """Initialize the content sanitizer."""
        # Define replacement patterns
        self.replacements = {
            # Command injection
            r";\s*rm\s+": "; [REMOVED]",
            r";\s*del\s+": "; [REMOVED]",
            r";\s*whoami": "; [REMOVED]",
            r";\s*chmod\s+": "; [REMOVED]",
            r";\s*sudo\s+": "; [REMOVED]",
            r"&&\s*[a-z]+\s*": " [REMOVED]",
            r"\|\s*[a-z]+\s*": " [REMOVED]",
            r"`[^`]+`": "[REMOVED]",
            r"\$\([^)]+\)": "[REMOVED]",
            
            # SQL injection
            r"'\s*OR\s+'1'='1": "'[REMOVED]'",
            r";\s*DROP\s+TABLE": "; [REMOVED]",
            r";\s*DELETE\s+FROM": "; [REMOVED]",
            r"UNION\s+SELECT": "[REMOVED]",
            r"--\s*": "[REMOVED]",
            r"/\*.*\*/": "[REMOVED]",
            
            # XSS
            r"<script[^>]*>.*?</script>": "[REMOVED]",
            r"javascript:": "[REMOVED]",
            r"onerror=": "[REMOVED]",
            r"onload=": "[REMOVED]",
            r"eval\(": "[REMOVED]",
            r"document\.cookie": "[REMOVED]",
            
            # Path traversal
            r"\.\./": "./",
            r"%2e%2e%2f": "./",
            r"\.\.\\": "./",
            r"%2e%2e%5c": "./"
        }
        
        # Compile regex patterns for efficiency
        self.compiled_patterns = {
            pattern: re.compile(pattern, re.IGNORECASE) 
            for pattern in self.replacements
        }
    
    def _sanitize_string(self, content: str) -> str:
        """
        Sanitize a string by replacing potentially malicious patterns.
        
        Args:
            content: The string to sanitize
            
        Returns:
            Sanitized string
        """
        # First apply regex replacements
        result = content
        for pattern, replacement in self.replacements.items():
            result = self.compiled_patterns[pattern].sub(replacement, result)
        
        # Then HTML-escape the content to handle any remaining HTML/script tags
        result = html.escape(result)
        
        return result
    
    def _sanitize_dict_recursively(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recursively sanitize a dictionary.
        
        Args:
            data: The dictionary to sanitize
            
        Returns:
            Sanitized dictionary
        """
        sanitized_data = {}
        
        for key, value in data.items():
            # Sanitize the key if it's a string
            sanitized_key = key
            if isinstance(key, str):
                sanitized_key = self._sanitize_string(key)
            
            # Sanitize the value based on its type
            if isinstance(value, str):
                sanitized_data[sanitized_key] = self._sanitize_string(value)
            elif isinstance(value, dict):
                # Recursive sanitization for nested dictionaries
                sanitized_data[sanitized_key] = self._sanitize_dict_recursively(value)
            elif isinstance(value, list):
                # Sanitize each item in the list
                sanitized_data[sanitized_key] = [
                    self._sanitize_dict_recursively(item) if isinstance(item, dict)
                    else self._sanitize_string(item) if isinstance(item, str)
                    else item
                    for item in value
                ]
            else:
                # Keep non-string, non-dict, non-list values unchanged
                sanitized_data[sanitized_key] = value
        
        return sanitized_data
    
    def sanitize(self, message: Message) -> Message:
        """
        Sanitize a message by removing potentially malicious content.
        
        Args:
            message: The message to sanitize
            
        Returns:
            Sanitized message
        """
        try:
            # Create a copy of the message for sanitization
            sanitized_message = message.copy()
            
            # Sanitize message content if it's a string
            if hasattr(sanitized_message, 'content') and isinstance(sanitized_message.content, str):
                sanitized_message.content = self._sanitize_string(sanitized_message.content)
            
            # Sanitize message payload if it's a dictionary
            if hasattr(sanitized_message, 'payload') and isinstance(sanitized_message.payload, dict):
                sanitized_message.payload = self._sanitize_dict_recursively(sanitized_message.payload)
            
            # Sanitize message metadata if it exists
            if hasattr(sanitized_message, 'metadata') and isinstance(sanitized_message.metadata, dict):
                sanitized_message.metadata = self._sanitize_dict_recursively(sanitized_message.metadata)
            
            logger.info(f"Successfully sanitized message {message.message_id}")
            return sanitized_message
        
        except Exception as e:
            logger.error(f"Error during content sanitization: {str(e)}")
            # Return the original message if sanitization fails
            return message
