"""
Integration of access control system with other components of the Nexus Framework.

This module provides classes and functions for integrating the access control
system with the communication bus and other framework components.
"""

import json
import logging
import os
from typing import Dict, Set, List, Optional, Any, Tuple, Callable

from ...communication.reliable_bus import ReliableCommunicationBus
from ...messaging.broker import MessageBroker
from ...core.message import Message
from ...security.authentication import AuthenticationService

from .permissions import Permission, PermissionSet, ResourceType, ResourceAction
from .roles import Role, RoleManager, RoleRegistry
from .policies import PolicyManager, PolicyContext, Policy, EffectType
from .acl import ACLManager, AccessControlList
from .middleware import AccessControlMiddleware, AccessControlProcessor

logger = logging.getLogger(__name__)

class AccessControlService:
    """
    Main service for access control in the Nexus Framework.
    
    This class provides a unified interface for managing access control
    through roles, policies, and ACLs.
    """
    
    def __init__(self, 
                role_manager: Optional[RoleManager] = None,
                policy_manager: Optional[PolicyManager] = None,
                acl_manager: Optional[ACLManager] = None,
                config_path: Optional[str] = None):
        """
        Initialize the access control service.
        
        Args:
            role_manager: Manager for roles.
            policy_manager: Manager for policies.
            acl_manager: Manager for ACLs.
            config_path: Path to the configuration directory.
        """
        # Create or use managers
        self.role_manager = role_manager or RoleManager()
        self.policy_manager = policy_manager or PolicyManager(self.role_manager)
        self.acl_manager = acl_manager or ACLManager(self.role_manager)
        
        # Set up config paths
        self.config_path = config_path
        if config_path:
            self.roles_file = os.path.join(config_path, "roles.json")
            self.policies_file = os.path.join(config_path, "policies.json")
            self.acls_file = os.path.join(config_path, "acls.json")
            
            # Load configuration if files exist
            self._load_configuration()
        
        logger.info("Access control service initialized")
    
    def _load_configuration(self) -> None:
        """Load configuration from files if they exist."""
        if self.config_path:
            # Create config directory if it doesn't exist
            os.makedirs(self.config_path, exist_ok=True)
            
            # Load roles
            if os.path.exists(self.roles_file):
                try:
                    with open(self.roles_file, 'r') as f:
                        data = json.load(f)
                        self.role_manager = RoleManager.from_dict(data)
                        logger.info(f"Loaded roles from {self.roles_file}")
                except Exception as e:
                    logger.error(f"Error loading roles from {self.roles_file}: {e}")
            
            # Load policies
            if os.path.exists(self.policies_file):
                try:
                    self.policy_manager.load_from_file(self.policies_file)
                    logger.info(f"Loaded policies from {self.policies_file}")
                except Exception as e:
                    logger.error(f"Error loading policies from {self.policies_file}: {e}")
            
            # Load ACLs
            if os.path.exists(self.acls_file):
                try:
                    self.acl_manager.load_from_file(self.acls_file)
                    logger.info(f"Loaded ACLs from {self.acls_file}")
                except Exception as e:
                    logger.error(f"Error loading ACLs from {self.acls_file}: {e}")
    
    def save_configuration(self) -> None:
        """Save configuration to files."""
        if self.config_path:
            # Create config directory if it doesn't exist
            os.makedirs(self.config_path, exist_ok=True)
            
            # Save roles
            try:
                with open(self.roles_file, 'w') as f:
                    json.dump(self.role_manager.to_dict(), f, indent=2)
                    logger.info(f"Saved roles to {self.roles_file}")
            except Exception as e:
                logger.error(f"Error saving roles to {self.roles_file}: {e}")
            
            # Save policies
            try:
                self.policy_manager.save_to_file(self.policies_file)
                logger.info(f"Saved policies to {self.policies_file}")
            except Exception as e:
                logger.error(f"Error saving policies to {self.policies_file}: {e}")
            
            # Save ACLs
            try:
                self.acl_manager.save_to_file(self.acls_file)
                logger.info(f"Saved ACLs to {self.acls_file}")
            except Exception as e:
                logger.error(f"Error saving ACLs to {self.acls_file}: {e}")
    
    def create_default_configuration(self) -> None:
        """Create default configuration with standard roles and policies."""
        # Create default roles if role manager is empty
        if not hasattr(self.role_manager, 'roles') or not self.role_manager.roles:
            roles = RoleRegistry.create_all_default_roles()
            for role in roles.values():
                try:
                    self.role_manager.add_role(role)
                except Exception:
                    # Role might already exist
                    pass
        
        # Create basic policies
        if hasattr(self.policy_manager, 'create_basic_policies'):
            self.policy_manager.create_basic_policies()
        
        # Save the configuration
        self.save_configuration()
        
        logger.info("Created default access control configuration")
    
    def has_permission(self, 
                      entity_id: str,
                      permission: Permission,
                      resource_id: Optional[str] = None) -> bool:
        """
        Check if an entity has a specific permission.
        
        This method checks both roles, policies, and ACLs.
        
        Args:
            entity_id: The entity ID to check.
            permission: The permission to check.
            resource_id: Optional specific resource ID to check.
            
        Returns:
            True if the entity has the permission, False otherwise.
        """
        # Check ACLs first (fastest)
        if self.acl_manager and self.acl_manager.has_permission(entity_id, permission, resource_id):
            return True
        
        # Check roles
        if self.role_manager and self.role_manager.has_permission(entity_id, permission):
            return True
        
        # Check policies
        resource_type = permission.resource_type.value
        action = permission.action.value
        instance_id = permission.instance if permission.instance != "*" else resource_id
        
        if self.policy_manager and self.policy_manager.is_allowed(
            entity_id, resource_type, instance_id, action
        ):
            return True
            
        return False
    
    def grant_permission(self, 
                        entity_id: str,
                        permission: Permission,
                        resource_id: Optional[str] = None,
                        expires_in: Optional[float] = None) -> None:
        """
        Grant a permission to an entity.
        
        This method grants the permission through ACLs.
        
        Args:
            entity_id: The entity ID to grant the permission to.
            permission: The permission to grant.
            resource_id: Optional specific resource ID to grant the permission for.
            expires_in: Optional expiration time in seconds from now.
        """
        if self.acl_manager:
            self.acl_manager.grant_permission(entity_id, permission, resource_id, expires_in)
    
    def assign_role(self, entity_id: str, role_name: str) -> None:
        """
        Assign a role to an entity.
        
        Args:
            entity_id: The entity ID to assign the role to.
            role_name: The name of the role to assign.
        """
        if self.role_manager:
            self.role_manager.assign_role(entity_id, role_name)
    
    def create_processor(self, strict_mode: bool = False) -> AccessControlProcessor:
        """
        Create an access control processor.
        
        Args:
            strict_mode: Whether to enforce strict access control.
            
        Returns:
            An access control processor.
        """
        return AccessControlProcessor(
            policy_manager=self.policy_manager,
            acl_manager=self.acl_manager,
            role_manager=self.role_manager,
            strict_mode=strict_mode
        )
    
    def create_middleware(self, strict_mode: bool = False) -> AccessControlMiddleware:
        """
        Create an access control middleware.
        
        Args:
            strict_mode: Whether to enforce strict access control.
            
        Returns:
            An access control middleware.
        """
        return AccessControlMiddleware(
            policy_manager=self.policy_manager,
            acl_manager=self.acl_manager,
            role_manager=self.role_manager,
            strict_mode=strict_mode
        )

