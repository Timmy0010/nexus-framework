"""
Permission definitions and management for the Nexus Framework's access control system.

This module provides the core classes for defining and managing permissions.
"""

import enum
import logging
from typing import Dict, Set, List, Optional, Any, Tuple, FrozenSet

logger = logging.getLogger(__name__)

class PermissionError(Exception):
    """Exception raised for permission-related errors."""
    pass

class ResourceType(enum.Enum):
    """Enum defining resource types in the system."""
    AGENT = "agent"
    MESSAGE = "message"
    WORKFLOW = "workflow"
    TOOL = "tool"
    SERVICE = "service"
    CONFIG = "config"
    DATA = "data"
    SYSTEM = "system"
    ANY = "*"
    
    @classmethod
    def from_string(cls, value: str) -> 'ResourceType':
        """Convert a string to a ResourceType enum value."""
        try:
            return cls(value.lower())
        except ValueError:
            # Handle legacy or custom resource types
            logger.warning(f"Unknown resource type: {value}")
            return cls.ANY

class ResourceAction(enum.Enum):
    """Enum defining actions that can be performed on resources."""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    EXECUTE = "execute"
    MANAGE = "manage"
    LIST = "list"
    ANY = "*"
    
    @classmethod
    def from_string(cls, value: str) -> 'ResourceAction':
        """Convert a string to a ResourceAction enum value."""
        try:
            return cls(value.lower())
        except ValueError:
            # Handle legacy or custom actions
            logger.warning(f"Unknown resource action: {value}")
            return cls.ANY

class Permission:
    """
    Represents a permission to perform an action on a resource type.
    
    Permissions can be specified in the format:
        resourceType:action:instance
    
    Examples:
        agent:read:*     - Can read all agents
        message:create:* - Can create any message
        tool:execute:calculator - Can execute the calculator tool
    """
    
    def __init__(self, 
                resource_type: ResourceType, 
                action: ResourceAction, 
                instance: str = "*"):
        """
        Initialize a permission.
        
        Args:
            resource_type: The type of resource this permission applies to.
            action: The action this permission allows.
            instance: Specific resource instance this permission applies to,
                    or "*" for all instances.
        """
        self.resource_type = resource_type
        self.action = action
        self.instance = instance
    
    @classmethod
    def from_string(cls, permission_str: str) -> 'Permission':
        """
        Create a Permission object from a string representation.
        
        Args:
            permission_str: String in the format "resourceType:action:instance"
                          or "resourceType:action" (instance defaults to "*")
        
        Returns:
            A Permission object.
            
        Raises:
            PermissionError: If the string format is invalid.
        """
        parts = permission_str.split(':')
        
        if len(parts) < 2 or len(parts) > 3:
            raise PermissionError(f"Invalid permission format: {permission_str}")
        
        resource_type = ResourceType.from_string(parts[0])
        action = ResourceAction.from_string(parts[1])
        instance = parts[2] if len(parts) == 3 else "*"
        
        return cls(resource_type, action, instance)
    
    def to_string(self) -> str:
        """
        Convert the permission to its string representation.
        
        Returns:
            String representation in the format "resourceType:action:instance"
        """
        return f"{self.resource_type.value}:{self.action.value}:{self.instance}"
    
    def implies(self, other: 'Permission') -> bool:
        """
        Check if this permission implies (includes) another permission.
        
        A permission implies another if it is more general or equal.
        For example, "agent:*:*" implies "agent:read:assistant1"
        
        Args:
            other: The permission to check against.
            
        Returns:
            True if this permission implies the other, False otherwise.
        """
        # Check resource type
        if self.resource_type != ResourceType.ANY and self.resource_type != other.resource_type:
            return False
        
        # Check action
        if self.action != ResourceAction.ANY and self.action != other.action:
            return False
        
        # Check instance
        if self.instance != "*" and self.instance != other.instance:
            return False
        
        return True
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Permission):
            return False
        
        return (self.resource_type == other.resource_type and
                self.action == other.action and
                self.instance == other.instance)
    
    def __hash__(self) -> int:
        return hash((self.resource_type, self.action, self.instance))
    
    def __str__(self) -> str:
        return self.to_string()
    
    def __repr__(self) -> str:
        return f"Permission({self.to_string()})"

