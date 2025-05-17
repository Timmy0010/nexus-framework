# Nexus Framework Access Control System

This document provides an overview of the Access Control System implemented in the Nexus Framework, which provides robust security and authorization capabilities.

## Overview

The Access Control System (Phase 3.3) provides a comprehensive security layer for the Nexus Framework, building on the Authentication System (Phase 3.2). It implements a hierarchical permission model with multiple authorization strategies:

1. **Role-Based Access Control (RBAC)** - Assign roles to entities and manage permissions through roles
2. **Policy-Based Access Control** - Define flexible policies for permission decisions based on context
3. **Access Control Lists (ACLs)** - Provide fine-grained and temporary permissions for specific resources

## Core Components

### Permission Model

Permissions are defined using a consistent structure:
- **Resource Type**: What kind of resource is being accessed (agent, message, tool, etc.)
- **Action**: What action is being performed (create, read, update, delete, execute, etc.) 
- **Instance**: Optional specific resource instance the permission applies to

Example permissions:
```
agent:read:assistant1  # Permission to read the assistant1 agent
message:create:*       # Permission to create any message
tool:execute:calculator # Permission to execute the calculator tool
```

### Roles

Roles are named collections of permissions that can be assigned to entities. The system provides several default roles:

- **Admin**: Full system access
- **User**: Standard access with common permissions
- **Observer**: Read-only access
- **Agent**: Standard permissions for agents
- **Tool**: Limited permissions for tools
- **Service**: Higher-level permissions for system services
- **System**: System-level permissions

Roles can inherit permissions from other roles, creating a hierarchical structure.

### Policies

Policies provide a flexible way to define authorization rules based on various context conditions. Key policy elements:

- **Effect**: Allow or deny
- **Resource Patterns**: Patterns of resources this policy applies to
- **Action Patterns**: Patterns of actions this policy applies to
- **Entity Patterns**: Patterns of entities this policy applies to
- **Conditions**: Additional context-based conditions
- **Priority**: Used to resolve conflicts between policies

### Access Control Lists (ACLs)

ACLs provide fine-grained permission management, including:
- **Time-based permissions**: Grant temporary access that expires automatically
- **Resource-specific permissions**: Grant permissions for specific resource instances
- **Direct entity permissions**: Assign permissions directly to entities without roles

## Integration with Authentication

The Access Control System integrates seamlessly with the Authentication System (Phase 3.2):

- **Combined Middleware**: A unified security pipeline that handles both authentication and authorization
- **JWT Claims Support**: Using JWT claims for authorization decisions
- **Message Metadata**: Security metadata attached to messages for audit trails

## Usage Examples

### Creating a Custom Role

```python
from nexus_framework.security.access_control import (
    Role, PermissionSet, Permission,
    ResourceType, ResourceAction
)

# Create permissions
read_agents = Permission(ResourceType.AGENT, ResourceAction.READ)
execute_tools = Permission(ResourceType.TOOL, ResourceAction.EXECUTE, "calculator")

# Create permission set
perms = PermissionSet([read_agents, execute_tools])

# Create role
assistant_role = Role(
    name="assistant_role",
    description="Role for assistant agents",
    permissions=perms,
    parent_roles=["agent"]  # Inherit from base agent role
)
```

### Using the Access Control Manager

```python
from nexus_framework.security.access_control import AccessControlManager, AccessControlService

# Create service and manager
ac_service = AccessControlService(config_path="./config")
ac_manager = AccessControlManager(ac_service)

# Create a role using the manager
ac_manager.create_role(
    name="custom_role",
    description="Custom role for special agents",
    permissions=[
        "agent:read:*",
        "message:create:*",
        "tool:execute:calculator"
    ],
    parent_roles=["agent"]
)

# Assign a role to an entity
ac_manager.assign_role_to_entity("agent_123", "custom_role")

# Grant a specific permission via ACL
ac_manager.grant_acl_permission(
    entity_id="agent_123",
    resource_type="tool",
    action="execute",
    resource_id="special_tool",
    expires_in=3600  # Permission expires in 1 hour
)

# Check permissions
allowed, reason = ac_manager.check_permission(
    entity_id="agent_123",
    resource_type="tool",
    action="execute",
    resource_id="calculator"
)
print(f"Is allowed: {allowed}, Reason: {reason}")
```

### Setting Up a Secure Communication Bus

```python
from nexus_framework.security.access_control import create_secure_bus
from nexus_framework.security.authentication import AuthenticationService, KeyManager

# Create authentication service
key_manager = KeyManager()
auth_service = AuthenticationService(key_manager)

# Create secure bus with both authentication and access control
secure_bus = create_secure_bus(
    broker=your_broker,
    auth_service=auth_service,
    config_path="./config",
    strict_mode=True  # Enforce strict security
)

# Send a message through the secure bus
# (authentication and access control are handled automatically)
message_id = secure_bus.send_message(message)
```

## Configuration

Configuration can be stored in JSON files for persistence:

- **roles.json**: Role definitions and assignments
- **policies.json**: Policy definitions and settings
- **acls.json**: Access control list entries

The `AccessControlService` can automatically load and save configurations:

```python
# Create service with configuration path
ac_service = AccessControlService(config_path="./config")

# Create default configuration
ac_service.create_default_configuration()

# Later, save any changes
ac_service.save_configuration()
```

## Security Best Practices

When using the Access Control System, follow these best practices:

1. **Principle of Least Privilege**: Grant only the minimum permissions necessary
2. **Role Hierarchy**: Use role inheritance to create a logical permission hierarchy
3. **Prefer Roles over Direct Permissions**: Manage permissions through roles for better maintainability
4. **Use Time-Limited Permissions**: For elevated access, use time-limited ACL entries
5. **Audit Permission Changes**: Log and review permission changes
6. **Enable Strict Mode**: In production, use strict mode to enforce security

## Advanced Features

### Dynamic Permission Checks

You can perform dynamic permission checks based on message content or other context:

```python
from nexus_framework.security.access_control import PolicyContext

# Create custom policy context
context = PolicyContext(
    entity_id="agent_123",
    resource_type="tool",
    resource_id="calculator",
    action="execute",
    additional_context={
        "payload_size": len(message.payload),
        "message_priority": message.metadata.get("priority"),
        "user_id": message.metadata.get("user_id")
    }
)

# Check permission with context
allowed = policy_manager.is_allowed(
    entity_id=context.entity_id,
    resource_type=context.resource_type,
    resource_id=context.resource_id,
    action=context.action,
    context_data=context.to_dict()
)
```

### Custom Policies

You can create sophisticated policies with custom conditions:

```python
from nexus_framework.security.access_control import Policy, EffectType

# Create a policy that allows access only during business hours
business_hours_policy = Policy(
    name="business_hours_only",
    description="Allow access only during business hours",
    effect=EffectType.ALLOW,
    resource_patterns=["data:*"],
    action_patterns=["read", "write"],
    entity_patterns=["user_*"],
    conditions={
        "additional_context.time_of_day": lambda x: 9 <= x.hour < 17,
        "additional_context.day_of_week": lambda x: x < 5  # Monday-Friday
    },
    priority=500
)
```

## Integration with Next Steps

The Access Control System provides the foundation for future security enhancements:

1. **Verification Agent (Phase 3.1)**: Will use the permission model for content verification
2. **Schema Validation (Phase 2.3)**: Will integrate with access control for message validation
3. **Rate Limiting (Phase 4.3)**: Will use permissions for rate limit prioritization
