# nexus_framework/agents/verification/rules/schema_rule.py
from typing import Dict, Any
import logging

from nexus_framework.core.message import Message
from nexus_framework.agents.verification.verification_agent import VerificationRule
from nexus_framework.validation.schema_registry import SchemaRegistry
from nexus_framework.validation.schema_validator import SchemaValidator

logger = logging.getLogger(__name__)

class SchemaVerificationRule(VerificationRule):
    """
    Verification rule that validates messages against their JSON schemas.
    """
    
    def __init__(self):
        """Initialize the schema verification rule."""
        # Create schema registry and validator
        self.schema_registry = SchemaRegistry()
        self.validator = SchemaValidator(
            self.schema_registry.get_base_schema("1.0"),
            self.schema_registry.get_all_payload_schemas()
        )
    
    def verify(self, message: Message) -> Dict[str, Any]:
        """
        Verify a message against its schema.
        
        Args:
            message: The message to verify
            
        Returns:
            Dict with verification results
        """
        try:
            # Convert message to dict for validation
            message_dict = message.to_dict()
            
            # Validate against schema
            valid, errors = self.validator.validate_message(message_dict)
            
            if valid:
                return {
                    "passed": True,
                    "reason": "Message schema validation passed",
                    "risk_level": "none"
                }
            else:
                # Determine risk level based on errors
                risk_level = "medium"  # Default risk level for schema errors
                
                # Check for critical schema issues (missing required fields, etc.)
                critical_keywords = ["required", "type", "format"]
                for error in errors:
                    if any(keyword in error for keyword in critical_keywords):
                        risk_level = "high"
                        break
                
                return {
                    "passed": False,
                    "reason": f"Message schema validation failed: {'; '.join(errors)}",
                    "risk_level": risk_level,
                    "errors": errors
                }
        
        except Exception as e:
            logger.error(f"Error during schema validation: {str(e)}")
            return {
                "passed": False,
                "reason": f"Schema validation error: {str(e)}",
                "risk_level": "high"
            }
