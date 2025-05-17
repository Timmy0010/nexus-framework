"""
Security package for the Nexus Framework.

This package provides security-related components such as the VerificationAgent,
authentication, access control, validation rules, and sanitization rules for 
ensuring message security.
"""

from .verification_agent import VerificationAgent, ValidationRule, SanitizationRule, ValidationResult
from .validation_rules import (
    SchemaValidator,
    SizeValidator,
    ContentValidator,
    PermissionValidator,
    RateLimitValidator
)
from .sanitization_rules import (
    SizeLimitSanitizer,
    ContentFilterSanitizer,
    JsonSanitizer,
    RecursiveDepthSanitizer
)

# Import authentication components
from .authentication import (
    KeyManager,
    MessageSigner,
    JWTManager,
    AuthenticationService,
    AuthMiddleware,
    JWTAuthMiddleware,
    AuthenticationProcessor,
    AuthenticatedCommunicationBus,
    KeyRotationManager,
    create_authenticated_bus,
    
    # Exceptions
    AuthenticationError,
    SignatureError,
    SigningKeyError,
    KeyRotationError
)

# Import access control components
from .access_control import (
    # Permissions
    Permission,
    PermissionSet,
    ResourceType,
    ResourceAction,
    PermissionRegistry,
    
    # Roles
    Role,
    RoleManager,
    RoleRegistry,
    SystemRoles,
    
    # Policies
    Policy,
    PolicySet,
    PolicyEngine,
    PolicyManager,
    EffectType,
    PolicyContext,
    
    # ACLs
    AccessControlList,
    ACLManager,
    AccessControlEntry,
    
    # Middleware
    AccessControlMiddleware,
    AccessControlProcessor,
    
    # Integration
    AccessControlService,
    SecureCommunicationBus,
    AccessControlManager,
    create_secure_bus,
    
    # Exceptions
    PermissionError,
    RoleError,
    PolicyError,
    AccessControlError
)

__all__ = [
    # Main classes
    'VerificationAgent',
    'ValidationRule',
    'SanitizationRule',
    'ValidationResult',
    
    # Validators
    'SchemaValidator',
    'SizeValidator',
    'ContentValidator',
    'PermissionValidator',
    'RateLimitValidator',
    
    # Sanitizers
    'SizeLimitSanitizer', 
    'ContentFilterSanitizer',
    'JsonSanitizer',
    'RecursiveDepthSanitizer',
    
    # Authentication
    'KeyManager',
    'MessageSigner',
    'JWTManager',
    'AuthenticationService',
    'AuthMiddleware',
    'JWTAuthMiddleware',
    'AuthenticationProcessor',
    'AuthenticatedCommunicationBus',
    'KeyRotationManager',
    'create_authenticated_bus',
    'AuthenticationError',
    'SignatureError',
    'SigningKeyError',
    'KeyRotationError',
    
    # Access Control
    'Permission',
    'PermissionSet',
    'ResourceType',
    'ResourceAction',
    'PermissionRegistry',
    'Role',
    'RoleManager',
    'RoleRegistry',
    'SystemRoles',
    'Policy',
    'PolicySet',
    'PolicyEngine',
    'PolicyManager',
    'EffectType',
    'PolicyContext',
    'AccessControlList',
    'ACLManager',
    'AccessControlEntry',
    'AccessControlMiddleware',
    'AccessControlProcessor',
    'AccessControlService',
    'SecureCommunicationBus',
    'AccessControlManager',
    'create_secure_bus',
    'PermissionError',
    'RoleError',
    'PolicyError',
    'AccessControlError'
]