class SecureCommunicationBus(ReliableCommunicationBus):
    """
    Communication bus with integrated authentication and access control.
    
    This class extends the reliable communication bus with security features
    including both authentication and access control.
    """
    
    def __init__(self, 
                broker: Optional[MessageBroker] = None, 
                legacy_mode: bool = False,
                auth_service: Optional[AuthenticationService] = None,
                access_control_service: Optional[AccessControlService] = None,
                strict_mode: bool = False,
                config_path: Optional[str] = None):
        """
        Initialize the secure communication bus.
        
        Args:
            broker: Message broker to use.
            legacy_mode: Whether to fall back to in-memory messaging if broker is unavailable.
            auth_service: Authentication service to use.
            access_control_service: Access control service to use.
            strict_mode: Whether to enforce strict security checks.
            config_path: Path to the configuration directory.
        """
        # Initialize the parent class
        super().__init__(broker, legacy_mode)
        
        # Create or use security services
        self.auth_service = auth_service
        self.access_control_service = access_control_service or AccessControlService(config_path=config_path)
        
        # Create security processors
        self.auth_processor = None
        if self.auth_service:
            from ...security.authentication import AuthenticationProcessor
            self.auth_processor = AuthenticationProcessor(self.auth_service, strict_mode)
        
        self.access_control_processor = self.access_control_service.create_processor(strict_mode)
        
        logger.info(f"Secure communication bus initialized (strict_mode={strict_mode})")
    
    def send_message(self, message: Message) -> Optional[str]:
        """
        Send a message with security checks.
        
        Args:
            message: The message to send.
            
        Returns:
            Message ID if sent successfully, None otherwise.
        """
        # Add access control metadata
        processed_message = self.access_control_processor.process_outgoing_message(message)
        
        # Add authentication if available
        if self.auth_processor:
            processed_message = self.auth_processor.process_outgoing_message(processed_message)
        
        # Send the secured message
        return super().send_message(processed_message)
    
    def send_broadcast(self, message: Message, recipients: List[str]) -> Dict[str, Optional[str]]:
        """
        Send a message to multiple recipients with security checks.
        
        Args:
            message: The message to send.
            recipients: List of recipient IDs.
            
        Returns:
            Dictionary mapping recipient IDs to message IDs or None if sending failed.
        """
        # Add access control metadata
        processed_message = self.access_control_processor.process_outgoing_message(message)
        
        # Add authentication if available
        if self.auth_processor:
            processed_message = self.auth_processor.process_outgoing_message(processed_message)
        
        # Send the secured message
        return super().send_broadcast(processed_message, recipients)
    
    def wrap_message_handler(self, handler: Callable[[Message], Optional[Message]]) -> Callable[[Message], Optional[Message]]:
        """
        Wrap a message handler with security checks.
        
        Args:
            handler: The original message handler function.
            
        Returns:
            A wrapped handler function.
        """
        # Start with the original handler
        wrapped_handler = handler
        
        # Wrap with access control
        wrapped_handler = self.access_control_processor.wrap_message_handler(wrapped_handler)
        
        # Wrap with authentication if available
        if self.auth_processor:
            wrapped_handler = self.auth_processor.wrap_message_handler(wrapped_handler)
        
        # Wrap with parent class functionality
        return super().wrap_message_handler(wrapped_handler)
    
    def register_agent(self, agent, handlers=None, topics=None):
        """
        Register an agent with the bus, wrapping its handlers for security.
        
        Args:
            agent: The agent to register.
            handlers: Optional mapping of topics to handler functions.
            topics: Optional list of topics to subscribe to.
        """
        # If the agent has a process_message method, wrap it for security
        if hasattr(agent, 'process_message'):
            # Start with the original method
            original_process_message = agent.process_message
            
            # Wrap with access control
            wrapped_method = self.access_control_processor.wrap_message_handler(original_process_message)
            
            # Wrap with authentication if available
            if self.auth_processor:
                wrapped_method = self.auth_processor.wrap_message_handler(wrapped_method)
                
            # Replace the method
            agent.process_message = wrapped_method
        
        # Register with parent class
        super().register_agent(agent, handlers, topics)

