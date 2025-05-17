"""
Authentication service for message signing and verification.

This module provides the core functionality for signing and verifying messages
in the Nexus Framework using HMAC or JWT-based approaches.
"""

import hmac
import hashlib
import json
import time
import logging
import uuid
import base64
from typing import Dict, Any, Optional, Tuple, List, Union
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class SigningKeyError(Exception):
    """Exception raised for errors with signing keys."""
    pass

class SignatureError(Exception):
    """Exception raised for errors during signature creation or verification."""
    pass

class AuthenticationError(Exception):
    """Exception raised when message authentication fails."""
    pass

class KeyRotationError(Exception):
    """Exception raised for errors during key rotation."""
    pass

class KeyManager:
    """
    Manages cryptographic keys for signing and verifying messages.
    
    This class handles key storage, retrieval, and rotation.
    """
    
    def __init__(self, 
                initial_key: Optional[str] = None,
                key_id: Optional[str] = None,
                rotation_interval_days: int = 30):
        """
        Initialize the key manager.
        
        Args:
            initial_key: Initial signing key. If None, a random key is generated.
            key_id: ID for the initial key. If None, a random ID is generated.
            rotation_interval_days: How often keys should be rotated (in days).
        """
        self.rotation_interval_days = rotation_interval_days
        
        # Format: {key_id: {"key": key_value, "created_at": timestamp, "expires_at": timestamp}}
        self.keys: Dict[str, Dict[str, Any]] = {}
        
        # Add initial key
        if initial_key is None:
            initial_key = self._generate_key()
            
        if key_id is None:
            key_id = str(uuid.uuid4())
            
        now = time.time()
        expiration = now + (rotation_interval_days * 24 * 60 * 60)
        
        self.keys[key_id] = {
            "key": initial_key,
            "created_at": now,
            "expires_at": expiration,
            "active": True
        }
        
        self.current_key_id = key_id
    
    def _generate_key(self, length: int = 32) -> str:
        """
        Generate a random key.
        
        Args:
            length: Length of the key in bytes.
            
        Returns:
            Base64-encoded random key.
        """
        random_bytes = uuid.uuid4().bytes + uuid.uuid4().bytes
        return base64.b64encode(random_bytes[:length]).decode('utf-8')
    
    def get_current_key(self) -> Tuple[str, str]:
        """
        Get the current active key for signing.
        
        Returns:
            Tuple of (key_id, key).
            
        Raises:
            SigningKeyError: If no active key is available.
        """
        if self.current_key_id not in self.keys:
            raise SigningKeyError("Current key not found")
            
        key_info = self.keys[self.current_key_id]
        
        # Check if the key is expired
        if key_info["expires_at"] < time.time():
            # Auto-rotate if expired
            logger.warning(f"Current key {self.current_key_id} is expired. Auto-rotating.")
            self.rotate_key()
            
        return self.current_key_id, key_info["key"]
    
    def get_key_by_id(self, key_id: str) -> Optional[str]:
        """
        Get a key by its ID.
        
        Args:
            key_id: ID of the key to retrieve.
            
        Returns:
            The key, or None if the key ID is not found.
        """
        if key_id not in self.keys:
            return None
            
        return self.keys[key_id]["key"]
    
    def rotate_key(self) -> str:
        """
        Rotate the signing key by generating a new one.
        
        The old key is kept for a grace period to validate incoming messages.
        
        Returns:
            ID of the new key.
            
        Raises:
            KeyRotationError: If key rotation fails.
        """
        try:
            # Generate new key and ID
            new_key = self._generate_key()
            new_key_id = str(uuid.uuid4())
            
            now = time.time()
            expiration = now + (self.rotation_interval_days * 24 * 60 * 60)
            
            # Add new key
            self.keys[new_key_id] = {
                "key": new_key,
                "created_at": now,
                "expires_at": expiration,
                "active": True
            }
            
            # Mark old key as inactive for signing (but still valid for verification)
            if self.current_key_id in self.keys:
                self.keys[self.current_key_id]["active"] = False
            
            # Update current key pointer
            self.current_key_id = new_key_id
            
            logger.info(f"Key rotated. New key ID: {new_key_id}")
            return new_key_id
        except Exception as e:
            raise KeyRotationError(f"Failed to rotate key: {e}")
    
    def purge_expired_keys(self, grace_period_days: int = 7) -> None:
        """
        Remove expired keys that are past the grace period.
        
        Args:
            grace_period_days: Number of days to keep expired keys.
        """
        now = time.time()
        grace_period = grace_period_days * 24 * 60 * 60
        
        keys_to_remove = []
        for key_id, key_info in self.keys.items():
            # Skip the current key
            if key_id == self.current_key_id:
                continue
                
            # Remove keys that are expired and past grace period
            if key_info["expires_at"] + grace_period < now:
                keys_to_remove.append(key_id)
        
        # Remove keys
        for key_id in keys_to_remove:
            del self.keys[key_id]
            logger.info(f"Purged expired key: {key_id}")
    
    def emergency_rotation(self) -> str:
        """
        Perform an emergency key rotation and invalidate all previous keys.
        
        Use this in case of a security breach.
        
        Returns:
            ID of the new key.
        """
        # Clear all existing keys
        self.keys = {}
        
        # Generate new key and ID
        new_key = self._generate_key()
        new_key_id = str(uuid.uuid4())
        
        now = time.time()
        expiration = now + (self.rotation_interval_days * 24 * 60 * 60)
        
        # Add new key
        self.keys[new_key_id] = {
            "key": new_key,
            "created_at": now,
            "expires_at": expiration,
            "active": True
        }
        
        # Update current key pointer
        self.current_key_id = new_key_id
        
        logger.warning(f"Emergency key rotation completed. All previous keys invalidated. New key ID: {new_key_id}")
        return new_key_id
    
    def import_key(self, key_id: str, key: str, 
                 created_at: Optional[float] = None,
                 expires_at: Optional[float] = None,
                 active: bool = False) -> None:
        """
        Import an existing key.
        
        Args:
            key_id: ID for the key.
            key: The key value.
            created_at: Creation timestamp. If None, uses current time.
            expires_at: Expiration timestamp. If None, uses rotation interval.
            active: Whether the key should be active for signing.
        """
        if created_at is None:
            created_at = time.time()
            
        if expires_at is None:
            expires_at = created_at + (self.rotation_interval_days * 24 * 60 * 60)
        
        self.keys[key_id] = {
            "key": key,
            "created_at": created_at,
            "expires_at": expires_at,
            "active": active
        }
        
        # If this is the only key or it's active, make it current
        if active or len(self.keys) == 1:
            self.current_key_id = key_id
            self.keys[key_id]["active"] = True
            
        logger.info(f"Imported key: {key_id}")
    
    def export_keys(self) -> Dict[str, Dict[str, Any]]:
        """
        Export all keys for backup or transfer.
        
        Returns:
            Dictionary of all keys with their metadata.
        """
        return self.keys.copy()

