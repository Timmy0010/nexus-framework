# Getting Started

This guide will help you get started with the Nexus Framework, from installation to creating your first agent system.

## Installation

You can install the Nexus Framework using pip:

```bash
pip install nexus-framework
```

For development, you can clone the repository and install it in development mode:

```bash
git clone https://github.com/yourusername/nexus-framework.git
cd nexus-framework
pip install -e .
```

## Requirements

- Python 3.9 or higher
- Dependencies listed in `requirements.txt`

## Basic Example

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

## Next Steps

Now that you have a basic understanding of how to use the Nexus Framework, you can:

1. Learn about the [different types of agents](agents.md) available in the framework
2. Explore [inter-agent communication](communication.md) patterns
3. Understand how to use the [task management](task_management.md) system
4. See how to [integrate with external tools](mcp_integration.md) using MCP
5. Check out the [examples](examples.md) for more advanced usage patterns

## Development Setup

If you're planning to contribute to the Nexus Framework, you'll need to set up a development environment:

```bash
# Clone the repository
git clone https://github.com/yourusername/nexus-framework.git
cd nexus-framework

# Create a virtual environment
python -m venv .venv

# Activate the virtual environment
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest
```
