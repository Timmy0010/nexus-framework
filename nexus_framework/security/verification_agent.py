"""
VerificationAgent implementation for the Nexus Framework.

This module implements a security-focused agent that validates and sanitizes
messages before they are processed by other agents in the system.
"""

import logging
import uuid
from typing import Dict, Any, Optional, List, Callable, Type, Tuple
from abc import ABC, abstractmethod

# Assuming BaseAgent is defined in the agents module
from ..agents.base_agent import BaseAgent
from ..core.message import Message

logger = logging.getLogger(__name__)

class ValidationRule(ABC):
    """
    Abstract base class for validation rules.
    
    Validation rules check if a message meets certain criteria and return
    a tuple of (is_valid, error_message).
    """
    
    def __init__(self, name: str, description: str = ""):
        """
        Initialize a validation rule.
        
        Args:
            name: The name of the rule
            description: A description of what the rule checks
        """
        self.name = name
        self.description = description
    
    @abstractmethod
    def validate(self, message: Message) -> Tuple[bool, Optional[str]]:
        """
        Validate a message against this rule.
        
        Args:
            message: The message to validate
            
        Returns:
            A tuple of (is_valid, error_message)
            is_valid: True if the message is valid, False otherwise
            error_message: A description of the error if the message is invalid, None otherwise
        """
        pass

class SanitizationRule(ABC):
    """
    Abstract base class for sanitization rules.
    
    Sanitization rules modify messages to make them safe for processing.
    """
    
    def __init__(self, name: str, description: str = ""):
        """
        Initialize a sanitization rule.
        
        Args:
            name: The name of the rule
            description: A description of what the rule does
        """
        self.name = name
        self.description = description
    
    @abstractmethod
    def sanitize(self, message: Message) -> Message:
        """
        Sanitize a message according to this rule.
        
        Args:
            message: The message to sanitize
            
        Returns:
            The sanitized message
        """
        pass

class ValidationResult:
    """
    Class representing the result of message validation.
    """
    
    def __init__(self, is_valid: bool, errors: Optional[List[str]] = None):
        """
        Initialize a validation result.
        
        Args:
            is_valid: Whether the message is valid
            errors: List of error messages if the message is invalid
        """
        self.is_valid = is_valid
        self.errors = errors or []