class MessageSigner:
    """
    Signs and verifies messages using HMAC-SHA256.
    
    This class uses the KeyManager to handle key management and rotation.
    """
    
    def __init__(self, key_manager: Optional[KeyManager] = None):
        """
        Initialize the message signer.
        
        Args:
            key_manager: KeyManager instance for key management.
                       If None, a new KeyManager is created.
        """
        self.key_manager = key_manager or KeyManager()
    
    def sign_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sign a message using HMAC-SHA256.
        
        Args:
            message: The message to sign.
            
        Returns:
            The message with added signature and key ID.
            
        Raises:
            SignatureError: If signing fails.
        """
        try:
            # Create a copy to avoid modifying the original
            signed_message = message.copy()
            
            # Remove any existing signature (for re-signing)
            if "signature" in signed_message:
                del signed_message["signature"]
            if "signature_metadata" in signed_message:
                del signed_message["signature_metadata"]
            
            # Get current key and ID
            key_id, key = self.key_manager.get_current_key()
            
            # Create canonical representation for signing
            # Sort keys to ensure consistent ordering
            canonical = json.dumps(signed_message, sort_keys=True, separators=(',', ':'))
            
            # Create signature
            signature = hmac.new(
                key.encode('utf-8'),
                canonical.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            # Add signature and metadata to the message
            signed_message["signature"] = signature
            signed_message["signature_metadata"] = {
                "key_id": key_id,
                "algorithm": "hmac-sha256",
                "timestamp": time.time()
            }
            
            return signed_message
        except Exception as e:
            raise SignatureError(f"Failed to sign message: {e}")
    
    def verify_message(self, message: Dict[str, Any]) -> bool:
        """
        Verify a message signature.
        
        Args:
            message: The message to verify.
            
        Returns:
            True if the signature is valid, False otherwise.
            
        Raises:
            AuthenticationError: If verification fails due to missing fields or other errors.
        """
        try:
            # Check if message has signature and metadata
            if "signature" not in message or "signature_metadata" not in message:
                raise AuthenticationError("Message does not have a signature")
            
            signature = message["signature"]
            metadata = message["signature_metadata"]
            
            # Get key ID and algorithm
            if "key_id" not in metadata or "algorithm" not in metadata:
                raise AuthenticationError("Signature metadata is missing required fields")
                
            key_id = metadata["key_id"]
            algorithm = metadata["algorithm"]
            
            # Check algorithm
            if algorithm != "hmac-sha256":
                raise AuthenticationError(f"Unsupported signature algorithm: {algorithm}")
            
            # Get the key
            key = self.key_manager.get_key_by_id(key_id)
            if key is None:
                raise AuthenticationError(f"Unknown key ID: {key_id}")
            
            # Create a copy of the message without the signature for verification
            message_copy = message.copy()
            del message_copy["signature"]
            
            # Create canonical representation
            canonical = json.dumps(message_copy, sort_keys=True, separators=(',', ':'))
            
            # Calculate expected signature
            expected_signature = hmac.new(
                key.encode('utf-8'),
                canonical.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            # Verify signature using constant-time comparison
            return hmac.compare_digest(signature, expected_signature)
        except AuthenticationError:
            raise
        except Exception as e:
            raise AuthenticationError(f"Signature verification failed: {e}")

class JWTManager:
    """
    Handles JWT creation and validation for authentication.
    
    This class is used for more complex authorization scenarios where
    additional claims and token expiration are needed.
    """
    
    def __init__(self, key_manager: Optional[KeyManager] = None,
                token_lifetime_minutes: int = 60):
        """
        Initialize the JWT manager.
        
        Args:
            key_manager: KeyManager for key management.
            token_lifetime_minutes: Default token lifetime in minutes.
        """
        self.key_manager = key_manager or KeyManager()
        self.token_lifetime_minutes = token_lifetime_minutes
    
    def create_token(self, subject: str, claims: Dict[str, Any] = None,
                   lifetime_minutes: Optional[int] = None) -> str:
        """
        Create a JWT token.
        
        Args:
            subject: Subject of the token (usually agent ID).
            claims: Additional claims to include in the token.
            lifetime_minutes: Token lifetime in minutes (overrides default).
            
        Returns:
            The JWT token as a string.
        """
        # Use default lifetime if not specified
        if lifetime_minutes is None:
            lifetime_minutes = self.token_lifetime_minutes
            
        # Get current time and expiration
        now = int(time.time())
        exp = now + (lifetime_minutes * 60)
        
        # Get current key and ID
        key_id, key = self.key_manager.get_current_key()
        
        # Create JWT header
        header = {
            "alg": "HS256",
            "typ": "JWT",
            "kid": key_id
        }
        
        # Create JWT payload
        payload = {
            "sub": subject,
            "iat": now,
            "exp": exp,
            "nbf": now
        }
        
        # Add additional claims
        if claims:
            payload.update(claims)
        
        # Encode header and payload
        header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip('=')
        payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
        
        # Create signature
        message = f"{header_b64}.{payload_b64}"
        signature = hmac.new(
            key.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).digest()
        signature_b64 = base64.urlsafe_b64encode(signature).decode().rstrip('=')
        
        # Combine to form the token
        return f"{header_b64}.{payload_b64}.{signature_b64}"
    
    def validate_token(self, token: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Validate a JWT token.
        
        Args:
            token: The JWT token to validate.
            
        Returns:
            Tuple of (is_valid, claims). If not valid, claims is None.
        """
        try:
            # Split token into parts
            parts = token.split('.')
            if len(parts) != 3:
                return False, None
                
            header_b64, payload_b64, signature_b64 = parts
            
            # Decode header and payload
            # Add padding if needed
            header_b64 += '=' * ((4 - len(header_b64) % 4) % 4)
            payload_b64 += '=' * ((4 - len(payload_b64) % 4) % 4)
            
            header = json.loads(base64.urlsafe_b64decode(header_b64).decode())
            payload = json.loads(base64.urlsafe_b64decode(payload_b64).decode())
            
            # Verify algorithm
            if header.get("alg") != "HS256":
                return False, None
                
            # Get key ID
            key_id = header.get("kid")
            if not key_id:
                return False, None
                
            # Get the key
            key = self.key_manager.get_key_by_id(key_id)
            if key is None:
                return False, None
            
            # Verify signature
            message = f"{header_b64}.{payload_b64}"
            expected_signature = hmac.new(
                key.encode('utf-8'),
                message.encode('utf-8'),
                hashlib.sha256
            ).digest()
            
            # Add padding to signature for comparison
            signature_b64 += '=' * ((4 - len(signature_b64) % 4) % 4)
            actual_signature = base64.urlsafe_b64decode(signature_b64)
            
            if not hmac.compare_digest(expected_signature, actual_signature):
                return False, None
            
            # Check expiration
            now = int(time.time())
            exp = payload.get("exp", 0)
            nbf = payload.get("nbf", 0)
            
            if now > exp:
                return False, None  # Token expired
                
            if now < nbf:
                return False, None  # Token not yet valid
            
            return True, payload
        except Exception as e:
            logger.error(f"Error validating token: {e}")
            return False, None

