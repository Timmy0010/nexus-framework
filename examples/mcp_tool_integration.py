"""
Example of using the MCP connector to access external tools.

This script demonstrates how to set up the MCPConnector and use it to
integrate with external tools via mcp-desktop-commander.
"""

import logging
import sys
import os

# Add the parent directory to the Python path so we can import the framework
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from nexus_framework import (
    configure_logging,
    AssistantAgent,
    UserProxyAgent,
    MCPConnector,
    CommunicationBus,
    SecurityManager
)


def main():
    """Run a demonstration of MCP tool integration."""
    # Configure logging
    configure_logging(log_level=logging.INFO, console=True)
    
    print("Nexus Framework MCP Tool Integration Example")
    print("===========================================")
    print()
    print("This example demonstrates how to integrate with external tools")
    print("via the Model Context Protocol (MCP) using mcp-desktop-commander.")
    print()
    print("NOTE: This example requires mcp-desktop-commander to be installed")
    print("and properly configured with Claude Desktop.")
    print()
    
    # Check if mcp-desktop-commander is in the PATH
    try:
        # Create an MCP connector
        print("Initializing MCP connector...")
        mcp_connector = MCPConnector()
        print("MCP connector initialized successfully.")
    except Exception as e:
        print(f"Error initializing MCP connector: {e}")
        print("Please ensure mcp-desktop-commander is installed and in your PATH.")
        return
    
    # Set up security manager for tool access control
    security_manager = SecurityManager()
    
    # Create a communication bus
    comm_bus = CommunicationBus()
    
    # Create agents
    print("Creating agents...")
    
    # User proxy agent for interaction
    user_agent = UserProxyAgent(
        agent_name="User",
        user_input_callback=lambda prompt: input(f"{prompt} "),
        user_output_callback=lambda content: print(f"Assistant: {content}")
    )
    
    # Assistant agent with MCP connector for tool access
    assistant_agent = AssistantAgent(
        agent_name="Tool-using Assistant",
        system_prompt=(
            "You are a helpful assistant that can use external tools. "
            "When appropriate, you should suggest using a tool to help answer questions."
        ),
        mcp_connector=mcp_connector
    )
    
    # Register agents with the communication bus
    comm_bus.register_agent(user_agent)
    comm_bus.register_agent(assistant_agent)
    
    # Grant the assistant agent permission to use all tools
    security_manager.set_tool_acl(assistant_agent.agent_id, ["*"])
    
    # List available tools
    try:
        print("\nQuerying available MCP tools...")
        tools = mcp_connector.list_tools()
        print(f"Found {len(tools)} MCP tools:")
        for i, tool in enumerate(tools, 1):
            print(f"  {i}. {tool.get('name')} - {tool.get('description', 'No description')}")
    except Exception as e:
        print(f"Error listing MCP tools: {e}")
        print("Continuing with example, but tool usage may not work correctly.")
    
    print("\nStarting conversation with the assistant.")
    print("You can ask questions that might require tool usage, such as:")
    print("  - \"What's the weather like in New York?\"")
    print("  - \"Search for the latest news about AI.\"")
    print("  - \"Can you help me analyze this data?\"")
    print("Type 'exit', 'quit', or 'end' to terminate the conversation.")
    
    # Start a conversation with the assistant
    conversation = user_agent.initiate_chat(
        recipient=assistant_agent,
        initial_message_content="Hello! I'm looking for some help with tasks that might need external tools."
    )
    
    print("\nConversation summary:")
    for i, msg in enumerate(conversation):
        sender = "User" if msg.sender_id == user_agent.agent_id else "Assistant"
        
        # Format content based on type
        if isinstance(msg.content, dict):
            import json
            content = json.dumps(msg.content, indent=2)
        else:
            content = str(msg.content)
        
        # Show truncated content for long messages
        if len(content) > 100:
            displayed_content = content[:100] + "..."
        else:
            displayed_content = content
        
        print(f"{i+1}. {sender} ({msg.role or 'message'}): {displayed_content}")
    
    print("\nThank you for trying the Nexus Framework MCP integration!")


if __name__ == "__main__":
    main()
