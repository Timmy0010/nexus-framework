"""
Role definitions and management for the Nexus Framework's access control system.

This module provides classes for defining and managing roles, which are
collections of permissions assigned to users or agents.
"""

import enum
import logging
from typing import Dict, Set, List, Optional, Any, Tuple, FrozenSet
from .permissions import Permission, PermissionSet, PermissionRegistry, PermissionError

logger = logging.getLogger(__name__)

class RoleError(Exception):
    """Exception raised for role-related errors."""
    pass

class Role:
    """
    Represents a role in the system, which is a named collection of permissions.
    
    Roles can inherit from other roles to build permission hierarchies.
    """
    
    def __init__(self, name: str, description: str = "", 
                permissions: Optional[PermissionSet] = None,
                parent_roles: Optional[List[str]] = None):
        """
        Initialize a role.
        
        Args:
            name: Unique role name.
            description: Role description.
            permissions: Set of permissions directly assigned to this role.
            parent_roles: List of parent role names this role inherits from.
        """
        self.name = name
        self.description = description
        self.permissions = permissions or PermissionSet()
        self.parent_roles = parent_roles or []
    
    def add_permission(self, permission: Permission) -> None:
        """
        Add a permission to this role.
        
        Args:
            permission: The permission to add.
        """
        self.permissions.add(permission)
    
    def remove_permission(self, permission: Permission) -> None:
        """
        Remove a permission from this role.
        
        Args:
            permission: The permission to remove.
            
        Raises:
            PermissionError: If the permission is not in the role.
        """
        self.permissions.remove(permission)
    
    def add_parent_role(self, role_name: str) -> None:
        """
        Add a parent role to inherit permissions from.
        
        Args:
            role_name: Name of the parent role.
        """
        if role_name not in self.parent_roles:
            self.parent_roles.append(role_name)
    
    def remove_parent_role(self, role_name: str) -> None:
        """
        Remove a parent role.
        
        Args:
            role_name: Name of the parent role to remove.
            
        Raises:
            RoleError: If the parent role is not found.
        """
        if role_name not in self.parent_roles:
            raise RoleError(f"Parent role '{role_name}' not found")
        
        self.parent_roles.remove(role_name)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the role to a dictionary.
        
        Returns:
            Dictionary representation of the role.
        """
        return {
            "name": self.name,
            "description": self.description,
            "permissions": self.permissions.to_string_list(),
            "parent_roles": self.parent_roles
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Role':
        """
        Create a role from a dictionary.
        
        Args:
            data: Dictionary representation of a role.
            
        Returns:
            A new role.
        """
        permissions = PermissionSet.from_string_list(data.get("permissions", []))
        
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            permissions=permissions,
            parent_roles=data.get("parent_roles", [])
        )
    
    def __str__(self) -> str:
        return f"Role({self.name})"

class SystemRoles(enum.Enum):
    """Enum defining standard system roles."""
    ADMIN = "admin"
    USER = "user"
    OBSERVER = "observer"
    AGENT = "agent"
    TOOL = "tool"
    SERVICE = "service"
    SYSTEM = "system"

class RoleRegistry:
    """
    Registry of standard system roles.
    
    This class provides factory methods for creating common roles.
    """
    
    @classmethod
    def create_admin_role(cls) -> Role:
        """
        Create the administrator role.
        
        Returns:
            Admin role with full system access.
        """
        return Role(
            name=SystemRoles.ADMIN.value,
            description="Administrator with full system access",
            permissions=PermissionRegistry.admin_permissions()
        )
    
    @classmethod
    def create_user_role(cls) -> Role:
        """
        Create the standard user role.
        
        Returns:
            User role with standard permissions.
        """
        return Role(
            name=SystemRoles.USER.value,
            description="Standard user with normal access",
            permissions=PermissionRegistry.user_permissions()
        )
    
    @classmethod
    def create_observer_role(cls) -> Role:
        """
        Create the observer role.
        
        Returns:
            Observer role with read-only access.
        """
        return Role(
            name=SystemRoles.OBSERVER.value,
            description="Observer with read-only access",
            permissions=PermissionRegistry.observer_permissions()
        )
    
    @classmethod
    def create_agent_role(cls) -> Role:
        """
        Create the standard agent role.
        
        Returns:
            Agent role with permissions for agent operations.
        """
        agent_perms = PermissionSet([
            PermissionRegistry.MESSAGE_CREATE,
            PermissionRegistry.MESSAGE_READ,
            PermissionRegistry.TOOL_EXECUTE,
            PermissionRegistry.TOOL_READ,
            PermissionRegistry.AGENT_READ,
            PermissionRegistry.WORKFLOW_READ,
            PermissionRegistry.DATA_READ
        ])
        
        return Role(
            name=SystemRoles.AGENT.value,
            description="Standard agent with limited permissions",
            permissions=agent_perms
        )
    
    @classmethod
    def create_tool_role(cls) -> Role:
        """
        Create the standard tool role.
        
        Returns:
            Tool role with permissions for tool operations.
        """
        tool_perms = PermissionSet([
            PermissionRegistry.DATA_READ,
            PermissionRegistry.DATA_CREATE,
            PermissionRegistry.MESSAGE_READ
        ])
        
        return Role(
            name=SystemRoles.TOOL.value,
            description="Standard tool with limited permissions",
            permissions=tool_perms
        )
    
    @classmethod
    def create_service_role(cls) -> Role:
        """
        Create the standard service role.
        
        Returns:
            Service role with permissions for service operations.
        """
        service_perms = PermissionSet([
            PermissionRegistry.AGENT_READ,
            PermissionRegistry.AGENT_LIST,
            PermissionRegistry.MESSAGE_READ,
            PermissionRegistry.MESSAGE_CREATE,
            PermissionRegistry.WORKFLOW_READ,
            PermissionRegistry.TOOL_READ,
            PermissionRegistry.TOOL_LIST,
            PermissionRegistry.DATA_READ
        ])
        
        return Role(
            name=SystemRoles.SERVICE.value,
            description="Standard service with elevated permissions",
            permissions=service_perms
        )
    
    @classmethod
    def create_system_role(cls) -> Role:
        """
        Create the system role.
        
        Returns:
            System role with permissions for system operations.
        """
        return Role(
            name=SystemRoles.SYSTEM.value,
            description="System processes with elevated permissions",
            permissions=PermissionRegistry.system_full_access()
        )
    
    @classmethod
    def create_all_default_roles(cls) -> Dict[str, Role]:
        """
        Create all default system roles.
        
        Returns:
            Dictionary mapping role names to role objects.
        """
        return {
            SystemRoles.ADMIN.value: cls.create_admin_role(),
            SystemRoles.USER.value: cls.create_user_role(),
            SystemRoles.OBSERVER.value: cls.create_observer_role(),
            SystemRoles.AGENT.value: cls.create_agent_role(),
            SystemRoles.TOOL.value: cls.create_tool_role(),
            SystemRoles.SERVICE.value: cls.create_service_role(),
            SystemRoles.SYSTEM.value: cls.create_system_role()
        }

class RoleManager:
    """
    Manages roles and their assignments.
    
    This class provides functionality for creating, updating, and deleting roles,
    as well as managing role assignments to users or agents.
    """
    
    def __init__(self):
        """Initialize the role manager with empty roles and assignments."""
        # Map of role name -> Role object
        self.roles: Dict[str, Role] = {}
        
        # Map of entity ID -> list of assigned role names
        self.role_assignments: Dict[str, List[str]] = {}
        
        # Add default system roles
        self._add_default_roles()
    
    def _add_default_roles(self) -> None:
        """Add default system roles to the manager."""
        default_roles = RoleRegistry.create_all_default_roles()
        for role in default_roles.values():
            self.add_role(role)
    
    def add_role(self, role: Role) -> None:
        """
        Add a role to the manager.
        
        Args:
            role: The role to add.
            
        Raises:
            RoleError: If a role with the same name already exists.
        """
        if role.name in self.roles:
            raise RoleError(f"Role '{role.name}' already exists")
        
        self.roles[role.name] = role
    
    def get_role(self, role_name: str) -> Role:
        """
        Get a role by name.
        
        Args:
            role_name: Name of the role to get.
            
        Returns:
            The role.
            
        Raises:
            RoleError: If the role is not found.
        """
        if role_name not in self.roles:
            raise RoleError(f"Role '{role_name}' not found")
        
        return self.roles[role_name]
    
    def update_role(self, role: Role) -> None:
        """
        Update an existing role.
        
        Args:
            role: The updated role.
            
        Raises:
            RoleError: If the role is not found.
        """
        if role.name not in self.roles:
            raise RoleError(f"Role '{role.name}' not found")
        
        self.roles[role.name] = role
    
    def delete_role(self, role_name: str) -> None:
        """
        Delete a role.
        
        Args:
            role_name: Name of the role to delete.
            
        Raises:
            RoleError: If the role is not found or is a system role.
        """
        # Check if role exists
        if role_name not in self.roles:
            raise RoleError(f"Role '{role_name}' not found")
        
        # Check if it's a system role
        if role_name in [r.value for r in SystemRoles]:
            raise RoleError(f"Cannot delete system role '{role_name}'")
        
        # Check if the role is used in parent_roles by other roles
        for r_name, r in self.roles.items():
            if role_name in r.parent_roles:
                raise RoleError(f"Cannot delete role '{role_name}' because it is a parent of '{r_name}'")
        
        # Check if the role is assigned to any entity
        for entity_id, roles in self.role_assignments.items():
            if role_name in roles:
                raise RoleError(f"Cannot delete role '{role_name}' because it is assigned to entity '{entity_id}'")
        
        # Delete the role
        del self.roles[role_name]
    
    def assign_role(self, entity_id: str, role_name: str) -> None:
        """
        Assign a role to an entity.
        
        Args:
            entity_id: ID of the entity (user, agent, etc.).
            role_name: Name of the role to assign.
            
        Raises:
            RoleError: If the role is not found.
        """
        # Check if role exists
        if role_name not in self.roles:
            raise RoleError(f"Role '{role_name}' not found")
        
        # Initialize empty list if entity doesn't have any roles yet
        if entity_id not in self.role_assignments:
            self.role_assignments[entity_id] = []
        
        # Add role if not already assigned
        if role_name not in self.role_assignments[entity_id]:
            self.role_assignments[entity_id].append(role_name)
            logger.info(f"Assigned role '{role_name}' to entity '{entity_id}'")
    
    def revoke_role(self, entity_id: str, role_name: str) -> None:
        """
        Revoke a role from an entity.
        
        Args:
            entity_id: ID of the entity.
            role_name: Name of the role to revoke.
            
        Raises:
            RoleError: If the entity or role assignment is not found.
        """
        # Check if entity has any roles
        if entity_id not in self.role_assignments:
            raise RoleError(f"Entity '{entity_id}' has no role assignments")
        
        # Check if entity has the role
        if role_name not in self.role_assignments[entity_id]:
            raise RoleError(f"Entity '{entity_id}' does not have role '{role_name}'")
        
        # Remove the role
        self.role_assignments[entity_id].remove(role_name)
        logger.info(f"Revoked role '{role_name}' from entity '{entity_id}'")
        
        # Clean up empty assignments
        if not self.role_assignments[entity_id]:
            del self.role_assignments[entity_id]
    
    def get_entity_roles(self, entity_id: str) -> List[str]:
        """
        Get all roles assigned to an entity.
        
        Args:
            entity_id: ID of the entity.
            
        Returns:
            List of role names assigned to the entity.
        """
        return self.role_assignments.get(entity_id, [])
    
    def get_entity_permissions(self, entity_id: str) -> PermissionSet:
        """
        Get all permissions granted to an entity through roles.
        
        This method computes the effective permissions by combining
        all permissions from assigned roles, including those inherited
        from parent roles.
        
        Args:
            entity_id: ID of the entity.
            
        Returns:
            Set of all permissions granted to the entity.
        """
        # Get roles assigned to the entity
        role_names = self.get_entity_roles(entity_id)
        
        # Start with an empty permission set
        all_permissions = PermissionSet()
        
        # Process all roles
        processed_roles = set()
        roles_to_process = list(role_names)
        
        while roles_to_process:
            role_name = roles_to_process.pop(0)
            
            # Skip if already processed to avoid circular dependencies
            if role_name in processed_roles:
                continue
                
            processed_roles.add(role_name)
            
            # Get the role
            try:
                role = self.get_role(role_name)
            except RoleError:
                logger.warning(f"Role '{role_name}' not found, skipping")
                continue
            
            # Add direct permissions
            all_permissions = all_permissions.merge(role.permissions)
            
            # Add parent roles to processing queue
            for parent_name in role.parent_roles:
                if parent_name not in processed_roles:
                    roles_to_process.append(parent_name)
        
        return all_permissions
    
    def has_permission(self, entity_id: str, permission: Permission) -> bool:
        """
        Check if an entity has a specific permission.
        
        Args:
            entity_id: ID of the entity.
            permission: The permission to check.
            
        Returns:
            True if the entity has the permission, False otherwise.
        """
        # Get all permissions for the entity
        permissions = self.get_entity_permissions(entity_id)
        
        # Check if the permission is granted
        return permissions.has_permission(permission)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the role manager to a dictionary.
        
        Returns:
            Dictionary representation of the role manager.
        """
        return {
            "roles": {name: role.to_dict() for name, role in self.roles.items()},
            "role_assignments": self.role_assignments
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RoleManager':
        """
        Create a role manager from a dictionary.
        
        Args:
            data: Dictionary representation of a role manager.
            
        Returns:
            A new role manager.
        """
        manager = cls()
        
        # Clear default roles
        manager.roles = {}
        manager.role_assignments = {}
        
        # Add roles from data
        for role_data in data.get("roles", {}).values():
            role = Role.from_dict(role_data)
            manager.roles[role.name] = role
        
        # Add role assignments from data
        manager.role_assignments = data.get("role_assignments", {})
        
        return manager
