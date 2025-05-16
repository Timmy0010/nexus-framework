# Nexus Advanced Agent Framework

A flexible, extensible framework for building and managing AI agent systems.

## Overview

Nexus is a cutting-edge framework designed to empower developers to build, deploy, and manage sophisticated AI agents and multi-agent systems. It provides the foundational infrastructure for creating intelligent agents that can collaborate, reason, and interact with various tools and data sources to automate complex tasks and build next-generation software applications.

## Key Features

- **Modular Agent Architecture**: Build agents as independent, reusable modules with specialized skills.
- **Inter-Agent Communication**: Enable agents to discover each other's capabilities and interact through standardized protocols.
- **IDE Integration**: Expose agent capabilities as tools and resources, allowing direct interaction from environments like Claude Desktop and VSCode.
- **Flexible LLM Integration**: Support for multiple LLM providers with a unified interface.
- **Robust Security**: Multi-layered security for authentication, authorization, and data protection.
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

The Nexus Framework now includes an Agent Team Builder that makes it easy to create and configure teams of specialized agents:

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

This makes it simple to create specialized teams for different tasks with appropriate model configurations for each agent.

For detailed documentation and examples, visit the [Nexus Framework Documentation](https://nexusframework.org/docs).

## Contributing

Contributions are welcome! Please see our [Contributing Guidelines](https://nexusframework.org/contributing) for more information.

## License

Nexus Framework is licensed under the MIT License. See the LICENSE file for details.