class PermissionSet:
    """
    A set of permissions.
    
    This class provides operations for working with groups of permissions,
    including checking if a specific permission is granted.
    """
    
    def __init__(self, permissions: Optional[List[Permission]] = None):
        """
        Initialize a permission set.
        
        Args:
            permissions: Initial list of permissions.
        """
        self.permissions: Set[Permission] = set(permissions or [])
    
    def add(self, permission: Permission) -> None:
        """
        Add a permission to the set.
        
        Args:
            permission: The permission to add.
        """
        self.permissions.add(permission)
    
    def remove(self, permission: Permission) -> None:
        """
        Remove a permission from the set.
        
        Args:
            permission: The permission to remove.
            
        Raises:
            PermissionError: If the permission is not in the set.
        """
        try:
            self.permissions.remove(permission)
        except KeyError:
            raise PermissionError(f"Permission {permission} not in set")
    
    def clear(self) -> None:
        """Clear all permissions from the set."""
        self.permissions.clear()
    
    def has_permission(self, permission: Permission) -> bool:
        """
        Check if the set grants a specific permission.
        
        Args:
            permission: The permission to check.
            
        Returns:
            True if the permission is granted, False otherwise.
        """
        # Direct match
        if permission in self.permissions:
            return True
        
        # Check for implied permissions
        for p in self.permissions:
            if p.implies(permission):
                return True
        
        return False
    
    def has_any_permission(self, permissions: List[Permission]) -> bool:
        """
        Check if the set grants any of the specified permissions.
        
        Args:
            permissions: List of permissions to check.
            
        Returns:
            True if any permission is granted, False otherwise.
        """
        return any(self.has_permission(p) for p in permissions)
    
    def has_all_permissions(self, permissions: List[Permission]) -> bool:
        """
        Check if the set grants all of the specified permissions.
        
        Args:
            permissions: List of permissions to check.
            
        Returns:
            True if all permissions are granted, False otherwise.
        """
        return all(self.has_permission(p) for p in permissions)
    
    def merge(self, other: 'PermissionSet') -> 'PermissionSet':
        """
        Merge this permission set with another.
        
        Args:
            other: The permission set to merge with.
            
        Returns:
            A new permission set containing all permissions from both sets.
        """
        result = PermissionSet()
        result.permissions = self.permissions.union(other.permissions)
        return result
    
    def as_list(self) -> List[Permission]:
        """
        Get the permissions as a list.
        
        Returns:
            List of permissions.
        """
        return list(self.permissions)
    
    def to_string_list(self) -> List[str]:
        """
        Get the permissions as a list of strings.
        
        Returns:
            List of permission strings.
        """
        return [p.to_string() for p in self.permissions]
    
    @classmethod
    def from_string_list(cls, permission_strings: List[str]) -> 'PermissionSet':
        """
        Create a permission set from a list of permission strings.
        
        Args:
            permission_strings: List of permission strings.
            
        Returns:
            A new permission set.
        """
        permissions = [Permission.from_string(p) for p in permission_strings]
        return cls(permissions)
    
    def __len__(self) -> int:
        return len(self.permissions)
    
    def __iter__(self):
        return iter(self.permissions)
    
    def __str__(self) -> str:
        return f"PermissionSet({', '.join(str(p) for p in self.permissions)})"

