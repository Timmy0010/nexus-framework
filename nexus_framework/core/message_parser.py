"""
Message parsing utilities for the Nexus framework.

This module provides utility functions for parsing and handling different
types of message content based on content_type and role.
"""

import json
import logging
from typing import Any, Dict, Optional, Union, Type, TypeVar, List

from nexus_framework.core.messaging import Message

# Set up logging
logger = logging.getLogger(__name__)

# Generic type for parsed content
T = TypeVar('T')

class MessageParser:
    """
    Utility class for parsing message content based on content_type.
    
    This class provides methods to extract and parse the content of 
    Message objects based on their content_type field.
    """
    
    @staticmethod
    def parse_content(message: Message, expected_type: Optional[Type[T]] = None) -> Any:
        """
        Parse the content of a message based on its content_type.
        
        Args:
            message: The Message object to parse.
            expected_type: Optional type that the parsed content should conform to.
            
        Returns:
            The parsed content, potentially cast to the expected_type if provided.
            
        Raises:
            ValueError: If the content_type is not recognized or the content
                      cannot be parsed as the expected type.
        """
        if message.content_type == "application/json":
            return MessageParser.parse_json_content(message, expected_type)
        elif message.content_type == "text/plain":
            return MessageParser.parse_text_content(message, expected_type)
        else:
            logger.warning(f"Unsupported content_type: {message.content_type}")
            return message.content  # Return as-is
    
    @staticmethod
    def parse_json_content(message: Message, expected_type: Optional[Type[T]] = None) -> Any:
        """
        Parse JSON content from a message.
        
        Args:
            message: The Message object with JSON content.
            expected_type: Optional type to cast the parsed JSON to.
            
        Returns:
            The parsed JSON content, potentially cast to expected_type.
            
        Raises:
            ValueError: If the content is not valid JSON or cannot be cast to expected_type.
        """
        # Handle the case where content is already parsed
        if not isinstance(message.content, str):
            content = message.content
        else:
            try:
                content = json.loads(message.content)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON content: {e}")
                raise ValueError(f"Invalid JSON content: {e}")
        
        # Cast to expected type if provided
        if expected_type:
            try:
                if expected_type is dict:
                    if not isinstance(content, dict):
                        raise ValueError(f"Expected dict, got {type(content).__name__}")
                    return content
                elif expected_type is list:
                    if not isinstance(content, list):
                        raise ValueError(f"Expected list, got {type(content).__name__}")
                    return content
                else:
                    # For other types, try to instantiate with the content
                    return expected_type(content)
            except (TypeError, ValueError) as e:
                logger.error(f"Failed to cast content to {expected_type.__name__}: {e}")
                raise ValueError(f"Cannot cast content to {expected_type.__name__}: {e}")
        
        return content
    
    @staticmethod
    def parse_text_content(message: Message, expected_type: Optional[Type[T]] = None) -> Any:
        """
        Parse text content from a message.
        
        Args:
            message: The Message object with text content.
            expected_type: Optional type to cast the text content to.
            
        Returns:
            The text content, potentially cast to expected_type.
            
        Raises:
            ValueError: If the content cannot be cast to expected_type.
        """
        content = message.content
        
        # Cast to expected type if provided
        if expected_type:
            try:
                if expected_type is str:
                    if not isinstance(content, str):
                        content = str(content)
                    return content
                else:
                    # For other types, try to instantiate with the content
                    return expected_type(content)
            except (TypeError, ValueError) as e:
                logger.error(f"Failed to cast content to {expected_type.__name__}: {e}")
                raise ValueError(f"Cannot cast content to {expected_type.__name__}: {e}")
        
        return content


class MessageHandler:
    """
    Utility class for handling messages based on their role.
    
    This class provides methods for processing messages differently
    depending on their role field, which indicates the context or
    purpose of the message.
    """
    
    @staticmethod
    def handle_by_role(message: Message) -> Dict[str, Any]:
        """
        Process a message based on its role.
        
        Args:
            message: The Message object to process.
            
        Returns:
            A dictionary containing the processed result and metadata.
            
        Raises:
            ValueError: If the role is not recognized or the message content
                      is inappropriate for the specified role.
        """
        # Determine the appropriate processing method based on the role
        if message.role == "user":
            return MessageHandler._handle_user_message(message)
        elif message.role == "assistant":
            return MessageHandler._handle_assistant_message(message)
        elif message.role == "system":
            return MessageHandler._handle_system_message(message)
        elif message.role == "tool_call":
            return MessageHandler._handle_tool_call_message(message)
        elif message.role == "tool_response":
            return MessageHandler._handle_tool_response_message(message)
        else:
            # For roles without specific handling or None
            logger.info(f"No specific handling for role: {message.role}")
            return {
                "content": MessageParser.parse_content(message),
                "role": message.role,
                "metadata": message.metadata or {}
            }
    
    @staticmethod
    def _handle_user_message(message: Message) -> Dict[str, Any]:
        """Process a message with role='user'."""
        # Typically just parse the content based on content_type
        return {
            "content": MessageParser.parse_content(message),
            "role": "user",
            "metadata": message.metadata or {}
        }
    
    @staticmethod
    def _handle_assistant_message(message: Message) -> Dict[str, Any]:
        """Process a message with role='assistant'."""
        # Typically just parse the content based on content_type
        return {
            "content": MessageParser.parse_content(message),
            "role": "assistant",
            "metadata": message.metadata or {}
        }
    
    @staticmethod
    def _handle_system_message(message: Message) -> Dict[str, Any]:
        """Process a message with role='system'."""
        # System messages might contain special directives or configurations
        return {
            "content": MessageParser.parse_content(message),
            "role": "system",
            "metadata": message.metadata or {}
        }
    
    @staticmethod
    def _handle_tool_call_message(message: Message) -> Dict[str, Any]:
        """
        Process a message with role='tool_call'.
        
        Expects message content to be a dictionary (or JSON string) with
        at least 'tool_name' and optionally 'parameters'.
        """
        # Parse to a dictionary if it's a JSON string
        content = MessageParser.parse_content(message, dict)
        
        # Validate the tool call format
        if 'tool_name' not in content:
            logger.error("tool_call message missing required 'tool_name' field")
            raise ValueError("tool_call message must contain 'tool_name'")
        
        # Extract tool name and parameters
        tool_name = content['tool_name']
        parameters = content.get('parameters', {})
        
        return {
            "tool_name": tool_name,
            "parameters": parameters,
            "role": "tool_call",
            "metadata": message.metadata or {}
        }
    
    @staticmethod
    def _handle_tool_response_message(message: Message) -> Dict[str, Any]:
        """
        Process a message with role='tool_response'.
        
        Expects message content to be the result from a tool invocation.
        """
        # Parse the content based on content_type
        content = MessageParser.parse_content(message)
        
        return {
            "result": content,
            "role": "tool_response",
            "metadata": message.metadata or {}
        }
