# nexus_framework/agents/verification/rules/size_rule.py
from typing import Dict, Any
import logging
import json

from nexus_framework.core.message import Message
from nexus_framework.agents.verification.verification_agent import VerificationRule

logger = logging.getLogger(__name__)

class SizeVerificationRule(VerificationRule):
    """
    Verification rule that checks message size to prevent DoS attacks.
    """
    
    def __init__(self, max_size_bytes: int = 1048576):  # Default to 1MB
        """
        Initialize the size verification rule.
        
        Args:
            max_size_bytes: Maximum allowed message size in bytes
        """
        self.max_size_bytes = max_size_bytes
    
    def verify(self, message: Message) -> Dict[str, Any]:
        """
        Verify a message's size is within allowed limits.
        
        Args:
            message: The message to verify
            
        Returns:
            Dict with verification results
        """
        try:
            # Convert message to JSON string to estimate size
            message_dict = message.to_dict()
            
            # Calculate size
            message_json = json.dumps(message_dict)
            size_bytes = len(message_json.encode('utf-8'))
            
            if size_bytes <= self.max_size_bytes:
                return {
                    "passed": True,
                    "reason": f"Message size ({size_bytes} bytes) is within limits",
                    "risk_level": "none",
                    "size_bytes": size_bytes
                }
            else:
                # Determine risk level based on how much the size exceeds the limit
                if size_bytes <= 2 * self.max_size_bytes:
                    risk_level = "low"
                elif size_bytes <= 5 * self.max_size_bytes:
                    risk_level = "medium"
                elif size_bytes <= 10 * self.max_size_bytes:
                    risk_level = "high"
                else:
                    risk_level = "critical"
                
                return {
                    "passed": False,
                    "reason": f"Message size ({size_bytes} bytes) exceeds maximum allowed size ({self.max_size_bytes} bytes)",
                    "risk_level": risk_level,
                    "size_bytes": size_bytes,
                    "max_size_bytes": self.max_size_bytes
                }
        
        except Exception as e:
            logger.error(f"Error during size verification: {str(e)}")
            return {
                "passed": False,
                "reason": f"Size verification error: {str(e)}",
                "risk_level": "medium"
            }
    
    def set_max_size(self, max_size_bytes: int) -> None:
        """
        Update the maximum allowed message size.
        
        Args:
            max_size_bytes: New maximum size in bytes
        """
        if max_size_bytes <= 0:
            raise ValueError("Maximum size must be positive")
        
        self.max_size_bytes = max_size_bytes
        logger.info(f"Updated maximum message size to {max_size_bytes} bytes")
