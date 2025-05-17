"""
Integration of authentication system with the communication bus.

This module provides classes and functions for integrating the message
authentication system with the Nexus Framework's communication infrastructure.
"""

import logging
import json
import os
from typing import Dict, Any, Optional, Callable, List

from ...communication.reliable_bus import ReliableCommunicationBus
from ...messaging.broker import MessageBroker
from ..authentication import (
    AuthenticationService,
    KeyManager,
    AuthMiddleware,
    JWTAuthMiddleware,
    AuthenticationProcessor,
    SigningKeyError,
    AuthenticationError
)
from ...core.message import Message

logger = logging.getLogger(__name__)

class AuthenticatedCommunicationBus(ReliableCommunicationBus):
    """
    Communication bus with built-in message authentication.
    
    This class extends the reliable communication bus to add message
    authentication using either HMAC or JWT.
    """
    
    def __init__(self, broker: Optional[MessageBroker] = None, 
                legacy_mode: bool = False,
                auth_service: Optional[AuthenticationService] = None,
                strict_mode: bool = False,
                use_jwt: bool = False,
                exempt_paths: Optional[List[str]] = None,
                keys_file: Optional[str] = None):
        """
        Initialize the authenticated communication bus.
        
        Args:
            broker: Message broker to use.
            legacy_mode: Whether to fall back to in-memory messaging if broker is unavailable.
            auth_service: Authentication service to use.
            strict_mode: If True, reject messages with invalid authentication.
            use_jwt: If True, use JWT tokens instead of HMAC signatures.
            exempt_paths: List of message paths exempt from authentication.
            keys_file: Path to keys file for authentication service.
        """
        # Initialize parent class
        super().__init__(broker, legacy_mode)
        
        # Create or use authentication service
        if auth_service is None and keys_file is not None:
            # Load keys from file
            try:
                with open(keys_file, 'r') as f:
                    keys_data = json.load(f)
                
                # Create key manager with loaded keys
                key_manager = KeyManager()  # Create empty manager first
                
                # Import existing keys
                for key_id, key_info in keys_data.items():
                    key_manager.import_key(
                        key_id,
                        key_info["key"],
                        key_info["created_at"],
                        key_info["expires_at"],
                        key_info["active"]
                    )
                
                # Create authentication service with loaded keys
                auth_service = AuthenticationService(key_manager)
                logger.info(f"Loaded authentication keys from {keys_file}")
            except Exception as e:
                logger.warning(f"Failed to load keys from {keys_file}: {e}")
                # Fall back to default authentication service
                auth_service = AuthenticationService()
                logger.info("Using default authentication service with generated keys")
        elif auth_service is None:
            # Create default authentication service
            auth_service = AuthenticationService()
            logger.info("Using default authentication service with generated keys")
        
        # Create authentication processor
        self.auth_processor = AuthenticationProcessor(
            auth_service, strict_mode, use_jwt, exempt_paths
        )
        
        logger.info(f"Authenticated communication bus initialized (strict_mode={strict_mode}, use_jwt={use_jwt})")
    
    def send_message(self, message: Message) -> Optional[str]:
        """
        Send a message with authentication.
        
        Args:
            message: The message to send.
            
        Returns:
            Message ID if sent successfully, None otherwise.
        """
        # Add authentication to the message
        authenticated_message = self.auth_processor.process_outgoing_message(message)
        
        # Send the authenticated message
        return super().send_message(authenticated_message)
    
    def send_broadcast(self, message: Message, recipients: List[str]) -> Dict[str, Optional[str]]:
        """
        Send a message to multiple recipients with authentication.
        
        Args:
            message: The message to send.
            recipients: List of recipient IDs.
            
        Returns:
            Dictionary mapping recipient IDs to message IDs or None if sending failed.
        """
        # Add authentication to the message
        authenticated_message = self.auth_processor.process_outgoing_message(message)
        
        # Send the authenticated message
        return super().send_broadcast(authenticated_message, recipients)
    
    def wrap_message_handler(self, handler: Callable[[Message], Optional[Message]]) -> Callable[[Message], Optional[Message]]:
        """
        Wrap a message handler to automatically handle authentication.
        
        Args:
            handler: The original message handler function.
            
        Returns:
            A wrapped handler function.
        """
        # Wrap with authentication processor
        auth_wrapped = self.auth_processor.wrap_message_handler(handler)
        
        # Wrap with parent class
        return super().wrap_message_handler(auth_wrapped)
    
    def register_agent(self, agent, handlers=None, topics=None):
        """
        Register an agent with the bus, wrapping its handlers for authentication.
        
        Args:
            agent: The agent to register.
            handlers: Optional mapping of topics to handler functions.
            topics: Optional list of topics to subscribe to.
        """
        # If the agent has a process_message method, wrap it for authentication
        if hasattr(agent, 'process_message'):
            original_process_message = agent.process_message
            agent.process_message = self.auth_processor.wrap_message_handler(original_process_message)
        
        # Register with parent class
        super().register_agent(agent, handlers, topics)