class PermissionRegistry:
    """
    Registry of common permissions used in the system.
    
    This class provides a centralized place to define and access
    commonly used permissions.
    """
    
    # Agent permissions
    AGENT_CREATE = Permission(ResourceType.AGENT, ResourceAction.CREATE)
    AGENT_READ = Permission(ResourceType.AGENT, ResourceAction.READ)
    AGENT_UPDATE = Permission(ResourceType.AGENT, ResourceAction.UPDATE)
    AGENT_DELETE = Permission(ResourceType.AGENT, ResourceAction.DELETE)
    AGENT_EXECUTE = Permission(ResourceType.AGENT, ResourceAction.EXECUTE)
    AGENT_MANAGE = Permission(ResourceType.AGENT, ResourceAction.MANAGE)
    AGENT_LIST = Permission(ResourceType.AGENT, ResourceAction.LIST)
    
    # Message permissions
    MESSAGE_CREATE = Permission(ResourceType.MESSAGE, ResourceAction.CREATE)
    MESSAGE_READ = Permission(ResourceType.MESSAGE, ResourceAction.READ)
    MESSAGE_UPDATE = Permission(ResourceType.MESSAGE, ResourceAction.UPDATE)
    MESSAGE_DELETE = Permission(ResourceType.MESSAGE, ResourceAction.DELETE)
    
    # Workflow permissions
    WORKFLOW_CREATE = Permission(ResourceType.WORKFLOW, ResourceAction.CREATE)
    WORKFLOW_READ = Permission(ResourceType.WORKFLOW, ResourceAction.READ)
    WORKFLOW_UPDATE = Permission(ResourceType.WORKFLOW, ResourceAction.UPDATE)
    WORKFLOW_DELETE = Permission(ResourceType.WORKFLOW, ResourceAction.DELETE)
    WORKFLOW_EXECUTE = Permission(ResourceType.WORKFLOW, ResourceAction.EXECUTE)
    WORKFLOW_MANAGE = Permission(ResourceType.WORKFLOW, ResourceAction.MANAGE)
    
    # Tool permissions
    TOOL_CREATE = Permission(ResourceType.TOOL, ResourceAction.CREATE)
    TOOL_READ = Permission(ResourceType.TOOL, ResourceAction.READ)
    TOOL_UPDATE = Permission(ResourceType.TOOL, ResourceAction.UPDATE)
    TOOL_DELETE = Permission(ResourceType.TOOL, ResourceAction.DELETE)
    TOOL_EXECUTE = Permission(ResourceType.TOOL, ResourceAction.EXECUTE)
    TOOL_MANAGE = Permission(ResourceType.TOOL, ResourceAction.MANAGE)
    TOOL_LIST = Permission(ResourceType.TOOL, ResourceAction.LIST)
    
    # Service permissions
    SERVICE_CREATE = Permission(ResourceType.SERVICE, ResourceAction.CREATE)
    SERVICE_READ = Permission(ResourceType.SERVICE, ResourceAction.READ)
    SERVICE_UPDATE = Permission(ResourceType.SERVICE, ResourceAction.UPDATE)
    SERVICE_DELETE = Permission(ResourceType.SERVICE, ResourceAction.DELETE)
    SERVICE_EXECUTE = Permission(ResourceType.SERVICE, ResourceAction.EXECUTE)
    SERVICE_MANAGE = Permission(ResourceType.SERVICE, ResourceAction.MANAGE)
    
    # Config permissions
    CONFIG_CREATE = Permission(ResourceType.CONFIG, ResourceAction.CREATE)
    CONFIG_READ = Permission(ResourceType.CONFIG, ResourceAction.READ)
    CONFIG_UPDATE = Permission(ResourceType.CONFIG, ResourceAction.UPDATE)
    CONFIG_DELETE = Permission(ResourceType.CONFIG, ResourceAction.DELETE)
    CONFIG_MANAGE = Permission(ResourceType.CONFIG, ResourceAction.MANAGE)
    
    # Data permissions
    DATA_CREATE = Permission(ResourceType.DATA, ResourceAction.CREATE)
    DATA_READ = Permission(ResourceType.DATA, ResourceAction.READ)
    DATA_UPDATE = Permission(ResourceType.DATA, ResourceAction.UPDATE)
    DATA_DELETE = Permission(ResourceType.DATA, ResourceAction.DELETE)
    DATA_MANAGE = Permission(ResourceType.DATA, ResourceAction.MANAGE)
    
    # System permissions
    SYSTEM_READ = Permission(ResourceType.SYSTEM, ResourceAction.READ)
    SYSTEM_UPDATE = Permission(ResourceType.SYSTEM, ResourceAction.UPDATE)
    SYSTEM_MANAGE = Permission(ResourceType.SYSTEM, ResourceAction.MANAGE)
    
    # Special permissions
    FULL_ACCESS = Permission(ResourceType.ANY, ResourceAction.ANY)
    
    # Common permission sets
    @classmethod
    def agent_full_access(cls) -> PermissionSet:
        """Get full access permissions for agents."""
        return PermissionSet([
            cls.AGENT_CREATE, cls.AGENT_READ, cls.AGENT_UPDATE,
            cls.AGENT_DELETE, cls.AGENT_EXECUTE, cls.AGENT_MANAGE,
            cls.AGENT_LIST
        ])
    
    @classmethod
    def message_full_access(cls) -> PermissionSet:
        """Get full access permissions for messages."""
        return PermissionSet([
            cls.MESSAGE_CREATE, cls.MESSAGE_READ,
            cls.MESSAGE_UPDATE, cls.MESSAGE_DELETE
        ])
    
    @classmethod
    def workflow_full_access(cls) -> PermissionSet:
        """Get full access permissions for workflows."""
        return PermissionSet([
            cls.WORKFLOW_CREATE, cls.WORKFLOW_READ, cls.WORKFLOW_UPDATE,
            cls.WORKFLOW_DELETE, cls.WORKFLOW_EXECUTE, cls.WORKFLOW_MANAGE
        ])
    
    @classmethod
    def tool_full_access(cls) -> PermissionSet:
        """Get full access permissions for tools."""
        return PermissionSet([
            cls.TOOL_CREATE, cls.TOOL_READ, cls.TOOL_UPDATE,
            cls.TOOL_DELETE, cls.TOOL_EXECUTE, cls.TOOL_MANAGE,
            cls.TOOL_LIST
        ])
    
    @classmethod
    def data_full_access(cls) -> PermissionSet:
        """Get full access permissions for data."""
        return PermissionSet([
            cls.DATA_CREATE, cls.DATA_READ, cls.DATA_UPDATE,
            cls.DATA_DELETE, cls.DATA_MANAGE
        ])
    
    @classmethod
    def system_full_access(cls) -> PermissionSet:
        """Get full access permissions for system."""
        return PermissionSet([
            cls.SYSTEM_READ, cls.SYSTEM_UPDATE, cls.SYSTEM_MANAGE
        ])
    
    @classmethod
    def admin_permissions(cls) -> PermissionSet:
        """Get administrative permissions for the system."""
        admin_perms = PermissionSet([cls.FULL_ACCESS])
        return admin_perms
    
    @classmethod
    def user_permissions(cls) -> PermissionSet:
        """Get standard user permissions."""
        user_perms = PermissionSet([
            cls.AGENT_READ, cls.AGENT_EXECUTE, cls.AGENT_LIST,
            cls.MESSAGE_CREATE, cls.MESSAGE_READ,
            cls.WORKFLOW_READ, cls.WORKFLOW_EXECUTE,
            cls.TOOL_READ, cls.TOOL_EXECUTE, cls.TOOL_LIST,
            cls.DATA_READ,
            cls.SYSTEM_READ
        ])
        return user_perms
    
    @classmethod
    def observer_permissions(cls) -> PermissionSet:
        """Get read-only observer permissions."""
        observer_perms = PermissionSet([
            cls.AGENT_READ, cls.AGENT_LIST,
            cls.MESSAGE_READ,
            cls.WORKFLOW_READ,
            cls.TOOL_READ, cls.TOOL_LIST,
            cls.DATA_READ,
            cls.SYSTEM_READ
        ])
        return observer_perms