class VerificationAgent(BaseAgent):
    """
    Agent responsible for verifying and sanitizing messages.
    
    The VerificationAgent acts as a gatekeeper, validating and sanitizing
    messages before they are processed by other agents in the system.
    """
    
    def __init__(self, agent_name: str = "VerificationAgent"):
        """
        Initialize the verification agent.
        
        Args:
            agent_name: Name of the agent
        """
        super().__init__(agent_name=agent_name, role="security")
        self.validators: List[ValidationRule] = []
        self.sanitizers: List[SanitizationRule] = []
        
    def register_validator(self, validator: ValidationRule) -> None:
        """
        Register a validation rule.
        
        Args:
            validator: The validation rule to register
        """
        self.validators.append(validator)
        logger.info(f"Registered validator: {validator.name}")
        
    def register_sanitizer(self, sanitizer: SanitizationRule) -> None:
        """
        Register a sanitization rule.
        
        Args:
            sanitizer: The sanitization rule to register
        """
        self.sanitizers.append(sanitizer)
        logger.info(f"Registered sanitizer: {sanitizer.name}")
        
    def load_validators_from_config(self, config: Dict[str, Any]) -> None:
        """
        Load validators from a configuration dictionary.
        
        Args:
            config: Configuration dictionary containing validator definitions
        """
        validators_config = config.get("validators", [])
        
        for validator_config in validators_config:
            validator_type = validator_config.get("type")
            validator_params = validator_config.get("params", {})
            
            try:
                # Dynamically create validator instance
                validator_class = self._get_validator_class(validator_type)
                validator = validator_class(**validator_params)
                self.register_validator(validator)
            except Exception as e:
                logger.error(f"Failed to load validator {validator_type}: {e}")
                
    def load_sanitizers_from_config(self, config: Dict[str, Any]) -> None:
        """
        Load sanitizers from a configuration dictionary.
        
        Args:
            config: Configuration dictionary containing sanitizer definitions
        """
        sanitizers_config = config.get("sanitizers", [])
        
        for sanitizer_config in sanitizers_config:
            sanitizer_type = sanitizer_config.get("type")
            sanitizer_params = sanitizer_config.get("params", {})
            
            try:
                # Dynamically create sanitizer instance
                sanitizer_class = self._get_sanitizer_class(sanitizer_type)
                sanitizer = sanitizer_class(**sanitizer_params)
                self.register_sanitizer(sanitizer)
            except Exception as e:
                logger.error(f"Failed to load sanitizer {sanitizer_type}: {e}")
    
    def _get_validator_class(self, validator_type: str) -> Type[ValidationRule]:
        """
        Get a validator class by type.
        
        Args:
            validator_type: The type of validator to get
            
        Returns:
            The validator class
            
        Raises:
            ValueError: If the validator type is not recognized
        """
        # This would be replaced with a proper plugin registry
        from .validation_rules import (
            SchemaValidator, 
            SizeValidator, 
            ContentValidator
        )
        
        validators = {
            "schema": SchemaValidator,
            "size": SizeValidator,
            "content": ContentValidator,
        }
        
        if validator_type not in validators:
            raise ValueError(f"Unknown validator type: {validator_type}")
            
        return validators[validator_type]
    
    def _get_sanitizer_class(self, sanitizer_type: str) -> Type[SanitizationRule]:
        """
        Get a sanitizer class by type.
        
        Args:
            sanitizer_type: The type of sanitizer to get
            
        Returns:
            The sanitizer class
            
        Raises:
            ValueError: If the sanitizer type is not recognized
        """
        # This would be replaced with a proper plugin registry
        from .sanitization_rules import (
            SizeLimitSanitizer,
            ContentFilterSanitizer,
            JsonSanitizer
        )
        
        sanitizers = {
            "size_limit": SizeLimitSanitizer,
            "content_filter": ContentFilterSanitizer,
            "json": JsonSanitizer,
        }
        
        if sanitizer_type not in sanitizers:
            raise ValueError(f"Unknown sanitizer type: {sanitizer_type}")
            
        return sanitizers[sanitizer_type]
    
    def _validate(self, message: Message) -> ValidationResult:
        """
        Validate a message against all registered validators.
        
        Args:
            message: The message to validate
            
        Returns:
            A ValidationResult object
        """
        errors = []
        
        for validator in self.validators:
            is_valid, error = validator.validate(message)
            if not is_valid and error:
                errors.append(f"{validator.name}: {error}")
                
        return ValidationResult(len(errors) == 0, errors)
    
    def _sanitize(self, message: Message) -> Message:
        """
        Sanitize a message using all registered sanitizers.
        
        Args:
            message: The message to sanitize
            
        Returns:
            The sanitized message
        """
        sanitized_message = message
        
        for sanitizer in self.sanitizers:
            try:
                sanitized_message = sanitizer.sanitize(sanitized_message)
            except Exception as e:
                logger.error(f"Error in sanitizer {sanitizer.name}: {e}")
                
        return sanitized_message
    
    def _create_rejection_message(self, message: Message, errors: List[str]) -> Message:
        """
        Create a message indicating rejection of the original message.
        
        Args:
            message: The original message that was rejected
            errors: List of validation errors
            
        Returns:
            A new message indicating rejection
        """
        return Message(
            message_id=str(uuid.uuid4()),
            sender_id=self.agent_id,
            recipient_id=message.sender_id,
            content=f"Message validation failed: {'; '.join(errors)}",
            metadata={
                "is_rejection": True,
                "original_message_id": message.message_id,
                "validation_errors": errors
            }
        )
    
    def process_message(self, message: Message) -> Optional[Message]:
        """
        Process a message by validating and sanitizing it.
        
        This is the main entry point for message processing in the VerificationAgent.
        
        Args:
            message: The message to process
            
        Returns:
            The processed message, a rejection message, or None
        """
        logger.debug(f"Processing message {message.message_id} from {message.sender_id}")
        
        # Validate the message
        validation_result = self._validate(message)
        if not validation_result.is_valid:
            logger.warning(f"Message {message.message_id} failed validation: {validation_result.errors}")
            return self._create_rejection_message(message, validation_result.errors)
        
        # Sanitize the message if it's valid
        sanitized_message = self._sanitize(message)
        
        # Forward to intended recipient
        return sanitized_message
