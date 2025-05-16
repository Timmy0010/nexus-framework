"""
Nexus Framework MCP Integration

This script creates a custom wrapper to integrate the Nexus Framework with Claude's MCP servers.
"""

import logging
import sys
import os
import json
import subprocess
import threading
import time
import nexus_framework as nf
from typing import Dict, List, Any, Optional, Union

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ClaudeMCPWrapper:
    """
    A wrapper class that integrates the Nexus Framework with Claude's MCP servers.
    """
    
    def __init__(self, mcp_config_path=None):
        """
        Initialize the wrapper.
        
        Args:
            mcp_config_path: Path to Claude's MCP configuration file. If None, the default location is used.
        """
        self.mcp_config_path = mcp_config_path or os.path.expanduser("C:\\Users\\thohn\\AppData\\Roaming\\Claude\\config.json")
        self.mcp_config = self._load_mcp_config()
        self.active_servers = {}
        self.agents = {}
        self.communication_bus = nf.CommunicationBus()
        
    def _load_mcp_config(self):
        """Load the MCP configuration from Claude's config file."""
        logger.info(f"Loading MCP configuration from {self.mcp_config_path}")
        
        if not os.path.exists(self.mcp_config_path):
            logger.error(f"MCP configuration file not found at {self.mcp_config_path}")
            return {}
            
        try:
            with open(self.mcp_config_path, 'r') as f:
                config = json.load(f)
                
            logger.info(f"Loaded MCP configuration with {len(config.get('mcpServers', {}))} servers")
            return config
        except Exception as e:
            logger.error(f"Error loading MCP configuration: {e}")
            return {}
            
    def start_mcp_server(self, server_name):
        """
        Start an MCP server from the configuration.
        
        Args:
            server_name: The name of the server in the configuration.
            
        Returns:
            bool: Whether the server was started successfully.
        """
        if not self.mcp_config or 'mcpServers' not in self.mcp_config:
            logger.error("MCP configuration not loaded or invalid")
            return False
            
        if server_name not in self.mcp_config['mcpServers']:
            logger.error(f"MCP server '{server_name}' not found in configuration")
            return False
            
        server_config = self.mcp_config['mcpServers'][server_name]
        command = server_config.get('command')
        args = server_config.get('args', [])
        env = server_config.get('env', {})
        
        if not command:
            logger.error(f"No command specified for MCP server '{server_name}'")
            return False
            
        logger.info(f"Starting MCP server '{server_name}' with command: {command} {' '.join(args)}")
        
        # Build environment variables
        process_env = os.environ.copy()
        process_env.update(env)
        
        try:
            # Start the process
            process = subprocess.Popen(
                [command] + args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=process_env,
                text=True
            )
            
            # Store the process
            self.active_servers[server_name] = {
                'process': process,
                'config': server_config,
                'last_request_id': 0
            }
            
            # Wait to ensure the server is ready
            time.sleep(2)
            
            # Check if the process is still running
            if process.poll() is not None:
                stderr = process.stderr.read()
                logger.error(f"MCP server '{server_name}' exited with code {process.poll()}")
                logger.error(f"Error output: {stderr}")
                del self.active_servers[server_name]
                return False
            
            logger.info(f"MCP server '{server_name}' started successfully")
            return True
        except Exception as e:
            logger.error(f"Error starting MCP server '{server_name}': {e}")
            return False
    
    def stop_mcp_server(self, server_name):
        """
        Stop a running MCP server.
        
        Args:
            server_name: The name of the server to stop.
        """
        if server_name not in self.active_servers:
            logger.warning(f"MCP server '{server_name}' is not running")
            return
            
        try:
            process = self.active_servers[server_name]['process']
            logger.info(f"Stopping MCP server '{server_name}'")
            
            # Terminate the process
            process.terminate()
            
            # Wait for it to exit
            process.wait(timeout=5)
            
            logger.info(f"MCP server '{server_name}' stopped")
        except Exception as e:
            logger.error(f"Error stopping MCP server '{server_name}': {e}")
            try:
                # Force kill if terminate didn't work
                process.kill()
                logger.info(f"Forcefully killed MCP server '{server_name}'")
            except:
                pass
        finally:
            # Remove from active servers
            if server_name in self.active_servers:
                del self.active_servers[server_name]
    
    def send_mcp_request(self, server_name, method, params=None):
        """
        Send a request to an MCP server.
        
        Args:
            server_name: The name of the server to send the request to.
            method: The JSON-RPC method to call.
            params: Optional parameters for the method.
            
        Returns:
            The result of the request, or None if there was an error.
        """
        if server_name not in self.active_servers:
            logger.error(f"MCP server '{server_name}' is not running")
            return None
            
        server = self.active_servers[server_name]
        process = server['process']
        
        # Generate a new request ID
        server['last_request_id'] += 1
        request_id = str(server['last_request_id'])
        
        # Build the request
        request = {
            'jsonrpc': '2.0',
            'id': request_id,
            'method': method
        }
        
        if params is not None:
            request['params'] = params
            
        request_str = json.dumps(request) + "\n"
        
        try:
            logger.debug(f"Sending request to '{server_name}': {request_str}")
            
            # Send the request
            process.stdin.write(request_str)
            process.stdin.flush()
            
            # Read the response
            response_str = process.stdout.readline()
            logger.debug(f"Received response from '{server_name}': {response_str}")
            
            # Parse the response
            response = json.loads(response_str)
            
            # Check for errors
            if 'error' in response:
                error = response['error']
                logger.error(f"Error from MCP server '{server_name}': {error}")
                return None
                
            # Return the result
            return response.get('result')
        except Exception as e:
            logger.error(f"Error sending request to MCP server '{server_name}': {e}")
            return None
    
    def list_server_capabilities(self, server_name):
        """
        List the capabilities of an MCP server.
        
        Args:
            server_name: The name of the server to query.
            
        Returns:
            A dictionary with the capabilities, or None if there was an error.
        """
        return self.send_mcp_request(server_name, 'mcp.capabilityList')
    
    def create_agent_with_mcp(self, agent_type, agent_name, server_name):
        """
        Create a Nexus agent with access to an MCP server.
        
        Args:
            agent_type: The type of agent to create ('user', 'assistant', 'planner', or 'executor').
            agent_name: The name of the agent.
            server_name: The name of the MCP server to connect to.
            
        Returns:
            The created agent, or None if there was an error.
        """
        if server_name not in self.active_servers:
            logger.error(f"MCP server '{server_name}' is not running")
            return None
            
        # Create a custom MCP connector for the server
        class CustomMCPConnector:
            def __init__(self, wrapper, server):
                self.wrapper = wrapper
                self.server = server
                self._tools_cache = None
                
            def list_tools(self):
                if self._tools_cache is None:
                    capabilities = self.wrapper.list_server_capabilities(self.server)
                    if capabilities:
                        self._tools_cache = capabilities.get('tools', [])
                    else:
                        self._tools_cache = []
                return self._tools_cache
                
            def invoke_tool(self, tool_name, parameters):
                return self.wrapper.send_mcp_request(
                    self.server,
                    'tools/call',
                    {
                        'tool_name': tool_name,
                        'parameters': parameters
                    }
                )
                
            def clear_cache(self):
                self._tools_cache = None
                
        # Create the custom MCP connector
        mcp_connector = CustomMCPConnector(self, server_name)
        
        # Create the agent based on the type
        agent = None
        if agent_type.lower() == 'user':
            agent = nf.UserProxyAgent(agent_name=agent_name)
        elif agent_type.lower() == 'assistant':
            agent = nf.AssistantAgent(agent_name=agent_name)
            # We'll monkey patch the agent to use our custom MCP connector
            agent.mcp_connector = mcp_connector
        elif agent_type.lower() == 'planner':
            agent = nf.PlannerAgent(agent_name=agent_name)
            # We'll monkey patch the agent to use our custom MCP connector
            agent.mcp_connector = mcp_connector
        elif agent_type.lower() == 'executor':
            agent = nf.ExecutorAgent(agent_name=agent_name)
            # We'll monkey patch the agent to use our custom MCP connector
            agent.mcp_connector = mcp_connector
        else:
            logger.error(f"Unknown agent type: {agent_type}")
            return None
            
        # Register the agent
        self.agents[agent.agent_id] = agent
        
        # Register with the communication bus
        self.communication_bus.register_agent(agent)
        
        logger.info(f"Created {agent_type} agent '{agent_name}' with MCP access to '{server_name}'")
        return agent
    
    def create_chat_group(self, agent_ids=None):
        """
        Create a chat group with the specified agents.
        
        Args:
            agent_ids: List of agent IDs to include. If None, all agents are included.
            
        Returns:
            The chat manager.
        """
        if agent_ids is None:
            agents = list(self.agents.values())
        else:
            agents = [self.agents[agent_id] for agent_id in agent_ids if agent_id in self.agents]
            
        if not agents:
            logger.error("No agents to include in chat group")
            return None
            
        chat_manager = nf.NexusGroupChatManager(
            agents=agents,
            communication_bus=self.communication_bus
        )
        
        logger.info(f"Created chat group with {len(agents)} agents")
        return chat_manager
    
    def run_chat(self, chat_manager, initial_sender_id, initial_message):
        """
        Run a chat with the specified initial message.
        
        Args:
            chat_manager: The chat manager to use.
            initial_sender_id: The ID of the agent to send the initial message.
            initial_message: The initial message content.
            
        Returns:
            The messages from the chat.
        """
        if initial_sender_id not in self.agents:
            logger.error(f"Agent with ID '{initial_sender_id}' not found")
            return None
            
        initial_sender = self.agents[initial_sender_id]
        
        logger.info(f"Running chat with initial message from {initial_sender.agent_name}")
        messages = chat_manager.run_chat(
            initial_sender=initial_sender,
            initial_message_content=initial_message
        )
        
        return messages
    
    def stop_all_servers(self):
        """Stop all running MCP servers."""
        for server_name in list(self.active_servers.keys()):
            self.stop_mcp_server(server_name)
        logger.info("All MCP servers stopped")


