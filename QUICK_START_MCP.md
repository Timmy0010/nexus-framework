# Nexus Framework MCP Integration - Quick Start Guide

This guide will help you quickly set up and use the Nexus Advanced Agent Framework with Model Context Protocol (MCP) integration to create powerful multi-agent systems that leverage Claude Desktop MCP tools.

## Prerequisites

- Python 3.9 or higher
- Claude Desktop installed
- Node.js installed (for fetch MCP server)
- Git (recommended)

## Installation

1. **Clone or download the repository**:
   ```
   git clone https://github.com/your-repo/nexus-framework.git
   cd nexus-framework
   ```

2. **Run the installation script**:
   - Double-click `install_nexus_mcp.bat` or run it from the command line:
   ```
   .\install_nexus_mcp.bat
   ```
   - Follow the on-screen instructions.
   - When prompted, decide whether to create a virtual environment.

3. **Verify installation**:
   - Run the test script:
   ```
   .\run_nexus_mcp_test.bat
   ```
   - This will test the connection to Claude's MCP servers and verify that the framework is installed correctly.

## Understanding MCP Integration

The Nexus Framework MCP integration allows your agents to:

1. **Access web resources** through Claude's fetch MCP server
2. **Query SQLite databases** through Claude's SQLite MCP server
3. **Interact with GitHub** through Claude's GitHub MCP server (if configured)

These capabilities are provided through custom MCP connectors that allow your Nexus agents to leverage the same tools that Claude uses.

## Running the Application

The application demonstrates several use cases:

1. **Start the app**:
   ```
   .\run_nexus_mcp_app.bat
   ```

2. **Observe the agent interactions**:
   - The app creates multiple agent groups, each using different MCP servers
   - Each group runs a chat to demonstrate a different capability
   - All interactions are logged in `nexus_app.log`

## Architecture

The integration consists of several components:

1. **ClaudeMCPWrapper**: Manages communication with Claude's MCP servers
2. **NexusMCPApplication**: Provides a high-level API for creating and managing agent groups
3. **Custom MCP Connector**: Adapts Nexus agents to use Claude's MCP tools

## Creating Your Own Agent Systems

To create your own agent systems with MCP integration:

1. **Define your agent structure**:
   ```python
   # Example: Creating a research team with web search capabilities
   servers_to_agents = {
       'fetch': [
           ('user', 'Human'),
           ('assistant', 'Research Assistant'),
           ('planner', 'Research Planner'),
           ('executor', 'Web Searcher')
       ]
   }
   ```

2. **Create an agent group**:
   ```python
   app = NexusMCPApplication()
   app.start_server('fetch')
   research_group = app.create_agent_group('research_team', servers_to_agents)
   ```

3. **Run a chat**:
   ```python
   messages = app.run_group_chat(
       'research_team',
       "Research question or task description",
       max_rounds=5
   )
   ```

4. **Process the results**:
   ```python
   app.print_chat_messages(messages)
   ```

## Advanced Configuration

### Using Different MCP Servers

The configuration automatically detects Claude's MCP servers from:
`C:\Users\<username>\AppData\Roaming\Claude\config.json`

You can specify a different configuration file when creating the application:
```python
app = NexusMCPApplication("path/to/config.json")
```

### Custom Agent Configuration

For more control over agent behavior, you can create agents with specific system prompts:

```python
# Directly using ClaudeMCPWrapper
wrapper = ClaudeMCPWrapper()
wrapper.start_mcp_server('fetch')

# Create a custom assistant with a specific system prompt
assistant = nf.AssistantAgent(
    agent_name="Specialized Assistant",
    system_prompt="You are a specialized assistant for financial analysis."
)

# Manually attach MCP capabilities
class CustomMCPConnector:
    def __init__(self, wrapper, server):
        self.wrapper = wrapper
        self.server = server
        self._tools_cache = None
        
    def list_tools(self):
        # Implementation
        pass
        
    def invoke_tool(self, tool_name, parameters):
        # Implementation
        pass
        
assistant.mcp_connector = CustomMCPConnector(wrapper, 'fetch')
```

## Troubleshooting

If you encounter issues:

1. **MCP server startup failures**:
   - Verify Claude Desktop is running
   - Check the paths in `nexus_mcp_config.json`
   - Ensure you have the necessary permissions

2. **Agent creation issues**:
   - Check the logs for detailed error messages
   - Verify all dependencies are installed correctly

3. **Tool access problems**:
   - Make sure your MCP servers are starting correctly
   - Verify that Claude Desktop has the tools you're trying to use

4. **Logs**:
   - Check `nexus_app.log` for detailed information

## Next Steps

- Explore the `examples` directory for more advanced use cases
- Check out the `LLM_INSTRUCTIONS.md` file for comprehensive documentation
- Modify the system prompts to create specialized agents for your use case
- Integrate with additional MCP servers or create your own tools

## Need Help?

- Submit an issue on GitHub
- Contribute improvements or bug fixes via pull requests
- Refer to the full documentation in the repository

Happy agent building!
