"""
Utility to load and integrate the VerificationAgent.

This module provides functions to load the VerificationAgent from a configuration
file and integrate it with the Nexus Framework's communication infrastructure.
"""

import os
import logging
import yaml
from typing import Dict, Any, Optional, List, Type

from nexus_framework.security import (
    VerificationAgent,
    ValidationRule,
    SanitizationRule,
    SchemaValidator,
    SizeValidator,
    ContentValidator,
    PermissionValidator,
    RateLimitValidator,
    SizeLimitSanitizer,
    ContentFilterSanitizer,
    JsonSanitizer,
    RecursiveDepthSanitizer
)
from nexus_framework.communication.reliable_bus import ReliableCommunicationBus
from nexus_framework.messaging.rabbit_mq_broker import RabbitMQBroker

logger = logging.getLogger(__name__)

# Registry of available validator and sanitizer classes
VALIDATOR_REGISTRY: Dict[str, Type[ValidationRule]] = {
    "schema": SchemaValidator,
    "size": SizeValidator,
    "content": ContentValidator,
    "permission": PermissionValidator,
    "rate_limit": RateLimitValidator
}

SANITIZER_REGISTRY: Dict[str, Type[SanitizationRule]] = {
    "size_limit": SizeLimitSanitizer,
    "content_filter": ContentFilterSanitizer,
    "json": JsonSanitizer,
    "recursive_depth": RecursiveDepthSanitizer
}

def load_config(config_path: str) -> Dict[str, Any]:
    """
    Load configuration from a YAML file.
    
    Args:
        config_path: Path to the configuration file
        
    Returns:
        Configuration dictionary
    """
    try:
        if not os.path.exists(config_path):
            logger.error(f"Configuration file not found: {config_path}")
            return {}
            
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
            
        if not config:
            logger.warning(f"Empty configuration loaded from {config_path}")
            return {}
            
        logger.info(f"Successfully loaded configuration from {config_path}")
        return config
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        return {}

def load_validation_rules(config: Dict[str, Any]) -> List[ValidationRule]:
    """
    Load validation rules from configuration.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        List of ValidationRule instances
    """
    validators = []
    
    for validator_config in config.get("validators", []):
        validator_type = validator_config.get("type")
        
        if not validator_type:
            logger.warning("Validator config missing 'type' field, skipping")
            continue
            
        # Skip disabled validators
        if not validator_config.get("enabled", True):
            logger.info(f"Validator '{validator_type}' is disabled, skipping")
            continue
            
        # Get validator class
        validator_class = VALIDATOR_REGISTRY.get(validator_type)
        if not validator_class:
            logger.warning(f"Unknown validator type: {validator_type}")
            continue
            
        # Extract parameters
        params = validator_config.get("params", {})
        
        # Add name and description if available
        if "description" in validator_config:
            params["description"] = validator_config["description"]
            
        if "name" in validator_config:
            params["name"] = validator_config["name"]
        else:
            # Create a name if not specified
            params["name"] = f"{validator_type.title()}Validator"
            
        # Create validator instance
        try:
            validator = validator_class(**params)
            validators.append(validator)
            logger.info(f"Loaded validator: {validator.name} ({validator_type})")
        except Exception as e:
            logger.error(f"Failed to create validator '{validator_type}': {e}")
            
    # Sort validators by priority
    return sorted(validators, key=lambda v: 
                 next((cfg["priority"] for cfg in config.get("validators", []) 
                       if cfg.get("type") == v.__class__.__name__.lower().replace("validator", "")), 100))

def load_sanitization_rules(config: Dict[str, Any]) -> List[SanitizationRule]:
    """
    Load sanitization rules from configuration.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        List of SanitizationRule instances
    """
    sanitizers = []
    
    for sanitizer_config in config.get("sanitizers", []):
        sanitizer_type = sanitizer_config.get("type")
        
        if not sanitizer_type:
            logger.warning("Sanitizer config missing 'type' field, skipping")
            continue
            
        # Skip disabled sanitizers
        if not sanitizer_config.get("enabled", True):
            logger.info(f"Sanitizer '{sanitizer_type}' is disabled, skipping")
            continue
            
        # Get sanitizer class
        sanitizer_class = SANITIZER_REGISTRY.get(sanitizer_type)
        if not sanitizer_class:
            logger.warning(f"Unknown sanitizer type: {sanitizer_type}")
            continue
            
        # Extract parameters
        params = sanitizer_config.get("params", {})
        
        # Add name and description if available
        if "description" in sanitizer_config:
            params["description"] = sanitizer_config["description"]
            
        if "name" in sanitizer_config:
            params["name"] = sanitizer_config["name"]
        else:
            # Create a name if not specified
            params["name"] = f"{sanitizer_type.title()}Sanitizer"
            
        # Create sanitizer instance
        try:
            sanitizer = sanitizer_class(**params)
            sanitizers.append(sanitizer)
            logger.info(f"Loaded sanitizer: {sanitizer.name} ({sanitizer_type})")
        except Exception as e:
            logger.error(f"Failed to create sanitizer '{sanitizer_type}': {e}")
            
    # Sort sanitizers by priority
    return sorted(sanitizers, key=lambda s: 
                 next((cfg["priority"] for cfg in config.get("sanitizers", []) 
                       if cfg.get("type") == s.__class__.__name__.lower().replace("sanitizer", "")), 100))

