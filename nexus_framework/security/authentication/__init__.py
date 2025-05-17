"""
Authentication package for the Nexus Framework.

This package provides functionality for message authentication and authorization.
"""

from .auth_service import (
    KeyManager,
    MessageSigner,
    JWTManager,
    AuthenticationService,
    AuthenticationError,
    SignatureError,
    SigningKeyError,
    KeyRotationError
)

from .auth_middleware import (
    AuthMiddleware,
    JWTAuthMiddleware,
    AuthenticationProcessor
)

from .bus_integration import (
    AuthenticatedCommunicationBus,
    KeyRotationManager,
    create_authenticated_bus
)

__all__ = [
    # Services
    'KeyManager',
    'MessageSigner',
    'JWTManager',
    'AuthenticationService',
    
    # Middleware
    'AuthMiddleware',
    'JWTAuthMiddleware',
    'AuthenticationProcessor',
    
    # Bus Integration
    'AuthenticatedCommunicationBus',
    'KeyRotationManager',
    'create_authenticated_bus',
    
    # Exceptions
    'AuthenticationError',
    'SignatureError',
    'SigningKeyError',
    'KeyRotationError'
]
