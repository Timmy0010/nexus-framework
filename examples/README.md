# Nexus Framework Examples

This directory contains example scripts that demonstrate how to use the Nexus Advanced Agent Framework in various scenarios.

## Available Examples

### 1. Simple Conversation (`simple_conversation.py`)

This example demonstrates how to create a basic conversation between a user and an AI assistant agent. It shows both direct sequential chat and group chat capabilities.

To run:
```bash
python simple_conversation.py
```

### 2. MCP Tool Integration (`mcp_tool_integration.py`)

This example shows how to integrate with external tools using the Model Context Protocol (MCP) via mcp-desktop-commander. It demonstrates how an assistant agent can leverage external tools to enhance its capabilities.

**Prerequisites:** This example requires mcp-desktop-commander to be installed and properly configured with Claude Desktop.

To run:
```bash
python mcp_tool_integration.py
```

### 3. Task Planning and Execution (`task_planning.py`)

This example demonstrates how to use the PlannerAgent to break down complex tasks into manageable sub-tasks, and then distribute them to specialized ExecutorAgents for completion. It showcases the task management capabilities of the framework.

To run:
```bash
python task_planning.py
```

## Running the Examples

First, make sure you have the required dependencies installed:

```bash
# From the root directory of the project
pip install -e .
```

Then, navigate to the examples directory and run the desired example:

```bash
cd examples
python simple_conversation.py
```

## Notes

- These examples are simplified demonstrations and may use placeholder implementations for some components (e.g., LLM integration, tool execution).
- For real-world usage, you would replace these placeholder implementations with actual integrations to LLM APIs, external tools, etc.
- The examples are designed to be self-contained and easy to understand, showcasing the core concepts of the Nexus framework.
