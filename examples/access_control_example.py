"""
Example demonstrating the Access Control System functionality.

This script shows how to set up and use the access control system
to secure agent interactions and tool access in the Nexus Framework.
"""

import logging
import os
import json
from typing import Dict, Any, Optional, List

from nexus_framework.core.message import Message
from nexus_framework.security.access_control import (
    Permission,
    ResourceType,
    ResourceAction,
    Role,
    RoleManager,
    RoleRegistry,
    PolicyManager,
    Policy,
    EffectType,
    AccessControlService,
    SecureCommunicationBus,
    AccessControlManager
)
from nexus_framework.messaging.broker import MessageBroker
from nexus_framework.security.authentication import (
    KeyManager,
    AuthenticationService
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_test_broker() -> MessageBroker:
    """Create a test message broker."""
    # This would typically be a RabbitMQ broker, but for the example
    # we'll just use a mock broker
    class MockBroker(MessageBroker):
        def initialize(self, config):
            return True
            
        def publish(self, topic, message, headers=None):
            logger.info(f"Publishing to {topic}: {message}")
            return "message-id"
            
        def subscribe(self, topic, callback, queue_name=None):
            logger.info(f"Subscribing to {topic}")
            return "subscription-id"
            
        def acknowledge(self, message_id):
            return True
            
        def negative_acknowledge(self, message_id, reason):
            return True
    
    return MockBroker()

def print_separator():
    """Print a separator line for better readability."""
    print("\n" + "=" * 80 + "\n")

def main():
    """Run the access control system example."""
    print("Nexus Framework - Access Control System Example")
    print_separator()
    
    # Create temporary directory for configuration
    config_dir = "access_control_example"
    os.makedirs(config_dir, exist_ok=True)
    
    # Step 1: Set up the access control service
    print("Step 1: Setting up Access Control Service")
    access_control_service = AccessControlService(config_path=config_dir)
    
    # Create default roles and policies
    access_control_service.create_default_configuration()
    print("Created default access control configuration")
    
    # Step 2: Create a manager for easier configuration
    print("\nStep 2: Creating Access Control Manager")
    ac_manager = AccessControlManager(access_control_service)
    
    # List the default roles
    roles = ac_manager.list_roles()
    print(f"Default roles ({len(roles)}):")
    for role in roles:
        print(f"  - {role['name']}: {role['description']}")
        print(f"    Permissions: {len(role['permissions'])}")
    
    # Step 3: Create custom roles and policies
    print("\nStep 3: Creating Custom Roles and Policies")
    
    # Create a custom role for assistant agents
    assistant_role = ac_manager.create_role(
        name="assistant_agent",
        description="Role for assistant agents with extended permissions",
        permissions=[
            "agent:read:*",
            "agent:execute:*",
            "message:create:*",
            "message:read:*",
            "tool:read:*",
            "tool:execute:calculator",
            "tool:execute:search",
            "data:read:*"
        ],
        parent_roles=["agent"]  # Inherit from base agent role
    )
    print(f"Created custom role: {assistant_role.name}")
    
    # Create a custom policy for workflow access
    workflow_policy = ac_manager.create_policy(
        name="workflow_access_policy",
        description="Allow agents to access workflows they are part of",
        effect="allow",
        resource_patterns=["workflow:*"],
        action_patterns=["read", "execute"],
        entity_patterns=["agent_*", "assistant_*"],
        priority=500
    )
    print(f"Created custom policy: {workflow_policy.name}")
    
    # Step 4: Assign roles to entities
    print("\nStep 4: Assigning Roles to Entities")
    
    # Assign roles to some example entities
    ac_manager.assign_role_to_entity("assistant_agent_1", "assistant_agent")
    ac_manager.assign_role_to_entity("admin_user_1", "admin")
    ac_manager.assign_role_to_entity("regular_user_1", "user")
    
    print("Assigned roles to entities:")
    print("  - assistant_agent_1 -> assistant_agent")
    print("  - admin_user_1 -> admin")
    print("  - regular_user_1 -> user")
    
    # Step 5: Grant specific permissions via ACLs
    print("\nStep 5: Granting Specific Permissions via ACLs")
    
    # Grant a specific permission to an entity
    ac_manager.grant_acl_permission(
        entity_id="assistant_agent_1",
        resource_type="tool",
        action="execute",
        resource_id="special_tool",
        expires_in=3600  # Permission expires in 1 hour
    )
    print("Granted temporary permission to assistant_agent_1 for special_tool")
    
    # Step 6: Check permissions
    print("\nStep 6: Checking Permissions")
    
    # Check various permission scenarios
    check_scenarios = [
        {
            "entity": "assistant_agent_1",
            "resource": "message",
            "action": "create",
            "instance": "user_agent_1"
        },
        {
            "entity": "assistant_agent_1",
            "resource": "tool",
            "action": "execute",
            "instance": "special_tool"
        },
        {
            "entity": "assistant_agent_1",
            "resource": "tool",
            "action": "execute",
            "instance": "restricted_tool"
        },
        {
            "entity": "admin_user_1",
            "resource": "agent",
            "action": "manage",
            "instance": "*"
        },
        {
            "entity": "regular_user_1",
            "resource": "agent",
            "action": "manage",
            "instance": "*"
        }
    ]
    
    for scenario in check_scenarios:
        entity = scenario["entity"]
        resource = scenario["resource"]
        action = scenario["action"]
        instance = scenario["instance"]
        
        allowed, reason = ac_manager.check_permission(entity, resource, action, instance)
        
        status = "✅ ALLOWED" if allowed else "❌ DENIED"
        print(f"{status}: {entity} -> {action} on {resource}:{instance}")
        print(f"  Reason: {reason}")
    
    # Step 7: View entity permissions
    print("\nStep 7: Viewing Entity Permissions")
    
    permissions = ac_manager.list_entity_permissions("assistant_agent_1")
    print(f"Permissions for assistant_agent_1:")
    print(f"  Roles: {permissions['roles']}")
    print(f"  Direct permissions: {len(permissions['direct_permissions'])}")
    print(f"  Effective permissions: {len(permissions['effective_permissions'])}")
    
    # Step 8: Create a secure communication bus
    print("\nStep 8: Creating a Secure Communication Bus")
    
    # Create an authentication service
    key_manager = KeyManager()
    auth_service = AuthenticationService(key_manager)
    
    # Create a secure bus that combines authentication and access control
    secure_bus = SecureCommunicationBus(
        broker=create_test_broker(),
        auth_service=auth_service,
        access_control_service=access_control_service,
        strict_mode=True  # Enforce strict security
    )
    
    print("Created secure communication bus with authentication and access control")
    
    # Step 9: Send messages through the secure bus
    print("\nStep 9: Sending Messages Through the Secure Bus")
    
    # Create and send an allowed message
    allowed_message = Message(
        content="Hello, this is an allowed message",
        sender_id="assistant_agent_1",
        recipient_id="user_agent_1"
    )
    
    message_id = secure_bus.send_message(allowed_message)
    print(f"Sent allowed message with ID: {message_id}")
    
    # Try to send a denied message (would be blocked in strict mode)
    try:
        denied_message = Message(
            content="This message should be denied",
            sender_id="assistant_agent_1",
            recipient_id="restricted_agent_1"
        )
        
        message_id = secure_bus.send_message(denied_message)
        print(f"Sent denied message with ID: {message_id}")
    except Exception as e:
        print(f"Message was denied as expected: {e}")
    
    print_separator()
    print("Access Control System Example Complete!")
    print("Configuration files created in the access_control_example directory.")

if __name__ == "__main__":
    main()