class KeyRotationManager:
    """
    Manages automatic key rotation for the authentication system.
    
    This class provides functionality for scheduled key rotation and
    key synchronization across multiple nodes.
    """
    
    def __init__(self, auth_service: AuthenticationService,
                keys_file: str,
                rotation_interval_days: int = 30,
                auto_purge: bool = True,
                purge_grace_days: int = 7):
        """
        Initialize the key rotation manager.
        
        Args:
            auth_service: Authentication service to manage.
            keys_file: Path to keys file.
            rotation_interval_days: Interval between key rotations.
            auto_purge: Whether to purge expired keys automatically.
            purge_grace_days: Grace period for expired keys.
        """
        self.auth_service = auth_service
        self.keys_file = keys_file
        self.rotation_interval_days = rotation_interval_days
        self.auto_purge = auto_purge
        self.purge_grace_days = purge_grace_days
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(os.path.abspath(keys_file)), exist_ok=True)
        
        logger.info(f"Key rotation manager initialized (rotation_interval={rotation_interval_days} days)")
    
    def perform_rotation(self, emergency: bool = False) -> str:
        """
        Perform key rotation and save updated keys.
        
        Args:
            emergency: Whether to perform an emergency rotation.
            
        Returns:
            ID of the new key.
        """
        try:
            # Perform the rotation
            if emergency:
                new_key_id = self.auth_service.emergency_rotation()
                logger.info(f"Emergency key rotation completed. New key ID: {new_key_id}")
            else:
                new_key_id = self.auth_service.rotate_keys()
                logger.info(f"Key rotation completed. New key ID: {new_key_id}")
            
            # Save updated keys
            self._save_keys()
            
            return new_key_id
        except Exception as e:
            logger.error(f"Key rotation failed: {e}")
            raise
    
    def purge_expired_keys(self) -> int:
        """
        Purge expired keys and save updated keys.
        
        Returns:
            Number of keys purged.
        """
        try:
            # Get count before purge
            before_count = len(self.auth_service.export_keys())
            
            # Purge expired keys
            self.auth_service.purge_expired_keys(self.purge_grace_days)
            
            # Get count after purge
            after_count = len(self.auth_service.export_keys())
            
            # Save updated keys
            self._save_keys()
            
            purged_count = before_count - after_count
            if purged_count > 0:
                logger.info(f"Purged {purged_count} expired keys")
            
            return purged_count
        except Exception as e:
            logger.error(f"Failed to purge expired keys: {e}")
            raise
    
    def _save_keys(self) -> None:
        """Save keys to the keys file."""
        try:
            # Export keys
            keys = self.auth_service.export_keys()
            
            # Save to file
            with open(self.keys_file, 'w') as f:
                json.dump(keys, f, indent=2)
                
            logger.debug(f"Keys saved to {self.keys_file}")
        except Exception as e:
            logger.error(f"Failed to save keys: {e}")
            raise
    
    def check_and_rotate(self) -> bool:
        """
        Check if key rotation is needed and perform it if necessary.
        
        Returns:
            True if rotation was performed, False otherwise.
        """
        try:
            # Get current key info
            key_info = self.auth_service.get_key_info()
            
            # Calculate remaining days
            now = key_info.get("created_at", 0)
            expires = key_info.get("expires_at", 0)
            remaining_seconds = max(0, expires - now)
            remaining_days = remaining_seconds / (24 * 60 * 60)
            
            # Rotate if less than 20% of time remaining
            threshold = self.rotation_interval_days * 0.2
            if remaining_days < threshold:
                logger.info(f"Key rotation needed: {remaining_days:.1f} days remaining")
                self.perform_rotation()
                return True
            
            # Purge expired keys if auto-purge is enabled
            if self.auto_purge:
                self.purge_expired_keys()
                
            return False
        except Exception as e:
            logger.error(f"Failed to check key rotation: {e}")
            return False
    
    def start_scheduled_rotation(self, comm_bus: ReliableCommunicationBus) -> None:
        """
        Start scheduled key rotation.
        
        This method sets up a scheduled task to check and rotate keys periodically.
        
        Args:
            comm_bus: Communication bus to use for coordination.
        """
        # TODO: Implement scheduled rotation
        # This could involve setting up a separate thread or using an external scheduler
        pass

def create_authenticated_bus(broker: Optional[MessageBroker] = None,
                           keys_file: str = "auth_keys.json",
                           strict_mode: bool = False,
                           use_jwt: bool = False) -> AuthenticatedCommunicationBus:
    """
    Create an authenticated communication bus.
    
    This is a convenience function for creating an authenticated bus
    with common settings.
    
    Args:
        broker: Message broker to use.
        keys_file: Path to keys file.
        strict_mode: If True, reject messages with invalid authentication.
        use_jwt: If True, use JWT tokens instead of HMAC signatures.
        
    Returns:
        An authenticated communication bus.
    """
    # Create authenticated bus
    bus = AuthenticatedCommunicationBus(
        broker=broker,
        legacy_mode=(broker is None),
        keys_file=keys_file,
        strict_mode=strict_mode,
        use_jwt=use_jwt
    )
    
    return bus
