# Message Authentication System

## Overview

The Message Authentication System for the Nexus Framework provides secure message signing and verification capabilities to ensure message integrity and authenticity. It implements both HMAC-based message signing and JWT-based authentication and authorization.

## Features

- **HMAC Message Signing**: Sign and verify messages using HMAC-SHA256
- **JWT Authentication**: Create and validate JWT tokens for more complex authorization scenarios
- **Key Management**: Automatic key rotation, purging, backup, and restoration
- **Authentication Middleware**: Integrate authentication with message processing pipelines
- **Bus Integration**: Seamlessly integrate with the communication infrastructure

## Architecture

The authentication system consists of several components:

1. **Core Services**:
   - `KeyManager`: Manages cryptographic keys for signing and verification
   - `MessageSigner`: Signs and verifies messages using HMAC-SHA256
   - `JWTManager`: Creates and validates JWT tokens
   - `AuthenticationService`: Provides a unified interface for authentication operations

2. **Middleware**:
   - `AuthMiddleware`: Handles HMAC-based message authentication
   - `JWTAuthMiddleware`: Handles JWT-based authentication and authorization
   - `AuthenticationProcessor`: Combines both authentication approaches

3. **Integration**:
   - `AuthenticatedCommunicationBus`: Extends the reliable communication bus with authentication
   - `KeyRotationManager`: Manages automatic key rotation and synchronization

## Usage

### Basic Usage

```python
from nexus_framework.security.authentication import (
    AuthenticationService,
    SignatureError,
    AuthenticationError
)

# Create authentication service
auth_service = AuthenticationService()

# Sign a message
message_dict = message.to_dict()
signed_dict = auth_service.sign_message(message_dict)

# Verify a message
try:
    is_valid = auth_service.verify_message(signed_dict)
    if is_valid:
        print("Message verified successfully")
    else:
        print("Message verification failed")
except AuthenticationError as e:
    print(f"Authentication error: {e}")
```

### JWT Authentication

```python
from nexus_framework.security.authentication import (
    AuthenticationService
)

# Create authentication service
auth_service = AuthenticationService()

# Create a JWT token
subject = "agent_id"
claims = {
    "permissions": ["read", "write"],
    "role": "admin"
}
token = auth_service.create_token(subject, claims)

# Validate a token
is_valid, token_claims = auth_service.validate_token(token)
if is_valid:
    print(f"Token validated successfully for subject: {token_claims['sub']}")
else:
    print("Token validation failed")
```

### Using Middleware

```python
from nexus_framework.security.authentication import (
    AuthMiddleware,
    AuthenticationService
)

# Create authentication service and middleware
auth_service = AuthenticationService()
middleware = AuthMiddleware(auth_service, strict_mode=True)

# Define a message handler
def message_handler(message):
    # Process the message
    response = create_response(message)
    return response

# Wrap the handler with authentication
wrapped_handler = middleware.wrap_message_handler(message_handler)

# Use the wrapped handler
response = wrapped_handler(message)
```

### Integration with Communication Bus

```python
from nexus_framework.security.authentication import (
    create_authenticated_bus
)
from nexus_framework.messaging.rabbit_mq_broker import RabbitMQBroker

# Create and initialize broker
broker = RabbitMQBroker()
broker.initialize({
    'host': 'localhost',
    'port': 5672,
    'username': 'guest',
    'password': 'guest'
})

# Create authenticated communication bus
bus = create_authenticated_bus(
    broker=broker,
    keys_file="auth_keys.json",
    strict_mode=True,
    use_jwt=False
)

# Register agents with the bus
bus.register_agent(agent1)
bus.register_agent(agent2)

# Send authenticated messages
bus.send_message(message)
```

## Key Management

The system provides robust key management features:

### Key Rotation

Keys are automatically rotated based on a configurable interval. Old keys are kept for a grace period to validate incoming messages:

```python
# Rotate keys
new_key_id = auth_service.rotate_keys()

# Emergency rotation (invalidates all previous keys)
new_key_id = auth_service.emergency_rotation()
```

### Key Backup and Restoration

Keys can be backed up and restored:

```python
# Export keys
keys = auth_service.export_keys()

# Save to file
with open("auth_keys_backup.json", "w") as f:
    json.dump(keys, f, indent=2)

# Import key
auth_service.import_key(
    key_id="imported_key_id",
    key="imported_key_value",
    active=True
)
```

### Command-Line Key Management

The system includes a command-line utility for key management:

