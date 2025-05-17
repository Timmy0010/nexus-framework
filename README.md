# Nexus Advanced Agent Framework

A flexible, extensible framework for building and managing AI agent systems with enterprise-grade security and reliability.

## Overview

Nexus is a cutting-edge framework designed to empower developers to build, deploy, and manage sophisticated AI agents and multi-agent systems. It provides the foundational infrastructure for creating intelligent agents that can collaborate, reason, and interact with various tools and data sources to automate complex tasks and build next-generation software applications.

## Key Features

- **Modular Agent Architecture**: Build agents as independent, reusable modules with specialized skills.
- **Inter-Agent Communication**: Enable agents to discover each other's capabilities and interact through standardized protocols.
- **IDE Integration**: Expose agent capabilities as tools and resources, allowing direct interaction from environments like Claude Desktop and VSCode.
- **Flexible LLM Integration**: Support for multiple LLM providers with a unified interface.
- **Enterprise-Grade Security**: Comprehensive authentication, access control, and verification for agent interactions.
- **Reliable Message Infrastructure**: Guaranteed message delivery even during service disruptions.
- **Schema Validation**: Ensure message integrity through JSON schema validation.
- **Dynamic Rate Limiting**: Adaptive rate limiting based on service health metrics.
- **Comprehensive Observability**: Structured logging, monitoring, and distributed tracing to understand agent behavior.
- **Extensible by Design**: Plugin architecture for adding new agent types, LLM connectors, tools, and communication adapters.

## Getting Started

### Installation

```bash
pip install nexus-framework
```

### Basic Usage

Here's a simple example of creating and using agents with the Nexus framework:

```python
import nexus_framework as nf

# Configure logging
nf.configure_logging(log_level="INFO")

# Create a communication bus
comm_bus = nf.CommunicationBus()

# Create agents
user_agent = nf.UserProxyAgent(agent_name="User")
assistant_agent = nf.AssistantAgent(agent_name="Assistant")

# Register agents with the communication bus
comm_bus.register_agent(user_agent)
comm_bus.register_agent(assistant_agent)

# Create a group chat manager
chat_manager = nf.NexusGroupChatManager(
    agents=[user_agent, assistant_agent],
    communication_bus=comm_bus
)

# Start a conversation
messages = chat_manager.run_chat(
    initial_sender=user_agent,
    initial_message_content="Hello, can you help me with a question about Python?"
)

# Print the conversation
for msg in messages:
    sender = "User" if msg.sender_id == user_agent.agent_id else "Assistant"
    print(f"{sender}: {msg.content}")
```

## Advanced Usage

For more complex scenarios, Nexus supports:

- Task planning and decomposition
- Tool integration via the Model Context Protocol (MCP)
- Multi-agent collaboration for complex problem-solving
- Robust error handling and state management
- Comprehensive observability for debugging and monitoring

### Agent Team Builder

The Nexus Framework includes an Agent Team Builder that makes it easy to create and configure teams of specialized agents:

```python
from agent_team_builder import AgentTeamBuilder

# Initialize with configuration
builder = AgentTeamBuilder('agent_model_config.json')

# Define your team
team_config = [
    {"type": "UserProxy", "name": "Human Interface"},
    {"type": "Assistant", "name": "Orchestration & Operations Agent"},
    {"type": "Assistant", "name": "Data Processing Agent"}
]

# Build the team
agents = builder.build_team(team_config)

# Set up team communication
chat_manager = builder.create_chat_manager(agents)

# Start the conversation
user_proxy = builder.get_agent_by_name("Human Interface")
messages = builder.run_team_chat(
    chat_manager=chat_manager,
    initial_sender=user_proxy,
    initial_message="Let's solve this problem together."
)
```

### Secure Communication

Nexus provides enterprise-grade security features:

```python
from nexus_framework.security.authentication import create_authenticated_bus
from nexus_framework.security.access_control import AccessControlService, create_secure_bus

# Create a fully secured communication bus with both authentication and access control
secure_bus = create_secure_bus(
    broker=your_message_broker,
    config_path="./security_config",
    strict_mode=True  # Enforce strict security checks
)

# Register agents with automatic security wrapping
secure_bus.register_agent(agent)

# Send messages with automatic authentication and access control
secure_bus.send_message(message)
```

### Schema Validation

Nexus ensures message integrity through schema validation:

```python
from nexus_framework.validation.schema_registry import SchemaRegistry
from nexus_framework.middleware.schema_validation_middleware import validate_incoming, validate_outgoing

# Create schema registry
registry = SchemaRegistry()

# Register custom schemas if needed
registry.register_payload_schema("my_message_type", "1.0", my_schema)

# Use decorators to validate messages
@validate_incoming(registry, strict=True)
def handle_incoming_message(message):
    # Message is validated before reaching this function
    process_message(message)

@validate_outgoing(registry, strict=True)
def send_message(message):
    # Message is validated before being sent
    return bus.send_message(message)
```

### Message Verification and Sanitization

Nexus includes a VerificationAgent for security checks and content sanitization:

```python
from nexus_framework.agents.verification.verification_agent import VerificationAgent

# Create verification agent
verification_agent = VerificationAgent(config_path="./verification_config")

# Process a message through verification
result_message = verification_agent.process_message(message)

# If result is the original message, verification passed
if result_message is message:
    print("Message passed verification")
# If result is a different message, it may have been sanitized
elif result_message:
    print("Message was sanitized and now passes verification")
# If result is None, the message was rejected
else:
    print("Message was rejected")
```

### Adaptive Rate Limiting

Nexus provides health-aware rate limiting that adjusts based on service conditions:

```python
from nexus_framework.core.enhanced_rate_limiter import HealthAwareRateLimiter

# Create rate limiter
rate_limiter = HealthAwareRateLimiter()

# Configure limits for specific resources
rate_limiter.configure_limit("api_service", capacity=50, refill_rate=10.0)

# Configure health thresholds
rate_limiter.configure_health_thresholds("api_service", {
    "error_rate_degraded": 0.05,   # 5% errors -> degraded
    "response_time_degraded": 0.5  # 500ms -> degraded
})

# Execute function with rate limiting and health tracking
try:
    result = rate_limiter.execute_with_rate_limit(
        "api_service", 
        api_client.make_request, 
        *args, **kwargs
    )
except RateLimitExceededError:
    # Handle rate limiting
    pass
```

For detailed documentation and examples, visit the documentation in the `docs` folder:
- [Enhanced Roadmap](docs/ENHANCEMENT_ROADMAP.md)
- [Access Control System](docs/ACCESS_CONTROL_SYSTEM.md)
- [Implementation Summary](docs/IMPLEMENTATION_SUMMARY.md)

## Examples

Several examples are provided to help you get started:
- `examples/access_control_example.py`: Demonstrates the Access Control System
- `examples/schema_validation_example/schema_validation.py`: Shows schema validation in action
- `examples/verification_example/message_verification.py`: Demonstrates message verification
- `examples/rate_limiter_example/dynamic_rate_limiting.py`: Shows adaptive rate limiting
- `examples/reliable_team_example.py`: Shows how to build reliable agent teams
- `examples/document_processing_team.py`: Example of a document processing pipeline

Run the examples using the provided batch files:
```
run_access_control_example.bat
run_schema_validation_example.bat
run_verification_example.bat
run_rate_limiting_example.bat
run_reliable_team_example.bat
run_document_processing_example.bat
```

## Contributing

Contributions are welcome! Please see our [Contributing Guidelines](CONTRIBUTING.md) for more information.

## License

Nexus Framework is licensed under the MIT License. See the LICENSE file for details.