class AccessControlManager:
    """
    Manages access control settings and configuration.
    
    This class provides high-level functionality for managing access control,
    including user interfaces and configuration management.
    """
    
    def __init__(self, service: AccessControlService):
        """
        Initialize the access control manager.
        
        Args:
            service: The access control service to manage.
        """
        self.service = service
    
    def create_role(self, 
                   name: str, 
                   description: str, 
                   permissions: List[str],
                   parent_roles: Optional[List[str]] = None) -> Role:
        """
        Create a new role.
        
        Args:
            name: Role name.
            description: Role description.
            permissions: List of permission strings.
            parent_roles: Optional list of parent role names.
            
        Returns:
            The created role.
        """
        # Convert permission strings to Permission objects
        permission_set = PermissionSet.from_string_list(permissions)
        
        # Create the role
        role = Role(
            name=name,
            description=description,
            permissions=permission_set,
            parent_roles=parent_roles or []
        )
        
        # Add it to the role manager
        self.service.role_manager.add_role(role)
        
        # Save configuration
        self.service.save_configuration()
        
        return role
    
    def create_policy(self, 
                     name: str, 
                     description: str,
                     effect: str,
                     conditions: Optional[Dict[str, Any]] = None,
                     resource_patterns: Optional[List[str]] = None,
                     action_patterns: Optional[List[str]] = None,
                     entity_patterns: Optional[List[str]] = None,
                     priority: int = 0) -> Policy:
        """
        Create a new policy.
        
        Args:
            name: Policy name.
            description: Policy description.
            effect: Effect of the policy ("allow" or "deny").
            conditions: Optional conditions for the policy.
            resource_patterns: Optional resource patterns.
            action_patterns: Optional action patterns.
            entity_patterns: Optional entity patterns.
            priority: Priority of the policy.
            
        Returns:
            The created policy.
        """
        # Convert effect string to enum
        try:
            effect_enum = EffectType(effect.lower())
        except ValueError:
            effect_enum = EffectType.ALLOW if effect.lower() == "allow" else EffectType.DENY
        
        # Create the policy
        policy = Policy(
            name=name,
            description=description,
            effect=effect_enum,
            conditions=conditions or {},
            resource_patterns=resource_patterns or ["*"],
            action_patterns=action_patterns or ["*"],
            entity_patterns=entity_patterns or ["*"],
            priority=priority
        )
        
        # Add it to the policy manager
        self.service.policy_manager.add_policy(policy)
        
        # Save configuration
        self.service.save_configuration()
        
        return policy
    
    def grant_acl_permission(self,
                           entity_id: str,
                           resource_type: str,
                           action: str,
                           resource_id: Optional[str] = None,
                           expires_in: Optional[float] = None) -> None:
        """
        Grant a permission through ACLs.
        
        Args:
            entity_id: Entity ID to grant the permission to.
            resource_type: Resource type.
            action: Action to allow.
            resource_id: Optional specific resource ID.
            expires_in: Optional expiration time in seconds.
        """
        # Convert to Permission object
        permission = Permission(
            ResourceType.from_string(resource_type),
            ResourceAction.from_string(action),
            resource_id or "*"
        )
        
        # Grant the permission
        self.service.acl_manager.grant_permission(entity_id, permission, resource_id, expires_in)
        
        # Save configuration
        self.service.save_configuration()
    
    def assign_role_to_entity(self, entity_id: str, role_name: str) -> None:
        """
        Assign a role to an entity.
        
        Args:
            entity_id: Entity ID to assign the role to.
            role_name: Role name to assign.
        """
        # Assign the role
        self.service.role_manager.assign_role(entity_id, role_name)
        
        # Save configuration
        self.service.save_configuration()
    
    def check_permission(self,
                        entity_id: str,
                        resource_type: str,
                        action: str,
                        resource_id: Optional[str] = None) -> Tuple[bool, str]:
        """
        Check if an entity has a permission and explain why.
        
        Args:
            entity_id: Entity ID to check.
            resource_type: Resource type.
            action: Action to check.
            resource_id: Optional specific resource ID.
            
        Returns:
            Tuple of (is_allowed, reason).
        """
        # Convert to Permission object
        permission = Permission(
            ResourceType.from_string(resource_type),
            ResourceAction.from_string(action),
            resource_id or "*"
        )
        
        # Check ACLs
        if self.service.acl_manager.has_permission(entity_id, permission, resource_id):
            return True, "Permission granted through ACL"
        
        # Check roles
        if self.service.role_manager.has_permission(entity_id, permission):
            roles = self.service.role_manager.get_entity_roles(entity_id)
            return True, f"Permission granted through roles: {', '.join(roles)}"
        
        # Check policies
        context = PolicyContext(
            entity_id=entity_id,
            resource_type=resource_type,
            resource_id=resource_id or "*",
            action=action
        )
        
        is_allowed = self.service.policy_manager.is_allowed(
            entity_id, resource_type, resource_id, action,
            context_data=context.to_dict()
        )
        
        if is_allowed:
            return True, "Permission granted through policy"
        
        # No permission
        return False, "Permission denied. No matching role, ACL, or policy."
    
    def list_entity_permissions(self, entity_id: str) -> Dict[str, Any]:
        """
        List all permissions for an entity.
        
        Args:
            entity_id: Entity ID to list permissions for.
            
        Returns:
            Dictionary containing roles, direct permissions, and effective permissions.
        """
        result = {
            "entity_id": entity_id,
            "roles": [],
            "direct_permissions": [],
            "effective_permissions": []
        }
        
        # Get roles
        if hasattr(self.service.role_manager, 'get_entity_roles'):
            result["roles"] = self.service.role_manager.get_entity_roles(entity_id)
        
        # Get direct permissions from ACLs
        if hasattr(self.service.acl_manager, 'get_permissions'):
            direct_permissions = self.service.acl_manager.get_permissions(entity_id)
            result["direct_permissions"] = direct_permissions.to_string_list()
        
        # Get effective permissions from all sources
        effective_permissions = PermissionSet()
        
        # Add permissions from roles
        if hasattr(self.service.role_manager, 'get_entity_permissions'):
            role_permissions = self.service.role_manager.get_entity_permissions(entity_id)
            effective_permissions = effective_permissions.merge(role_permissions)
        
        # Add permissions from ACLs
        if hasattr(self.service.acl_manager, 'get_permissions'):
            acl_permissions = self.service.acl_manager.get_permissions(entity_id)
            effective_permissions = effective_permissions.merge(acl_permissions)
        
        result["effective_permissions"] = effective_permissions.to_string_list()
        
        return result
    
    def list_roles(self) -> List[Dict[str, Any]]:
        """
        List all roles in the system.
        
        Returns:
            List of role information dictionaries.
        """
        result = []
        
        if hasattr(self.service.role_manager, 'roles'):
            for role_name, role in self.service.role_manager.roles.items():
                role_info = {
                    "name": role_name,
                    "description": role.description,
                    "permissions": role.permissions.to_string_list(),
                    "parent_roles": role.parent_roles
                }
                result.append(role_info)
                
        return result
    
    def list_policies(self) -> List[Dict[str, Any]]:
        """
        List all policies in the system.
        
        Returns:
            List of policy information dictionaries.
        """
        result = []
        
        if hasattr(self.service.policy_manager, 'engine') and hasattr(self.service.policy_manager.engine, 'default_policies'):
            for policy in self.service.policy_manager.engine.default_policies.policies:
                policy_info = {
                    "name": policy.name,
                    "description": policy.description,
                    "effect": policy.effect.value,
                    "conditions": policy.conditions,
                    "resource_patterns": policy.resource_patterns,
                    "action_patterns": policy.action_patterns,
                    "entity_patterns": policy.entity_patterns,
                    "priority": policy.priority
                }
                result.append(policy_info)
                
        return result

def create_secure_bus(broker: Optional[MessageBroker] = None,
                    legacy_mode: bool = False,
                    auth_service: Optional[AuthenticationService] = None,
                    config_path: Optional[str] = None,
                    strict_mode: bool = False) -> SecureCommunicationBus:
    """
    Create a secure communication bus with both authentication and access control.
    
    This is a convenience function for creating a secure bus with common settings.
    
    Args:
        broker: Message broker to use.
        legacy_mode: Whether to fall back to in-memory messaging if broker is unavailable.
        auth_service: Authentication service to use.
        config_path: Path to the configuration directory.
        strict_mode: Whether to enforce strict security checks.
        
    Returns:
        A secure communication bus.
    """
    # Create access control service
    access_control_service = AccessControlService(config_path=config_path)
    
    # Create secure bus
    bus = SecureCommunicationBus(
        broker=broker,
        legacy_mode=legacy_mode,
        auth_service=auth_service,
        access_control_service=access_control_service,
        strict_mode=strict_mode,
        config_path=config_path
    )
    
    # Create default configuration if needed
    if config_path:
        access_control_service.create_default_configuration()
    
    return bus