```
# Generate new keys
python key_manager_tool.py generate --output auth_keys.json --rotation-days 30

# Rotate keys
python key_manager_tool.py rotate --keys-file auth_keys.json

# Backup keys
python key_manager_tool.py backup --keys-file auth_keys.json --output backup.json

# Restore keys
python key_manager_tool.py restore --backup-file backup.json --output restored_keys.json

# List keys
python key_manager_tool.py list --keys-file auth_keys.json --verbose

# Purge expired keys
python key_manager_tool.py purge --keys-file auth_keys.json --grace-days 7

# Import a key
python key_manager_tool.py import --keys-file auth_keys.json --key-id "new_key" --key-value "..."
```

## Security Considerations

### Key Storage

The security of the authentication system depends on secure key storage. Consider the following:

1. **Store keys securely**: Use proper file permissions and encryption for key files.
2. **Limit access**: Only trusted services should have access to the keys.
3. **Backup keys**: Regularly backup keys to prevent data loss.
4. **Audit access**: Monitor and audit access to key files.

### Key Rotation

Regular key rotation improves security:

1. **Automate rotation**: Use the `KeyRotationManager` to automate key rotation.
2. **Handle emergencies**: Have procedures for emergency key rotation.
3. **Test rotation**: Regularly test key rotation procedures.

### Message Authentication

When implementing message authentication:

1. **Use strict mode**: Enable strict mode in production to reject unauthenticated messages.
2. **Exempt appropriate paths**: Configure exempt paths carefully.
3. **Monitor failures**: Track and alert on authentication failures.
4. **Use appropriate authentication**: Choose between HMAC and JWT based on your needs.

## Integration with Verification Agent

The Message Authentication System works well with the Verification Agent:

```python
from nexus_framework.security.authentication import AuthenticationService
from nexus_framework.security.verification_agent import VerificationAgent
from nexus_framework.security.validation_rules import PermissionValidator
from nexus_framework.communication.reliable_bus import ReliableCommunicationBus

# Create authentication service
auth_service = AuthenticationService()

# Create verification agent
verification_agent = VerificationAgent(agent_name="SecurityGateway")

# Register authentication-related validators
verification_agent.register_validator(PermissionValidator(
    acl={
        # ACL configuration
    }
))

# Create communication bus with authentication
bus = create_authenticated_bus(broker, "auth_keys.json", strict_mode=True)

# Register verification agent with the bus
bus.register_agent(verification_agent)

# Configure routing to ensure messages pass through verification
# ...
```

## Best Practices

1. **Use strict mode in production**: Reject invalid messages to prevent security breaches.
2. **Implement proper key management**: Rotate keys regularly and store them securely.
3. **Choose the right authentication method**: Use HMAC for simple integrity checks and JWT for authorization.
4. **Monitor authentication failures**: Set up alerting for authentication failures.
5. **Integrate with other security components**: Combine with the Verification Agent for comprehensive security.
6. **Test authentication under failure conditions**: Ensure the system handles failures gracefully.
7. **Document key rotation procedures**: Have clear procedures for key management.
8. **Use different keys for different environments**: Use separate keys for development, testing, and production.

## Technical Details

### Message Signing Format

When a message is signed, the following fields are added:

```json
{
  "signature": "hmac-sha256-signature-hex-string",
  "signature_metadata": {
    "key_id": "id-of-key-used-for-signing",
    "algorithm": "hmac-sha256",
    "timestamp": 1621234567.89
  }
}
```

### JWT Token Format

JWT tokens follow the standard JWT format:

```
header.payload.signature
```

- **Header**: Contains the algorithm and key ID
- **Payload**: Contains the subject, expiration, and custom claims
- **Signature**: HMAC-SHA256 signature of the header and payload

### Key Storage Format

Keys are stored in the following format:

```json
{
  "key-id-1": {
    "key": "base64-encoded-key",
    "created_at": 1621234567.89,
    "expires_at": 1624234567.89,
    "active": true
  },
  "key-id-2": {
    "key": "base64-encoded-key",
    "created_at": 1622234567.89,
    "expires_at": 1625234567.89,
    "active": false
  }
}
```

## Conclusion

The Message Authentication System provides a robust, flexible foundation for securing message exchanges in the Nexus Framework. By ensuring message integrity and authenticity, it helps prevent message tampering, replay attacks, and unauthorized access.

For more advanced security features, combine this system with the Verification Agent and Access Control System to create a comprehensive security framework.
