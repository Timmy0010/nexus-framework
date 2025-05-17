"""
Access Control List (ACL) implementation for the Nexus Framework.

This module provides classes for implementing and managing Access Control Lists,
which control fine-grained permissions for entities to access resources.
"""

import enum
import logging
import time
import json
from typing import Dict, Set, List, Optional, Any, Tuple, Union

from .permissions import Permission, PermissionSet, PermissionError, ResourceType, ResourceAction
from .roles import Role, RoleManager, RoleError

logger = logging.getLogger(__name__)

class AccessControlError(Exception):
    """Exception raised for access control related errors."""
    pass

class AccessControlEntry:
    """
    Entry in an access control list that grants or denies permissions.
    
    An ACE defines specific permissions granted to a specific entity
    for a specific resource or resource type.
    """
    
    def __init__(self, 
                entity_id: str,
                permissions: Union[PermissionSet, List[Permission]],
                resource_id: Optional[str] = None,
                resource_type: Optional[str] = None,
                created_at: Optional[float] = None,
                expires_at: Optional[float] = None,
                metadata: Optional[Dict[str, Any]] = None):
        """
        Initialize an access control entry.
        
        Args:
            entity_id: ID of the entity (user, agent, etc.) for this entry.
            permissions: Set of permissions granted by this entry.
            resource_id: Optional specific resource ID this entry applies to.
            resource_type: Optional resource type this entry applies to.
            created_at: Creation timestamp. If None, uses current time.
            expires_at: Expiration timestamp. If None, the entry doesn't expire.
            metadata: Additional metadata for the entry.
        """
        self.entity_id = entity_id
        
        # Convert list to PermissionSet if needed
        if isinstance(permissions, list):
            self.permissions = PermissionSet(permissions)
        else:
            self.permissions = permissions
            
        self.resource_id = resource_id
        self.resource_type = resource_type
        self.created_at = created_at or time.time()
        self.expires_at = expires_at
        self.metadata = metadata or {}
    
    def is_expired(self) -> bool:
        """
        Check if this entry has expired.
        
        Returns:
            True if the entry has expired, False otherwise.
        """
        if self.expires_at is None:
            return False
            
        return time.time() > self.expires_at
    
    def matches_resource(self, 
                        resource_type: Optional[str] = None,
                        resource_id: Optional[str] = None) -> bool:
        """
        Check if this entry applies to a specific resource.
        
        Args:
            resource_type: The resource type to check.
            resource_id: The resource ID to check.
            
        Returns:
            True if this entry applies to the resource, False otherwise.
        """
        # If this entry doesn't specify a resource type, it applies to all types
        if self.resource_type is None:
            # If this entry doesn't specify a resource ID, it applies to all IDs
            if self.resource_id is None:
                return True
            # Otherwise, check resource ID
            else:
                return resource_id is not None and resource_id == self.resource_id
        # Otherwise, check if the resource type matches
        elif resource_type is not None and resource_type == self.resource_type:
            # If this entry doesn't specify a resource ID, it applies to all IDs of this type
            if self.resource_id is None:
                return True
            # Otherwise, check resource ID
            else:
                return resource_id is not None and resource_id == self.resource_id
        
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the entry to a dictionary.
        
        Returns:
            Dictionary representation of the entry.
        """
        return {
            "entity_id": self.entity_id,
            "permissions": self.permissions.to_string_list(),
            "resource_id": self.resource_id,
            "resource_type": self.resource_type,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AccessControlEntry':
        """
        Create an entry from a dictionary.
        
        Args:
            data: Dictionary representation of an entry.
            
        Returns:
            A new access control entry.
        """
        permissions = PermissionSet.from_string_list(data.get("permissions", []))
        
        return cls(
            entity_id=data["entity_id"],
            permissions=permissions,
            resource_id=data.get("resource_id"),
            resource_type=data.get("resource_type"),
            created_at=data.get("created_at"),
            expires_at=data.get("expires_at"),
            metadata=data.get("metadata", {})
        )
    
    def __str__(self) -> str:
        resource_str = ""
        if self.resource_type:
            resource_str += self.resource_type
            if self.resource_id:
                resource_str += f":{self.resource_id}"
        else:
            resource_str = "*"
            
        return f"ACE({self.entity_id}, {resource_str}, {len(self.permissions)} permissions)"

class AccessControlList:
    """
    List of access control entries that define permissions for resources.
    
    An ACL contains multiple ACEs that collectively define the access control
    policy for one or more resources.
    """
    
    def __init__(self, entries: Optional[List[AccessControlEntry]] = None):
        """
        Initialize an access control list.
        
        Args:
            entries: Initial list of access control entries.
        """
        self.entries = entries or []
    
    def add_entry(self, entry: AccessControlEntry) -> None:
        """
        Add an entry to the ACL.
        
        Args:
            entry: The entry to add.
        """
        self.entries.append(entry)
    
    def remove_entry(self, 
                    entity_id: str,
                    resource_type: Optional[str] = None,
                    resource_id: Optional[str] = None) -> None:
        """
        Remove entries matching the given criteria.
        
        Args:
            entity_id: The entity ID to match.
            resource_type: Optional resource type to match.
            resource_id: Optional resource ID to match.
            
        Raises:
            AccessControlError: If no matching entries are found.
        """
        matching_indices = []
        
        for i, entry in enumerate(self.entries):
            if entry.entity_id == entity_id:
                if (resource_type is None or entry.resource_type == resource_type) and \
                   (resource_id is None or entry.resource_id == resource_id):
                    matching_indices.append(i)
        
        if not matching_indices:
            raise AccessControlError(f"No matching entries found for entity {entity_id}")
        
        # Remove entries in reverse order to preserve indices
        for i in sorted(matching_indices, reverse=True):
            del self.entries[i]
    
    def get_entries(self, 
                   entity_id: Optional[str] = None,
                   resource_type: Optional[str] = None,
                   resource_id: Optional[str] = None) -> List[AccessControlEntry]:
        """
        Get entries matching the given criteria.
        
        Args:
            entity_id: Optional entity ID to match.
            resource_type: Optional resource type to match.
            resource_id: Optional resource ID to match.
            
        Returns:
            List of matching entries.
        """
        result = []
        
        for entry in self.entries:
            if (entity_id is None or entry.entity_id == entity_id) and \
               entry.matches_resource(resource_type, resource_id) and \
               not entry.is_expired():
                result.append(entry)
                
        return result
    
    def check_permission(self, 
                        entity_id: str,
                        permission: Permission,
                        resource_id: Optional[str] = None) -> bool:
        """
        Check if an entity has a specific permission.
        
        Args:
            entity_id: The entity ID to check.
            permission: The permission to check.
            resource_id: Optional specific resource ID to check.
            
        Returns:
            True if the entity has the permission, False otherwise.
        """
        # Get relevant entries for this entity and resource
        resource_type = permission.resource_type.value
        entries = self.get_entries(entity_id, resource_type, resource_id)
        
        # If no entries found, the entity doesn't have the permission
        if not entries:
            return False
        
        # Check each entry
        for entry in entries:
            if entry.permissions.has_permission(permission):
                return True
                
        return False
    
    def get_permissions(self, 
                       entity_id: str,
                       resource_type: Optional[str] = None,
                       resource_id: Optional[str] = None) -> PermissionSet:
        """
        Get all permissions for an entity on a resource.
        
        Args:
            entity_id: The entity ID to get permissions for.
            resource_type: Optional resource type to filter by.
            resource_id: Optional resource ID to filter by.
            
        Returns:
            Set of all permissions the entity has.
        """
        entries = self.get_entries(entity_id, resource_type, resource_id)
        
        # Start with an empty permission set
        result = PermissionSet()
        
        # Merge permissions from all entries
        for entry in entries:
            result = result.merge(entry.permissions)
            
        return result
    
    def purge_expired_entries(self) -> int:
        """
        Remove all expired entries from the ACL.
        
        Returns:
            Number of entries removed.
        """
        expired_indices = []
        
        for i, entry in enumerate(self.entries):
            if entry.is_expired():
                expired_indices.append(i)
        
        # Remove entries in reverse order to preserve indices
        for i in sorted(expired_indices, reverse=True):
            del self.entries[i]
            
        return len(expired_indices)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the ACL to a dictionary.
        
        Returns:
            Dictionary representation of the ACL.
        """
        return {
            "entries": [entry.to_dict() for entry in self.entries]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AccessControlList':
        """
        Create an ACL from a dictionary.
        
        Args:
            data: Dictionary representation of an ACL.
            
        Returns:
            A new access control list.
        """
        entries = [
            AccessControlEntry.from_dict(entry_data)
            for entry_data in data.get("entries", [])
        ]
        return cls(entries)
    
    def __len__(self) -> int:
        return len(self.entries)
    
    def __str__(self) -> str:
        return f"ACL({len(self.entries)} entries)"

class ACLManager:
    """
    Manager for ACLs that provides a higher-level API for access control.
    
    This class manages access control lists for different resources
    and provides methods for checking and granting permissions.
    """
    
    def __init__(self, role_manager: Optional[RoleManager] = None):
        """
        Initialize the ACL manager.
        
        Args:
            role_manager: Optional role manager for role-based access control.
        """
        # Map of resource type -> resource ID -> ACL
        self.acls: Dict[str, Dict[str, AccessControlList]] = {}
        
        # Global ACL for permissions that apply to all resources
        self.global_acl = AccessControlList()
        
        # Role manager for role-based access control
        self.role_manager = role_manager
    
    def get_acl(self, 
               resource_type: str,
               resource_id: Optional[str] = None) -> AccessControlList:
        """
        Get the ACL for a specific resource.
        
        Args:
            resource_type: The resource type.
            resource_id: Optional resource ID. If None, gets the ACL for the resource type.
            
        Returns:
            The ACL for the resource.
        """
        # Ensure resource type exists
        if resource_type not in self.acls:
            self.acls[resource_type] = {}
        
        # If no resource ID, get the ACL for the resource type
        if resource_id is None:
            if "" not in self.acls[resource_type]:
                self.acls[resource_type][""] = AccessControlList()
            return self.acls[resource_type][""]
        
        # Otherwise, get the ACL for the specific resource
        if resource_id not in self.acls[resource_type]:
            self.acls[resource_type][resource_id] = AccessControlList()
            
        return self.acls[resource_type][resource_id]
    
    def grant_permission(self, 
                        entity_id: str,
                        permission: Permission,
                        resource_id: Optional[str] = None,
                        expires_in: Optional[float] = None) -> None:
        """
        Grant a permission to an entity.
        
        Args:
            entity_id: The entity ID to grant the permission to.
            permission: The permission to grant.
            resource_id: Optional specific resource ID to grant the permission for.
                       If None, grants the permission for all resources of this type.
            expires_in: Optional expiration time in seconds from now.
                      If None, the permission doesn't expire.
        """
        resource_type = permission.resource_type.value
        
        # If the permission has a specific instance, use that as the resource ID
        if permission.instance != "*":
            resource_id = permission.instance
        
        # Calculate expiration time if needed
        expires_at = None
        if expires_in is not None:
            expires_at = time.time() + expires_in
        
        # Create a permission set with this permission
        permission_set = PermissionSet([permission])
        
        # Create an ACL entry
        entry = AccessControlEntry(
            entity_id=entity_id,
            permissions=permission_set,
            resource_type=resource_type,
            resource_id=resource_id,
            expires_at=expires_at
        )
        
        # Get the appropriate ACL and add the entry
        acl = self.get_acl(resource_type, resource_id)
        acl.add_entry(entry)
    
    def revoke_permission(self, 
                         entity_id: str,
                         permission: Permission,
                         resource_id: Optional[str] = None) -> None:
        """
        Revoke a permission from an entity.
        
        Args:
            entity_id: The entity ID to revoke the permission from.
            permission: The permission to revoke.
            resource_id: Optional specific resource ID to revoke the permission for.
                       If None, revokes the permission for all resources of this type.
        """
        resource_type = permission.resource_type.value
        
        # If the permission has a specific instance, use that as the resource ID
        if permission.instance != "*":
            resource_id = permission.instance
        
        # Get the appropriate ACL
        acl = self.get_acl(resource_type, resource_id)
        
        # Get all entries for this entity and resource
        entries = acl.get_entries(entity_id, resource_type, resource_id)
        
        # For each entry, remove this permission
        for entry in entries:
            try:
                entry.permissions.remove(permission)
            except PermissionError:
                # Permission not in this entry, skip
                pass
    
    def grant_permission_set(self, 
                           entity_id: str,
                           permissions: PermissionSet,
                           resource_type: str,
                           resource_id: Optional[str] = None,
                           expires_in: Optional[float] = None) -> None:
        """
        Grant a set of permissions to an entity.
        
        Args:
            entity_id: The entity ID to grant permissions to.
            permissions: The permission set to grant.
            resource_type: The resource type.
            resource_id: Optional resource ID. If None, grants permissions for all resources of this type.
            expires_in: Optional expiration time in seconds from now.
        """
        # Calculate expiration time if needed
        expires_at = None
        if expires_in is not None:
            expires_at = time.time() + expires_in
        
        # Create an ACL entry
        entry = AccessControlEntry(
            entity_id=entity_id,
            permissions=permissions,
            resource_type=resource_type,
            resource_id=resource_id,
            expires_at=expires_at
        )
        
        # Get the appropriate ACL and add the entry
        acl = self.get_acl(resource_type, resource_id)
        acl.add_entry(entry)
    
    def has_permission(self, 
                      entity_id: str,
                      permission: Permission,
                      resource_id: Optional[str] = None) -> bool:
        """
        Check if an entity has a specific permission.
        
        This method checks both ACLs and roles if a role manager is available.
        
        Args:
            entity_id: The entity ID to check.
            permission: The permission to check.
            resource_id: Optional specific resource ID to check.
            
        Returns:
            True if the entity has the permission, False otherwise.
        """
        # Check role-based permissions first
        if self.role_manager:
            if self.role_manager.has_permission(entity_id, permission):
                return True
        
        # Get resource type from permission
        resource_type = permission.resource_type.value
        
        # If the permission has a specific instance, use that as the resource ID
        if permission.instance != "*" and resource_id is None:
            resource_id = permission.instance
        
        # Check global ACL first
        if self.global_acl.check_permission(entity_id, permission, resource_id):
            return True
        
        # Check resource type ACL
        type_acl = self.get_acl(resource_type)
        if type_acl.check_permission(entity_id, permission, resource_id):
            return True
        
        # Check resource instance ACL if resource ID is provided
        if resource_id is not None:
            instance_acl = self.get_acl(resource_type, resource_id)
            if instance_acl.check_permission(entity_id, permission, resource_id):
                return True
        
        return False
    
    def get_permissions(self, 
                       entity_id: str,
                       resource_type: Optional[str] = None,
                       resource_id: Optional[str] = None) -> PermissionSet:
        """
        Get all permissions for an entity on a resource.
        
        This method combines permissions from both ACLs and roles.
        
        Args:
            entity_id: The entity ID to get permissions for.
            resource_type: Optional resource type to filter by.
            resource_id: Optional resource ID to filter by.
            
        Returns:
            Set of all permissions the entity has.
        """
        # Start with an empty permission set
        result = PermissionSet()
        
        # Add role-based permissions if available
        if self.role_manager:
            role_permissions = self.role_manager.get_entity_permissions(entity_id)
            result = result.merge(role_permissions)
        
        # Add permissions from global ACL
        global_permissions = self.global_acl.get_permissions(entity_id, resource_type, resource_id)
        result = result.merge(global_permissions)
        
        # Add permissions from resource type ACL if resource type is provided
        if resource_type is not None:
            type_acl = self.get_acl(resource_type)
            type_permissions = type_acl.get_permissions(entity_id, resource_type, resource_id)
            result = result.merge(type_permissions)
            
            # Add permissions from resource instance ACL if resource ID is provided
            if resource_id is not None:
                instance_acl = self.get_acl(resource_type, resource_id)
                instance_permissions = instance_acl.get_permissions(entity_id, resource_type, resource_id)
                result = result.merge(instance_permissions)
        
        return result
    
    def purge_expired_entries(self) -> int:
        """
        Remove all expired entries from all ACLs.
        
        Returns:
            Total number of entries removed.
        """
        total_removed = 0
        
        # Purge global ACL
        total_removed += self.global_acl.purge_expired_entries()
        
        # Purge resource type and instance ACLs
        for resource_type, resource_acls in self.acls.items():
            for resource_id, acl in resource_acls.items():
                total_removed += acl.purge_expired_entries()
        
        return total_removed
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the ACL manager to a dictionary.
        
        Returns:
            Dictionary representation of the ACL manager.
        """
        return {
            "global_acl": self.global_acl.to_dict(),
            "resource_acls": {
                resource_type: {
                    resource_id: acl.to_dict()
                    for resource_id, acl in resource_acls.items()
                }
                for resource_type, resource_acls in self.acls.items()
            }
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], role_manager: Optional[RoleManager] = None) -> 'ACLManager':
        """
        Create an ACL manager from a dictionary.
        
        Args:
            data: Dictionary representation of an ACL manager.
            role_manager: Optional role manager for role-based access control.
            
        Returns:
            A new ACL manager.
        """
        manager = cls(role_manager)
        
        # Load global ACL
        if "global_acl" in data:
            manager.global_acl = AccessControlList.from_dict(data["global_acl"])
        
        # Load resource ACLs
        for resource_type, resource_acls in data.get("resource_acls", {}).items():
            manager.acls[resource_type] = {}
            
            for resource_id, acl_data in resource_acls.items():
                manager.acls[resource_type][resource_id] = AccessControlList.from_dict(acl_data)
        
        return manager
    
    def save_to_file(self, file_path: str) -> None:
        """
        Save the ACL manager to a JSON file.
        
        Args:
            file_path: Path to the JSON file.
            
        Raises:
            AccessControlError: If the file cannot be saved.
        """
        try:
            with open(file_path, 'w') as f:
                json.dump(self.to_dict(), f, indent=2)
        except Exception as e:
            raise AccessControlError(f"Failed to save ACLs to {file_path}: {e}")
    
    def load_from_file(self, file_path: str) -> None:
        """
        Load the ACL manager from a JSON file.
        
        Args:
            file_path: Path to the JSON file.
            
        Raises:
            AccessControlError: If the file cannot be loaded.
        """
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                
            # Load global ACL
            if "global_acl" in data:
                self.global_acl = AccessControlList.from_dict(data["global_acl"])
            
            # Load resource ACLs
            for resource_type, resource_acls in data.get("resource_acls", {}).items():
                self.acls[resource_type] = {}
                
                for resource_id, acl_data in resource_acls.items():
                    self.acls[resource_type][resource_id] = AccessControlList.from_dict(acl_data)
        except Exception as e:
            raise AccessControlError(f"Failed to load ACLs from {file_path}: {e}")
