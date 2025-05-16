# Nexus Framework MCP Integration

This extension to the Nexus Advanced Agent Framework enables seamless integration with Claude Desktop's MCP (Model Context Protocol) tools, allowing your agents to access web resources, databases, GitHub repositories, and more through Claude's MCP servers.

## Overview

The Nexus MCP Integration provides:

1. **Claude MCP Access**: Connect to Claude Desktop's built-in MCP servers
2. **Multi-Agent Orchestration**: Create groups of specialized agents that collaborate on complex tasks
3. **Tool-Enhanced Agents**: Equip your agents with web search, database access, and code repository management capabilities
4. **Standardized Communication**: Leverage Nexus's robust communication infrastructure with MCP tool access

This integration bridges the gap between Nexus's powerful agent framework and Claude's MCP tools, creating a comprehensive environment for building sophisticated AI systems.

## Features

- **MCP Server Management**: Start, stop, and interact with Claude's MCP servers
- **Custom MCP Connectors**: Seamless adaptation between Nexus agents and MCP tools
- **Agent Group Creation**: Build specialized teams of agents with different tool access
- **Chat Orchestration**: Run structured conversations between agents with MCP capabilities
- **Comprehensive Logging**: Track all agent interactions and tool usage
- **Easy Setup**: Simple installation and configuration process

## Installation

### Prerequisites

- Python 3.9 or higher
- Claude Desktop installed
- Node.js installed (for fetch MCP server)

### Quick Install

1. Run the installation script:
   ```
   .\install_nexus_mcp.bat
   ```

2. Follow the on-screen instructions to complete the installation.

3. Create a desktop shortcut (optional):
   ```
   .\create_desktop_shortcut.bat
   ```

4. Start the application:
   ```
   .\start_nexus_mcp.bat
   ```

For detailed instructions, see [QUICK_START_MCP.md](QUICK_START_MCP.md).

## Architecture

### Components

1. **ClaudeMCPWrapper**: Core integration with Claude's MCP servers
   - Manages server processes
   - Routes MCP requests/responses
   - Provides custom MCP connectors for agents

2. **NexusMCPApplication**: High-level application framework
   - Creates and manages agent groups
   - Orchestrates chats with MCP-enabled agents
   - Handles startup/shutdown of MCP servers

3. **Custom MCP Connectors**: Bridge between agents and MCP
   - List available tools from MCP servers
   - Invoke tools with appropriate parameters
   - Handle tool responses

4. **Agent Groups**: Specialized teams for different tasks
   - Research teams for web search
   - Database teams for data analysis
   - Development teams for coding tasks

### Workflow

1. **Server Initialization**: MCP servers are started based on configuration
2. **Agent Creation**: Specialized agents are created with MCP capabilities
3. **Group Formation**: Agents are organized into functional groups
4. **Task Execution**: Groups execute tasks with seamless MCP tool access
5. **Result Processing**: Results are collected, formatted, and presented

## Example Usage

### Basic Research Team

```python
# Create the application
app = NexusMCPApplication()

# Start the fetch MCP server for web access
app.start_server('fetch')

# Define the research team structure
servers_to_agents = {
    'fetch': [
        ('user', 'Human'),
        ('assistant', 'Research Assistant'),
        ('planner', 'Research Planner'),
        ('executor', 'Web Searcher')
    ]
}

# Create the research team
research_group = app.create_agent_group('research_team', servers_to_agents)

# Run a research task
messages = app.run_group_chat(
    'research_team',
    "Research the latest developments in AI agent frameworks",
    max_rounds=5
)

# Print the results
app.print_chat_messages(messages)

# Shutdown when done
app.shutdown()
```

### Multi-Tool Development Team

```python
# Create the application
app = NexusMCPApplication()

# Start multiple MCP servers
app.start_server('fetch')    # For web access
app.start_server('sqlite')   # For database access
app.start_server('github')   # For code repository access

# Define a development team with diverse capabilities
servers_to_agents = {
    'fetch': [
        ('user', 'Developer'),
        ('assistant', 'Programming Assistant')
    ],
    'sqlite': [
        ('executor', 'Database Manager')
    ],
    'github': [
        ('executor', 'Code Repository Manager')
    ]
}

# Create the development team
dev_group = app.create_agent_group('development_team', servers_to_agents)

# Run a development task
messages = app.run_group_chat(
    'development_team',
    "Develop a feature that requires web API access, database storage, and code repository management",
    max_rounds=10
)

# Process the results
app.print_chat_messages(messages)

# Shutdown when done
app.shutdown()
```

## Configuration

### MCP Servers

The MCP integration automatically detects servers from Claude's configuration at:
`C:\Users\<username>\AppData\Roaming\Claude\config.json`

You can also provide a custom configuration file:

```python
app = NexusMCPApplication("path/to/custom_config.json")
```

Example configuration:
```json
{
  "mcp_servers": {
    "fetch": {
      "command": "node",
      "args": [
        "C:\\Users\\username\\AppData\\Local\\AnthropicClaude\\app-0.9.3\\fetch-mcp\\dist\\index.js"
      ]
    },
    "sqlite": {
      "command": "uvx",
      "args": [
        "mcp-server-sqlite",
        "--db-path",
        "C:\\Users\\username\\TestSQLbase.db"
      ]
    }
  }
}
```

## Troubleshooting

### Common Issues

1. **MCP Server Start Failures**:
   - Ensure Claude Desktop is installed and running
   - Verify the paths in your configuration match your system
   - Check that required dependencies (Node.js, uvx) are installed

2. **Tool Access Problems**:
   - Make sure the necessary MCP servers are running
   - Check the agent is correctly configured with the MCP connector
   - Verify the tool exists in the MCP server's capabilities

3. **Agent Communication Issues**:
   - Ensure all agents are registered with the CommunicationBus
   - Check that the chat manager has all the required agents
   - Verify the message format matches what agents expect

### Logs

Check `nexus_app.log` for detailed information about:
- MCP server startup/shutdown
- Tool invocations and responses
- Agent messages and errors
- Application workflow

## Contributing

Contributions to the Nexus MCP Integration are welcome! Please see our [Contributing Guidelines](CONTRIBUTING.md) for more information.

## License

This integration is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Acknowledgements

- The Nexus Framework Team for the core agent system
- Anthropic for Claude Desktop and the MCP tools
- Contributors to the open-source libraries that make this integration possible
