"""
Access Control package for the Nexus Framework.

This package provides functionality for authorization and access control,
building on top of the authentication system.
"""

from .permissions import (
    Permission,
    PermissionSet, 
    ResourceAction,
    ResourceType,
    PermissionRegistry,
    PermissionError
)

from .roles import (
    Role,
    RoleManager,
    RoleError,
    RoleRegistry,
    SystemRoles
)

from .policies import (
    Policy,
    PolicySet,
    PolicyEngine,
    PolicyManager,
    PolicyError,
    EffectType,
    PolicyContext
)

from .acl import (
    AccessControlList,
    ACLManager,
    AccessControlError,
    AccessControlEntry
)

from .middleware import (
    AccessControlMiddleware,
    AccessControlProcessor
)

from .integration import (
    AccessControlService,
    SecureCommunicationBus,
    create_secure_bus,
    AccessControlManager
)

__all__ = [
    # Permissions
    'Permission',
    'PermissionSet',
    'ResourceAction',
    'ResourceType',
    'PermissionRegistry',
    'PermissionError',
    
    # Roles
    'Role',
    'RoleManager',
    'RoleError',
    'RoleRegistry',
    'SystemRoles',
    
    # Policies
    'Policy',
    'PolicySet',
    'PolicyEngine',
    'PolicyManager',
    'PolicyError',
    'EffectType',
    'PolicyContext',
    
    # ACLs
    'AccessControlList',
    'ACLManager',
    'AccessControlError',
    'AccessControlEntry',
    
    # Middleware
    'AccessControlMiddleware',
    'AccessControlProcessor',
    
    # Integration
    'AccessControlService',
    'SecureCommunicationBus',
    'create_secure_bus',
    'AccessControlManager'
]