def main():
    """
    Main function to demonstrate using the Claude MCP wrapper with Nexus.
    """
    # Configure Nexus logging
    nf.configure_logging(log_level="INFO")
    
    # Create the wrapper
    wrapper = ClaudeMCPWrapper()
    
    # List available servers
    available_servers = wrapper.mcp_config.get('mcpServers', {}).keys()
    logger.info(f"Available MCP servers: {', '.join(available_servers)}")
    
    # Start the fetch server
    if 'fetch' in available_servers:
        logger.info("Starting the fetch MCP server...")
        if wrapper.start_mcp_server('fetch'):
            # List capabilities
            capabilities = wrapper.list_server_capabilities('fetch')
            if capabilities:
                logger.info(f"Fetch server capabilities: {json.dumps(capabilities, indent=2)}")
                
                # Create agents
                user_agent = wrapper.create_agent_with_mcp('user', 'User', 'fetch')
                assistant_agent = wrapper.create_agent_with_mcp('assistant', 'Assistant', 'fetch')
                
                if user_agent and assistant_agent:
                    # Create a chat group
                    chat_manager = wrapper.create_chat_group()
                    
                    if chat_manager:
                        # Run a test chat
                        messages = wrapper.run_chat(
                            chat_manager,
                            user_agent.agent_id,
                            "Hello Assistant, can you help me find information on the web?"
                        )
                        
                        # Print the conversation
                        if messages:
                            logger.info("Chat completed. Messages:")
                            for msg in messages:
                                sender_name = "Unknown"
                                for agent in chat_manager.agents:
                                    if agent.agent_id == msg.sender_id:
                                        sender_name = agent.agent_name
                                        break
                                logger.info(f"{sender_name}: {msg.content}")
    
    # You could also start and use the SQLite server in a similar way
    
    # Stop all servers when done
    wrapper.stop_all_servers()
    
    logger.info("Demonstration completed.")


if __name__ == "__main__":
    main()
