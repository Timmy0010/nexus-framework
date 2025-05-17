"""
Middleware for implementing access control in the Nexus Framework.

This module provides middleware components that can be integrated into the
message processing pipeline to enforce access control policies.
"""

import logging
from typing import Dict, Set, List, Optional, Any, Tuple, Callable

from ...core.message import Message
from .permissions import Permission, PermissionSet, ResourceType, ResourceAction, PermissionError
from .policies import PolicyManager, PolicyContext, EffectType, PolicyError
from .acl import ACLManager, AccessControlError
from .roles import RoleManager, RoleError

logger = logging.getLogger(__name__)

class AccessControlMiddleware:
    """
    Middleware for enforcing access control policies.
    
    This middleware can be inserted into the message processing pipeline
    to automatically check permissions for message senders and recipients.
    """
    
    def __init__(self, 
                policy_manager: Optional[PolicyManager] = None,
                acl_manager: Optional[ACLManager] = None,
                role_manager: Optional[RoleManager] = None,
                strict_mode: bool = False,
                exempt_paths: Optional[List[str]] = None):
        """
        Initialize the access control middleware.
        
        Args:
            policy_manager: Manager for access control policies.
            acl_manager: Manager for access control lists.
            role_manager: Manager for roles.
            strict_mode: If True, reject messages that fail permission checks.
                       If False, log a warning but allow them.
            exempt_paths: List of message paths that are exempt from access control.
                        Format: "sender_id:recipient_id"
        """
        self.policy_manager = policy_manager or PolicyManager()
        self.acl_manager = acl_manager
        self.role_manager = role_manager
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
        
        logger.info(f"Access control middleware initialized (strict_mode={strict_mode})")
    
    def _is_exempt(self, message: Message) -> bool:
        """
        Check if a message is exempt from access control.
        
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
    
    def check_permission(self, message: Message) -> Tuple[bool, Optional[str]]:
        """
        Check if a message is allowed based on access control policies.
        
        Args:
            message: The message to check.
            
        Returns:
            Tuple of (is_allowed, reason). If is_allowed is False, reason contains
            the explanation.
        """
        # Check if message is exempt
        if self._is_exempt(message):
            logger.debug(f"Message exempt from access control: {message.message_id}")
            return True, "Exempt path"
        
        # Extract relevant information from the message
        sender_id = message.sender_id
        recipient_id = message.recipient_id
        content_type = message.content_type or "text"
        
        # Define the resources being accessed
        # For messages, we check if the sender can send to the recipient
        resource_type = "message"
        resource_id = f"{sender_id}:{recipient_id}"
        action = "create"
        
        # Create a permission for this action
        try:
            permission = Permission(
                ResourceType.MESSAGE,
                ResourceAction.CREATE,
                recipient_id
            )
            
            # Check if the sender has this permission
            if self.acl_manager:
                if self.acl_manager.has_permission(sender_id, permission):
                    return True, "ACL allows"
            
            # Check policy-based permissions
            context = PolicyContext(
                entity_id=sender_id,
                resource_type=resource_type,
                resource_id=recipient_id,
                action=action,
                message_metadata={
                    "content_type": content_type,
                    "message_id": message.message_id,
                    "workflow_id": message.workflow_id,
                    "timestamp": message.timestamp
                }
            )
            
            is_allowed = self.policy_manager.is_allowed(
                sender_id, resource_type, recipient_id, action,
                context_data=context.to_dict()
            )
            
            if is_allowed:
                return True, "Policy allows"
            else:
                reason = self.policy_manager.why(
                    sender_id, resource_type, recipient_id, action,
                    context_data=context.to_dict()
                )
                return False, reason
                
        except Exception as e:
            logger.error(f"Error checking permissions for message {message.message_id}: {e}")
            return not self.strict_mode, f"Error: {str(e)}"
    
    def process_message(self, message: Message) -> Tuple[bool, Optional[str], Message]:
        """
        Process a message according to access control policies.
        
        Args:
            message: The message to process.
            
        Returns:
            Tuple of (is_allowed, reason, message). If is_allowed is False and
            strict_mode is True, message is None.
        """
        is_allowed, reason = self.check_permission(message)
        
        if not is_allowed and self.strict_mode:
            logger.warning(f"Access denied for message {message.message_id}: {reason}")
            return False, reason, None
        elif not is_allowed:
            logger.warning(f"Access warning for message {message.message_id}: {reason}")
            
        return is_allowed, reason, message
    
    def wrap_message_handler(self, handler: Callable[[Message], Optional[Message]]) -> Callable[[Message], Optional[Message]]:
        """
        Wrap a message handler to automatically enforce access control.
        
        Args:
            handler: The original message handler function.
            
        Returns:
            A wrapped handler function.
        """
        def wrapped_handler(message: Message) -> Optional[Message]:
            # Check permissions
            is_allowed, reason, processed_message = self.process_message(message)
            
            if not is_allowed and self.strict_mode:
                logger.warning(f"Rejected message {message.message_id} due to access control: {reason}")
                return None
            
            # Process the message
            response = handler(processed_message)
            
            # If there's a response, check permissions for it too
            if response is not None:
                is_allowed, reason, processed_response = self.process_message(response)
                
                if not is_allowed and self.strict_mode:
                    logger.warning(f"Rejected response {response.message_id} due to access control: {reason}")
                    return None
                
                return processed_response
                
            return response
            
        return wrapped_handler
    
    def add_permission_metadata(self, message: Message) -> Message:
        """
        Add permission-related metadata to a message.
        
        This can be used to enrich messages with information about
        the sender's permissions for debugging or auditing purposes.
        
        Args:
            message: The message to enrich.
            
        Returns:
            The enriched message.
        """
        # Create a copy to avoid modifying the original
        enriched_message = message.copy()
        
        # Extract relevant information
        sender_id = message.sender_id
        recipient_id = message.recipient_id
        
        # Skip if the message already has permission metadata
        if enriched_message.metadata and "permissions" in enriched_message.metadata:
            return enriched_message
            
        # Initialize metadata if needed
        if not enriched_message.metadata:
            enriched_message.metadata = {}
            
        # If we have a role manager, add role information
        if self.role_manager:
            try:
                roles = self.role_manager.get_entity_roles(sender_id)
                enriched_message.metadata["roles"] = roles
            except Exception as e:
                logger.warning(f"Error getting roles for {sender_id}: {e}")
        
        # If we have an ACL manager, add permission information
        if self.acl_manager:
            try:
                permissions = self.acl_manager.get_permissions(
                    sender_id, "message", recipient_id
                )
                enriched_message.metadata["permissions"] = permissions.to_string_list()
            except Exception as e:
                logger.warning(f"Error getting permissions for {sender_id}: {e}")
        
        return enriched_message

class AccessControlProcessor:
    """
    Message processor that checks and enforces access control policies.
    
    This class can be used as a standalone processor or integrated with
    other components like the authentication processor.
    """
    
    def __init__(self, 
                policy_manager: Optional[PolicyManager] = None,
                acl_manager: Optional[ACLManager] = None,
                role_manager: Optional[RoleManager] = None,
                strict_mode: bool = False,
                exempt_paths: Optional[List[str]] = None):
        """
        Initialize the access control processor.
        
        Args:
            policy_manager: Manager for access control policies.
            acl_manager: Manager for access control lists.
            role_manager: Manager for roles.
            strict_mode: If True, reject messages that fail permission checks.
            exempt_paths: List of message paths exempt from access control.
        """
        self.middleware = AccessControlMiddleware(
            policy_manager, acl_manager, role_manager, strict_mode, exempt_paths
        )
        
        logger.info(f"Access control processor initialized (strict_mode={strict_mode})")
    
    def process_outgoing_message(self, message: Message) -> Message:
        """
        Process an outgoing message by checking permissions and adding metadata.
        
        Args:
            message: The message to process.
            
        Returns:
            The processed message, possibly with added metadata.
        """
        return self.middleware.add_permission_metadata(message)
    
    def process_incoming_message(self, message: Message) -> Tuple[bool, Optional[Message]]:
        """
        Process an incoming message by checking permissions.
        
        Args:
            message: The message to process.
            
        Returns:
            Tuple of (is_allowed, processed_message).
            If is_allowed is False and strict_mode is True, processed_message is None.
        """
        is_allowed, reason, processed_message = self.middleware.process_message(message)
        return is_allowed, processed_message
    
    def wrap_message_handler(self, handler: Callable[[Message], Optional[Message]]) -> Callable[[Message], Optional[Message]]:
        """
        Wrap a message handler to automatically enforce access control.
        
        Args:
            handler: The original message handler function.
            
        Returns:
            A wrapped handler function.
        """
        return self.middleware.wrap_message_handler(handler)
    
    def check_tool_access(self, 
                         agent_id: str, 
                         tool_name: str, 
                         parameters: Optional[Dict[str, Any]] = None) -> Tuple[bool, Optional[str]]:
        """
        Check if an agent has permission to use a specific tool.
        
        Args:
            agent_id: The ID of the agent.
            tool_name: The name of the tool.
            parameters: Optional parameters for the tool.
            
        Returns:
            Tuple of (is_allowed, reason). If is_allowed is False, reason contains
            the explanation.
        """
        try:
            # Create a permission for this action
            permission = Permission(
                ResourceType.TOOL,
                ResourceAction.EXECUTE,
                tool_name
            )
            
            # Check if the agent has this permission through ACLs
            if self.middleware.acl_manager:
                if self.middleware.acl_manager.has_permission(agent_id, permission):
                    return True, "ACL allows"
            
            # Check policy-based permissions
            if self.middleware.policy_manager:
                context = PolicyContext(
                    entity_id=agent_id,
                    resource_type="tool",
                    resource_id=tool_name,
                    action="execute",
                    additional_context={"parameters": parameters or {}}
                )
                
                is_allowed = self.middleware.policy_manager.is_allowed(
                    agent_id, "tool", tool_name, "execute",
                    context_data=context.to_dict()
                )
                
                if is_allowed:
                    return True, "Policy allows"
                else:
                    reason = self.middleware.policy_manager.why(
                        agent_id, "tool", tool_name, "execute",
                        context_data=context.to_dict()
                    )
                    return False, reason
            
            # If we have no policy manager or ACL manager, default based on strict mode
            return not self.middleware.strict_mode, "No access control configured"
            
        except Exception as e:
            logger.error(f"Error checking tool access for {agent_id} to {tool_name}: {e}")
            return not self.middleware.strict_mode, f"Error: {str(e)}"
    
    def wrap_tool_handler(self, handler: Callable) -> Callable:
        """
        Wrap a tool handler to automatically enforce access control.
        
        Args:
            handler: The original tool handler function.
            
        Returns:
            A wrapped handler function.
        """
        def wrapped_handler(agent_id: str, tool_name: str, parameters: Dict[str, Any], *args, **kwargs):
            # Check if the agent has permission to use this tool
            is_allowed, reason = self.check_tool_access(agent_id, tool_name, parameters)
            
            if not is_allowed and self.middleware.strict_mode:
                logger.warning(f"Tool access denied for {agent_id} to {tool_name}: {reason}")
                raise AccessControlError(f"Access denied: {reason}")
            elif not is_allowed:
                logger.warning(f"Tool access warning for {agent_id} to {tool_name}: {reason}")
            
            # Call the original handler
            return handler(agent_id, tool_name, parameters, *args, **kwargs)
            
        return wrapped_handler
