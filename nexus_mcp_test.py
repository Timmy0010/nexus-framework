"""
Nexus MCP Test Script

This script demonstrates how to set up and use the Nexus Framework with MCP integration.
"""

import logging
import sys
import nexus_framework as nf
from nexus_framework.tools.mcp_connector import MCPConnector
import subprocess
import json
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_mcp_commander_path():
    """Try to locate mcp-desktop-commander"""
    try:
        # Check if available in the Claude app's directory
        claude_app_path = os.path.expanduser("C:\\Users\\thohn\\AppData\\Local\\AnthropicClaude\\app-0.9.3")
        
        logger.info(f"Looking for mcp-desktop-commander in: {claude_app_path}")
        
        # Try different possible locations
        candidate_paths = [
            os.path.join(claude_app_path, "resources", "bin", "mcp-desktop-commander.exe"),
            os.path.join(claude_app_path, "resources", "bin", "mcp-desktop-commander"),
            os.path.join(claude_app_path, "mcp-desktop-commander.exe"),
            os.path.join(claude_app_path, "mcp-desktop-commander"),
        ]
        
        for path in candidate_paths:
            if os.path.exists(path):
                logger.info(f"Found mcp-desktop-commander at: {path}")
                return path
                
        # If not found in Claude's directory, check if it's in PATH
        result = subprocess.run(
            ["where", "mcp-desktop-commander"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        if result.returncode == 0 and result.stdout.strip():
            path = result.stdout.strip().split("\n")[0]
            logger.info(f"Found mcp-desktop-commander in PATH: {path}")
            return path
            
        # If not found, try to use the node.js approach from the config
        logger.info("mcp-desktop-commander not found, trying node.js approach")
        return "node C:\\Users\\thohn\\AppData\\Local\\AnthropicClaude\\app-0.9.3\\fetch-mcp\\dist\\index.js"
    except Exception as e:
        logger.error(f"Error finding mcp-desktop-commander: {e}")
        return None

def test_sqlite_mcp_server():
    """Test connecting to the SQLite MCP server"""
    logger.info("Testing SQLite MCP server...")
    
    try:
        # Check if uvx is available
        result = subprocess.run(
            ["where", "uvx"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        if result.returncode != 0:
            logger.error("uvx command not found, skipping SQLite MCP server test")
            return False
            
        # The command from Claude's config.json
        cmd = ["uvx", "mcp-server-sqlite", "--db-path", "C:\\Users\\thohn\\TestSQLbase.db"]
        
        # Try to start the process with a timeout
        logger.info("Starting SQLite MCP server process...")
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait a bit for the server to start
        import time
        time.sleep(2)
        
        # Check if the process is still running
        if process.poll() is not None:
            logger.error(f"SQLite MCP server process exited with code {process.poll()}")
            stderr = process.stderr.read()
            logger.error(f"Error output: {stderr}")
            return False
        
        logger.info("SQLite MCP server appears to be running")
        
        # Terminate the process
        process.terminate()
        
        logger.info("SQLite MCP server test completed")
        return True
    except Exception as e:
        logger.error(f"Error testing SQLite MCP server: {e}")
        return False

def test_fetch_mcp_server():
    """Test connecting to the Fetch MCP server"""
    logger.info("Testing Fetch MCP server...")
    
    try:
        # Check if node is available
        result = subprocess.run(
            ["where", "node"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        if result.returncode != 0:
            logger.error("node command not found, skipping Fetch MCP server test")
            return False
            
        # Check if the script exists
        fetch_script_path = "C:\\Users\\thohn\\AppData\\Local\\AnthropicClaude\\app-0.9.3\\fetch-mcp\\dist\\index.js"
        if not os.path.exists(fetch_script_path):
            logger.error(f"Fetch MCP script not found at {fetch_script_path}")
            return False
            
        # The command from Claude's config.json
        cmd = ["node", fetch_script_path]
        
        # Try to start the process with a timeout
        logger.info("Starting Fetch MCP server process...")
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait a bit for the server to start
        import time
        time.sleep(2)
        
        # Check if the process is still running
        if process.poll() is not None:
            logger.error(f"Fetch MCP server process exited with code {process.poll()}")
            stderr = process.stderr.read()
            logger.error(f"Error output: {stderr}")
            return False
        
        logger.info("Fetch MCP server appears to be running")
        
        # Terminate the process
        process.terminate()
        
        logger.info("Fetch MCP server test completed")
        return True
    except Exception as e:
        logger.error(f"Error testing Fetch MCP server: {e}")
        return False

def main():
    """Main function to demonstrate Nexus Framework with MCP integration"""
    logger.info("Starting Nexus MCP integration test...")
    
    # Test SQLite MCP server
    sqlite_mcp_working = test_sqlite_mcp_server()
    
    # Test Fetch MCP server
    fetch_mcp_working = test_fetch_mcp_server()
    
    if not sqlite_mcp_working and not fetch_mcp_working:
        logger.error("No MCP servers are working. Exiting.")
        return
        
    # Set up the right MCP connector based on working servers
    mcp_connector = None
    
    try:
        # Find mcp-desktop-commander
        mcp_commander_path = get_mcp_commander_path()
        
        if mcp_commander_path:
            logger.info(f"Using MCP commander path: {mcp_commander_path}")
            mcp_connector = MCPConnector(mcp_commander_path=mcp_commander_path)
            
            # Try to list tools
            logger.info("Listing MCP tools...")
            tools = mcp_connector.list_tools()
            logger.info(f"Found {len(tools)} tools")
            
            for i, tool in enumerate(tools):
                logger.info(f"Tool {i+1}: {tool.get('name')} - {tool.get('description')}")
        else:
            logger.error("Could not find mcp-desktop-commander. MCP integration will not work.")
    except Exception as e:
        logger.error(f"Error setting up MCP connector: {e}")
    
    # Create agents
    logger.info("Creating agents...")
    
    # Configure logging
    nf.configure_logging(log_level="INFO")
    
    # Create a communication bus
    comm_bus = nf.CommunicationBus()
    
    # Create agents
    user_agent = nf.UserProxyAgent(agent_name="User")
    
    # Create an assistant agent with MCP tool access if available
    assistant_kwargs = {"agent_name": "Assistant"}
    if mcp_connector:
        assistant_kwargs["mcp_connector"] = mcp_connector
        
    assistant_agent = nf.AssistantAgent(**assistant_kwargs)
    
    # Register agents with the communication bus
    comm_bus.register_agent(user_agent)
    comm_bus.register_agent(assistant_agent)
    
    # Create a group chat manager
    chat_manager = nf.NexusGroupChatManager(
        agents=[user_agent, assistant_agent],
        communication_bus=comm_bus
    )
    
    logger.info("Setup complete. Nexus Framework is now integrated with MCP.")
    logger.info("You can now use the NexusGroupChatManager to run conversations with tool access.")

if __name__ == "__main__":
    main()