class AuthenticationService:
    """
    Main service for message authentication, combining HMAC and JWT approaches.
    
    This class provides a unified interface for signing and verifying messages
    using either HMAC or JWT, depending on the use case.
    """
    
    def __init__(self, key_manager: Optional[KeyManager] = None,
                token_lifetime_minutes: int = 60):
        """
        Initialize the authentication service.
        
        Args:
            key_manager: KeyManager for key management.
            token_lifetime_minutes: Default JWT token lifetime in minutes.
        """
        self.key_manager = key_manager or KeyManager()
        self.message_signer = MessageSigner(self.key_manager)
        self.jwt_manager = JWTManager(self.key_manager, token_lifetime_minutes)
        
        logger.info("Authentication service initialized")
    
    def sign_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sign a message using HMAC.
        
        Args:
            message: The message to sign.
            
        Returns:
            The signed message.
        """
        return self.message_signer.sign_message(message)
    
    def verify_message(self, message: Dict[str, Any]) -> bool:
        """
        Verify a message signature.
        
        Args:
            message: The message to verify.
            
        Returns:
            True if the signature is valid, False otherwise.
        """
        try:
            return self.message_signer.verify_message(message)
        except AuthenticationError as e:
            logger.warning(f"Authentication failed: {e}")
            return False
    
    def create_token(self, subject: str, claims: Dict[str, Any] = None,
                   lifetime_minutes: Optional[int] = None) -> str:
        """
        Create a JWT token.
        
        Args:
            subject: Subject of the token (usually agent ID).
            claims: Additional claims to include in the token.
            lifetime_minutes: Token lifetime in minutes (overrides default).
            
        Returns:
            The JWT token as a string.
        """
        return self.jwt_manager.create_token(subject, claims, lifetime_minutes)
    
    def validate_token(self, token: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Validate a JWT token.
        
        Args:
            token: The JWT token to validate.
            
        Returns:
            Tuple of (is_valid, claims). If not valid, claims is None.
        """
        return self.jwt_manager.validate_token(token)
    
    def rotate_keys(self) -> str:
        """
        Rotate the signing keys.
        
        Returns:
            ID of the new key.
        """
        return self.key_manager.rotate_key()
    
    def emergency_rotation(self) -> str:
        """
        Perform an emergency key rotation.
        
        Returns:
            ID of the new key.
        """
        return self.key_manager.emergency_rotation()
    
    def purge_expired_keys(self, grace_period_days: int = 7) -> None:
        """
        Purge expired keys.
        
        Args:
            grace_period_days: Grace period in days.
        """
        self.key_manager.purge_expired_keys(grace_period_days)
    
    def get_key_info(self) -> Dict[str, Any]:
        """
        Get information about the current key.
        
        Returns:
            Key information.
        """
        key_id, _ = self.key_manager.get_current_key()
        key_info = self.key_manager.keys[key_id]
        
        return {
            "key_id": key_id,
            "created_at": key_info["created_at"],
            "expires_at": key_info["expires_at"],
            "active": key_info["active"]
        }
    
    def export_keys(self) -> Dict[str, Dict[str, Any]]:
        """
        Export all keys for backup or transfer.
        
        Returns:
            Dictionary of all keys with their metadata.
        """
        return self.key_manager.export_keys()
    
    def import_key(self, key_id: str, key: str, 
                 created_at: Optional[float] = None,
                 expires_at: Optional[float] = None,
                 active: bool = False) -> None:
        """
        Import an existing key.
        
        Args:
            key_id: ID for the key.
            key: The key value.
            created_at: Creation timestamp.
            expires_at: Expiration timestamp.
            active: Whether the key should be active for signing.
        """
        self.key_manager.import_key(key_id, key, created_at, expires_at, active)
