"""
Security manager for the Nexus framework.

This module provides basic security and access control for agent interactions
and tool access within the Nexus framework.
"""

import logging
from typing import Dict, List, Optional, Any, Set, Tuple
import uuid
from datetime import datetime
import re

from nexus_framework.core.agents import BaseAgent, AgentIdentity
from nexus_framework.core.exceptions import NexusSecurityError, NexusToolError

# Set up logging
logger = logging.getLogger(__name__)


class SecurityManager:
    """
    Manages security and access control for the Nexus framework.
    
    This class is responsible for:
    - Authenticating agents
    - Controlling which agents can communicate with each other
    - Authorizing access to external tools
    - Logging security-relevant events
    """
    
    def __init__(self):
        """Initialize a new security manager."""
        # Maps agent_id -> set of agent_ids it can communicate with
        self._communication_acl: Dict[str, Set[str]] = {}
        
        # Maps agent_id -> set of tool_names it can use
        self._tool_acl: Dict[str, Set[str]] = {}
        
        # Maps agent_id -> AgentIdentity for validated agents
        self._validated_agents: Dict[str, AgentIdentity] = {}
        
        # Security settings
        self.enforce_communication_acl = False  # Default: open communication
        self.enforce_tool_acl = True  # Default: restrict tool access
    
    def validate_agent(self, agent: BaseAgent) -> bool:
        """
        Validate an agent's identity.
        
        Args:
            agent: The agent to validate.
            
        Returns:
            True if the agent's identity is valid, False otherwise.
        """
        # In a real implementation, this would involve more sophisticated
        # checks, possibly including cryptographic verification
        
        try:
            identity = agent.get_identity()
            
            # Basic validation
            if not identity.id or identity.id != agent.agent_id:
                logger.warning(f"Agent ID mismatch: {identity.id} != {agent.agent_id}")
                return False
            
            if not identity.name:
                logger.warning(f"Agent has no name: {agent.agent_id}")
                return False
            
            # Store the validated identity
            self._validated_agents[agent.agent_id] = identity
            
            return True
        except Exception as e:
            logger.error(f"Error validating agent {agent.agent_id}: {e}")
            return False
    
    def allow_communication(self, sender_id: str, recipient_id: str) -> bool:
        """
        Check if communication between two agents is allowed.
        
        Args:
            sender_id: The ID of the sending agent.
            recipient_id: The ID of the receiving agent.
            
        Returns:
            True if communication is allowed, False otherwise.
        """
        # If ACL enforcement is disabled, allow all communication
        if not self.enforce_communication_acl:
            return True
        
        # Check if the sender has an entry in the ACL
        if sender_id not in self._communication_acl:
            logger.warning(f"Agent {sender_id} not in communication ACL")
            return False
        
        # Check if the recipient is in the sender's allowed list
        if recipient_id not in self._communication_acl[sender_id]:
            logger.warning(f"Agent {sender_id} not allowed to communicate with {recipient_id}")
            return False
        
        return True
    
    def allow_tool_access(self, agent_id: str, tool_name: str) -> bool:
        """
        Check if an agent is allowed to use a specific tool.
        
        Args:
            agent_id: The ID of the agent.
            tool_name: The name of the tool.
            
        Returns:
            True if tool access is allowed, False otherwise.
        """
        # If ACL enforcement is disabled, allow all tool access
        if not self.enforce_tool_acl:
            return True
        
        # Check if the agent has an entry in the tool ACL
        if agent_id not in self._tool_acl:
            logger.warning(f"Agent {agent_id} not in tool ACL")
            return False
        
        # Check for wildcard access (allow all tools)
        if "*" in self._tool_acl[agent_id]:
            return True
        
        # Check for wildcard tools with pattern matching
        for allowed_tool in self._tool_acl[agent_id]:
            if allowed_tool.endswith("*"):
                # Convert * to regex pattern
                pattern = allowed_tool.replace("*", ".*")
                if re.match(pattern, tool_name):
                    return True
        
        # Check if the specific tool is allowed
        if tool_name not in self._tool_acl[agent_id]:
            logger.warning(f"Agent {agent_id} not allowed to use tool {tool_name}")
            return False
        
        return True
    
    def set_communication_acl(self, agent_id: str, allowed_recipients: List[str]) -> None:
        """
        Set the list of agents that an agent can communicate with.
        
        Args:
            agent_id: The ID of the agent.
            allowed_recipients: List of agent IDs that this agent can send messages to.
        """
        self._communication_acl[agent_id] = set(allowed_recipients)
        logger.info(f"Set communication ACL for agent {agent_id}: {allowed_recipients}")
    
    def add_communication_permission(self, agent_id: str, recipient_id: str) -> None:
        """
        Allow an agent to communicate with another agent.
        
        Args:
            agent_id: The ID of the agent to grant permission to.
            recipient_id: The ID of the agent they can communicate with.
        """
        if agent_id not in self._communication_acl:
            self._communication_acl[agent_id] = set()
        
        self._communication_acl[agent_id].add(recipient_id)
        logger.info(f"Added communication permission: {agent_id} -> {recipient_id}")
    
    def set_tool_acl(self, agent_id: str, allowed_tools: List[str]) -> None:
        """
        Set the list of tools that an agent can use.
        
        Args:
            agent_id: The ID of the agent.
            allowed_tools: List of tool names that this agent can use.
                          Use "*" for allowing all tools or "prefix*" for pattern matching.
        """
        self._tool_acl[agent_id] = set(allowed_tools)
        logger.info(f"Set tool ACL for agent {agent_id}: {allowed_tools}")
    
    def add_tool_permission(self, agent_id: str, tool_name: str) -> None:
        """
        Allow an agent to use a specific tool.
        
        Args:
            agent_id: The ID of the agent to grant permission to.
            tool_name: The name of the tool they can use.
                      Use "*" for allowing all tools or "prefix*" for pattern matching.
        """
        if agent_id not in self._tool_acl:
            self._tool_acl[agent_id] = set()
        
        self._tool_acl[agent_id].add(tool_name)
        logger.info(f"Added tool permission: {agent_id} -> {tool_name}")
    
    def log_security_event(self, event_type: str, details: Dict[str, Any]) -> None:
        """
        Log a security-relevant event.
        
        Args:
            event_type: The type of security event.
            details: Additional details about the event.
        """
        event_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        log_entry = {
            "event_id": event_id,
            "timestamp": timestamp,
            "event_type": event_type,
            **details
        }
        
        logger.info(f"Security event: {event_type}", extra=log_entry)
    
    def validate_tool_parameters(
        self, 
        tool_name: str, 
        parameters: Dict[str, Any],
        schema: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate tool parameters against a schema or for security issues.
        
        Args:
            tool_name: The name of the tool.
            parameters: The parameters to validate.
            schema: Optional schema to validate against.
            
        Returns:
            A tuple of (is_valid, error_message).
        """
        # Basic input validation
        if not isinstance(parameters, dict):
            return False, "Parameters must be a dictionary"
        
        # Schema validation
        if schema:
            # TODO: Implement full JSON Schema validation
            for required_key in schema.get("required", []):
                if required_key not in parameters:
                    return False, f"Missing required parameter: {required_key}"
            
            for param_name, param_value in parameters.items():
                if param_name in schema.get("properties", {}):
                    param_schema = schema["properties"][param_name]
                    param_type = param_schema.get("type")
                    
                    # Basic type checking
                    if param_type == "string" and not isinstance(param_value, str):
                        return False, f"Parameter {param_name} must be a string"
                    elif param_type == "number" and not isinstance(param_value, (int, float)):
                        return False, f"Parameter {param_name} must be a number"
                    elif param_type == "boolean" and not isinstance(param_value, bool):
                        return False, f"Parameter {param_name} must be a boolean"
                    elif param_type == "array" and not isinstance(param_value, list):
                        return False, f"Parameter {param_name} must be an array"
                    elif param_type == "object" and not isinstance(param_value, dict):
                        return False, f"Parameter {param_name} must be an object"
                    
                    # Check enum if present
                    if "enum" in param_schema and param_value not in param_schema["enum"]:
                        return False, f"Parameter {param_name} must be one of: {param_schema['enum']}"
        
        # Security checks
        # These are simple checks for demonstration; a real implementation would
        # have more comprehensive security checks
        
        # Check for common command injection patterns in string parameters
        for param_name, param_value in parameters.items():
            if isinstance(param_value, str):
                # Check for shell special characters or common injection patterns
                injection_patterns = [
                    r';\s*\w+',  # semicolon followed by command
                    r'\|\s*\w+',  # pipe followed by command
                    r'&&\s*\w+',  # && followed by command
                    r'`.*`',      # backtick command substitution
                    r'\$\(.+\)',   # $() command substitution
                ]
                
                for pattern in injection_patterns:
                    if re.search(pattern, param_value):
                        return False, f"Potential command injection in parameter {param_name}"
        
        return True, None
    
    def mask_sensitive_data(self, data: Dict[str, Any], sensitive_keys: List[str]) -> Dict[str, Any]:
        """
        Mask sensitive data for logging purposes.
        
        Args:
            data: The data containing potentially sensitive information.
            sensitive_keys: List of key names that contain sensitive data.
            
        Returns:
            A copy of the data with sensitive fields masked.
        """
        masked_data = data.copy()
        
        for key in sensitive_keys:
            if key in masked_data:
                masked_data[key] = "[REDACTED]"
                
        return masked_data
    
    def audit_agent_interactions(self, sender_id: str, recipient_id: str, message_content_type: str) -> None:
        """
        Audit agent interactions for security purposes.
        
        Args:
            sender_id: The ID of the sending agent.
            recipient_id: The ID of the receiving agent.
            message_content_type: The content type of the message.
        """
        self.log_security_event(
            "agent_interaction",
            {
                "sender_id": sender_id,
                "recipient_id": recipient_id,
                "content_type": message_content_type,
                "allowed": self.allow_communication(sender_id, recipient_id)
            }
        )
    
    def audit_tool_access(self, agent_id: str, tool_name: str, parameters: Dict[str, Any]) -> None:
        """
        Audit tool access for security purposes.
        
        Args:
            agent_id: The ID of the agent.
            tool_name: The name of the tool.
            parameters: The parameters used for the tool invocation.
        """
        # Mask sensitive parameters
        masked_parameters = self.mask_sensitive_data(
            parameters,
            ["api_key", "password", "secret", "token", "credentials"]
        )
        
        self.log_security_event(
            "tool_access",
            {
                "agent_id": agent_id,
                "tool_name": tool_name,
                "parameters": masked_parameters,
                "allowed": self.allow_tool_access(agent_id, tool_name)
            }
        )