def create_verification_agent(config_path: str) -> Optional[VerificationAgent]:
    """
    Create a VerificationAgent from a configuration file.
    
    Args:
        config_path: Path to the configuration file
        
    Returns:
        VerificationAgent instance, or None if creation failed
    """
    # Load configuration
    config = load_config(config_path)
    if not config:
        logger.error("Failed to load configuration, cannot create VerificationAgent")
        return None
        
    # Create agent
    agent_name = config.get("agent_name", "VerificationAgent")
    role = config.get("role", "security")
    
    agent = VerificationAgent(agent_name=agent_name)
    
    # Load validation rules
    validators = load_validation_rules(config)
    for validator in validators:
        agent.register_validator(validator)
        
    # Load sanitization rules
    sanitizers = load_sanitization_rules(config)
    for sanitizer in sanitizers:
        agent.register_sanitizer(sanitizer)
        
    logger.info(f"Created {agent.agent_name} with {len(agent.validators)} validators and {len(agent.sanitizers)} sanitizers")
    return agent

def integrate_with_communication_bus(agent: VerificationAgent, 
                                    bus: ReliableCommunicationBus) -> None:
    """
    Integrate the VerificationAgent with a communication bus.
    
    This function registers the agent with the bus and configures the routing
    to ensure all messages pass through the verification agent.
    
    Args:
        agent: The VerificationAgent to integrate
        bus: The communication bus to integrate with
    """
    try:
        # Register the agent with the bus
        bus.register_agent(agent)
        logger.info(f"Registered {agent.agent_name} with communication bus")
        
        # Configure the bus to route messages through the verification agent
        # This is a simplified example - the actual implementation would depend
        # on the specific communication bus design
        bus.configure_message_interceptor(agent)
        logger.info("Configured message interception for VerificationAgent")
        
        # Set up the verification topic
        verification_topic = "nexus.verification"
        bus.create_topic(verification_topic)
        logger.info(f"Created verification topic: {verification_topic}")
        
        # Configure routing to ensure all messages pass through verification
        bus.configure_routing(
            source_pattern="*",  # All sources
            destination_pattern="*",  # All destinations
            via_agent=agent.agent_id,
            priority=100  # High priority to ensure it runs before other routing rules
        )
        logger.info("Configured routing rules for VerificationAgent")
        
        logger.info("VerificationAgent integration complete")
    except Exception as e:
        logger.error(f"Failed to integrate VerificationAgent with communication bus: {e}")

def setup_security_system(config_path: str = "config/verification_agent_config.yml") -> Optional[VerificationAgent]:
    """
    Set up the security system with a VerificationAgent and integrate it with the communication infrastructure.
    
    Args:
        config_path: Path to the configuration file
        
    Returns:
        The configured VerificationAgent, or None if setup failed
    """
    # Create verification agent from config
    agent = create_verification_agent(config_path)
    
    if not agent:
        logger.error("Failed to create VerificationAgent, exiting")
        return None
    
    # Create and initialize RabbitMQ broker
    broker_config = {
        'host': 'localhost',
        'port': 5672,
        'vhost': '/',
        'username': 'guest',
        'password': 'guest',
        'heartbeat': 60,
        'connection_attempts': 3
    }
    
    try:
        broker = RabbitMQBroker()
        initialized = broker.initialize(broker_config)
        
        if not initialized:
            logger.error("Failed to initialize RabbitMQ broker, exiting")
            return agent
        
        logger.info("RabbitMQ broker initialized")
        
        # Create communication bus with the broker
        bus = ReliableCommunicationBus(broker=broker)
        logger.info("ReliableCommunicationBus created")
        
        # Integrate verification agent with the communication bus
        integrate_with_communication_bus(agent, bus)
        
        return agent
    except Exception as e:
        logger.error(f"Error setting up security system: {e}")
        return agent

def main():
    """Example usage of the utility functions."""
    # Configure logging
    logging.basicConfig(level=logging.INFO, 
                       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Set up security system
    agent = setup_security_system()
    
    if agent:
        logger.info(f"Security system set up successfully with agent: {agent.agent_name}")
    else:
        logger.error("Failed to set up security system")

if __name__ == "__main__":
    main()
