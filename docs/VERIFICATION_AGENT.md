# Nexus Framework VerificationAgent

## Overview

The VerificationAgent is a security-focused component of the Nexus Framework that validates and sanitizes messages before they are processed by other agents in the system. It acts as a gatekeeper, ensuring that all messages meet defined security and validity requirements.

## Features

- **Message Validation**: Checks messages against predefined rules and schemas
- **Content Sanitization**: Removes or modifies potentially harmful content
- **Plugin Architecture**: Extensible design with pluggable validators and sanitizers
- **Configuration-Driven**: Easy setup through YAML configuration files
- **Integration with Messaging**: Seamlessly integrates with the Nexus messaging infrastructure

## Components

### Core Components

- **VerificationAgent**: The main agent class that coordinates validation and sanitization
- **ValidationRule**: Abstract base class for all validation rules
- **SanitizationRule**: Abstract base class for all sanitization rules
- **ValidationResult**: Class representing the result of message validation

### Validators

- **SchemaValidator**: Validates messages against JSON schemas
- **SizeValidator**: Validates messages against size constraints
- **ContentValidator**: Validates message content against patterns and rules
- **PermissionValidator**: Validates sender permissions for accessing specific resources or recipients
- **RateLimitValidator**: Validates messages against rate limits for senders

### Sanitizers

- **SizeLimitSanitizer**: Sanitizes messages by applying size limits
- **ContentFilterSanitizer**: Sanitizes message content by filtering out inappropriate content
- **JsonSanitizer**: Sanitizes JSON content for security
- **RecursiveDepthSanitizer**: Limits the nesting depth of recursive structures to prevent DoS attacks

## Usage

### Basic Usage

```python
from nexus_framework.security import (
    VerificationAgent,
    SchemaValidator,
    ContentValidator,
    SizeLimitSanitizer
)

# Create a verification agent
agent = VerificationAgent(agent_name="SecurityGateway")

# Register validators
agent.register_validator(SchemaValidator())
agent.register_validator(ContentValidator(
    forbidden_patterns=["password=", "api_key="],
    allowed_domains=["example.com", "github.com"]
))

# Register sanitizers
agent.register_sanitizer(SizeLimitSanitizer(
    max_content_length=10000,
    max_field_lengths={"content.text": 5000}
))

# Process a message
result = agent.process_message(message)
if result:
    print("Message passed verification and was sanitized")
else:
    print("Message was rejected")
```

### Configuration-Based Setup

For production use, it's recommended to use configuration files to set up the VerificationAgent:

```python
from nexus_framework.security.verification_agent_utils import create_verification_agent

# Create a verification agent from configuration
agent = create_verification_agent("config/verification_agent_config.yml")

# Now the agent is ready to use
# ...
```

### Integration with Communication Bus

To integrate the VerificationAgent with the Nexus messaging infrastructure:

```python
from nexus_framework.security.verification_agent_utils import (
    create_verification_agent,
    integrate_with_communication_bus
)
from nexus_framework.communication.reliable_bus import ReliableCommunicationBus
from nexus_framework.messaging.rabbit_mq_broker import RabbitMQBroker

# Create a verification agent from configuration
agent = create_verification_agent("config/verification_agent_config.yml")

# Initialize the broker
broker = RabbitMQBroker()
broker.initialize({
    'host': 'localhost',
    'port': 5672,
    'username': 'guest',
    'password': 'guest'
})

# Create communication bus with the broker
bus = ReliableCommunicationBus(broker=broker)

# Integrate the verification agent with the communication bus
integrate_with_communication_bus(agent, bus)

# Now all messages will pass through the verification agent
```

## Configuration

The VerificationAgent is highly configurable through YAML configuration files. Here's an example configuration:

```yaml
# Agent configuration
agent_name: SecurityGateway
role: security

# Validation rules
validators:
  - type: schema
    enabled: true
    priority: 10
    description: Validates message schema
    params:
      # Using default schemas from schemas.py

  - type: size
    enabled: true
    priority: 20
    description: Validates message size constraints
    params:
      max_message_size: 1048576  # 1MB
      max_content_size: 524288   # 512KB 
      max_metadata_size: 16384   # 16KB

  # More validators...

# Sanitization rules
sanitizers:
  - type: size_limit
    enabled: true
    priority: 10
    description: Limits size of messages
    params:
      max_content_length: 100000
      max_field_lengths:
        content.text: 50000
        content.subject: 500

  # More sanitizers...
```

## Extending

### Creating Custom Validators

To create a custom validator, extend the `ValidationRule` class:

```python
from nexus_framework.security import ValidationRule

class MyCustomValidator(ValidationRule):
    def __init__(self, name="MyCustomValidator", description="", my_param=None):
        super().__init__(name, description)
        self.my_param = my_param
    
    def validate(self, message):
        # Implement validation logic
        # Return (is_valid, error_message)
        if some_condition:
            return True, None
        else:
            return False, "Validation failed because..."
```

### Creating Custom Sanitizers

To create a custom sanitizer, extend the `SanitizationRule` class:

```python
from nexus_framework.security import SanitizationRule

class MyCustomSanitizer(SanitizationRule):
    def __init__(self, name="MyCustomSanitizer", description="", my_param=None):
        super().__init__(name, description)
        self.my_param = my_param
    
    def sanitize(self, message):
        # Implement sanitization logic
        # Return the sanitized message
        sanitized_message = message.copy()
        # Modify sanitized_message...
        return sanitized_message
```

## Best Practices

1. **Configure validators and sanitizers in the right order**:
   - Schema validation should come first
   - Size limitations should be applied early
   - Content filtering should come after basic validations

2. **Use appropriate error messages**:
   - Error messages should be informative but not reveal sensitive information
   - Include enough context for debugging but not implementation details

3. **Test with malicious inputs**:
   - Oversized payloads
   - Malformed message structures
   - Messages with potentially harmful content
   - Unauthorized sender/recipient combinations

4. **Monitor validation failures**:
   - Set up logging for rejected messages
   - Track validation statistics to identify potential attacks
   - Configure alerts for unusual validation failure patterns

## Contributing

Contributions to the VerificationAgent are welcome! Here are some ways to contribute:

- Add new validators for specific security concerns
- Add new sanitizers for handling different content types
- Improve performance of existing validators and sanitizers
- Enhance the configuration system
- Add support for new message types

Please follow the project's coding standards and include tests for new functionality.

## License

This component is part of the Nexus Framework and is licensed under the same terms as the framework itself.
