"""
Nexus MCP Application

A complete application that demonstrates the Nexus Framework with MCP integration.
"""

import logging
import sys
import os
import json
import argparse
import time
import nexus_framework as nf
from typing import Dict, List, Any, Optional, Union

# Import our custom Claude MCP wrapper
from claude_mcp_integration import ClaudeMCPWrapper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("nexus_app.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class NexusMCPApplication:
    """
    A complete application that demonstrates the Nexus Framework with MCP integration.
    """
    
    def __init__(self, config_path=None):
        """
        Initialize the application.
        
        Args:
            config_path: Path to Claude's MCP configuration file. If None, the default location is used.
        """
        self.wrapper = ClaudeMCPWrapper(config_path)
        
        # Collection of active MCP servers
        self.active_servers = set()
        
        # Collection of created agent groups
        self.agent_groups = {}
        
    def start_server(self, server_name):
        """
        Start an MCP server.
        
        Args:
            server_name: The name of the server to start.
            
        Returns:
            bool: Whether the server was started successfully.
        """
        if self.wrapper.start_mcp_server(server_name):
            self.active_servers.add(server_name)
            return True
        return False
        
    def stop_server(self, server_name):
        """
        Stop an MCP server.
        
        Args:
            server_name: The name of the server to stop.
        """
        self.wrapper.stop_mcp_server(server_name)
        if server_name in self.active_servers:
            self.active_servers.remove(server_name)
            
    def list_available_servers(self):
        """
        List all available MCP servers from the configuration.
        
        Returns:
            List of server names.
        """
        return list(self.wrapper.mcp_config.get('mcpServers', {}).keys())
        
    def list_active_servers(self):
        """
        List all currently active MCP servers.
        
        Returns:
            List of active server names.
        """
        return list(self.active_servers)
        
    def create_agent_group(self, group_name, servers_to_agents):
        """
        Create a group of agents with MCP access.
        
        Args:
            group_name: The name of the group.
            servers_to_agents: Dictionary mapping server names to lists of (agent_type, agent_name) tuples.
            
        Returns:
            The chat manager for the group, or None if there was an error.
        """
        agent_ids = []
        
        # Create agents for each server
        for server_name, agents in servers_to_agents.items():
            if server_name not in self.active_servers:
                logger.error(f"Server '{server_name}' is not active")
                continue
                
            for agent_type, agent_name in agents:
                agent = self.wrapper.create_agent_with_mcp(agent_type, agent_name, server_name)
                if agent:
                    agent_ids.append(agent.agent_id)
        
        if not agent_ids:
            logger.error("No agents were created for the group")
            return None
            
        # Create the chat group
        chat_manager = self.wrapper.create_chat_group(agent_ids)
        
        if chat_manager:
            self.agent_groups[group_name] = chat_manager
            logger.info(f"Created agent group '{group_name}' with {len(agent_ids)} agents")
            return chat_manager
        
        return None
        
    def run_group_chat(self, group_name, initial_message, max_rounds=10):
        """
        Run a chat with a group of agents.
        
        Args:
            group_name: The name of the group.
            initial_message: The initial message content.
            max_rounds: Maximum number of chat rounds.
            
        Returns:
            The messages from the chat, or None if there was an error.
        """
        if group_name not in self.agent_groups:
            logger.error(f"Agent group '{group_name}' not found")
            return None
            
        chat_manager = self.agent_groups[group_name]
        
        # Find the user agent in the group
        user_agent = None
        for agent in chat_manager.agents:
            if isinstance(agent, nf.UserProxyAgent):
                user_agent = agent
                break
                
        if not user_agent:
            logger.error(f"No UserProxyAgent found in group '{group_name}'")
            return None
            
        # Run the chat
        chat_manager.max_rounds = max_rounds
        messages = self.wrapper.run_chat(
            chat_manager,
            user_agent.agent_id,
            initial_message
        )
        
        return messages
        
    def print_chat_messages(self, messages):
        """
        Print chat messages in a nice format.
        
        Args:
            messages: List of messages from the chat.
        """
        if not messages:
            logger.warning("No messages to print")
            return
            
        print("\n" + "=" * 50)
        print("CHAT TRANSCRIPT")
        print("=" * 50)
        
        for msg in messages:
            # Find the sender name
            sender_name = "Unknown"
            for group_name, chat_manager in self.agent_groups.items():
                for agent in chat_manager.agents:
                    if agent.agent_id == msg.sender_id:
                        sender_name = agent.agent_name
                        break
                if sender_name != "Unknown":
                    break
                    
            print(f"\n{sender_name}:")
            print("-" * (len(sender_name) + 1))
            print(msg.content)
            
        print("\n" + "=" * 50)
        
    def shutdown(self):
        """Shutdown the application and stop all servers."""
        logger.info("Shutting down the application...")
        self.wrapper.stop_all_servers()
        self.active_servers.clear()
        self.agent_groups.clear()
        logger.info("Application shutdown complete.")


def main():
    """
    Main function to run the Nexus MCP Application.
    """
    parser = argparse.ArgumentParser(description="Nexus MCP Application")
    parser.add_argument("--config", help="Path to Claude's MCP configuration file")
    args = parser.parse_args()
    
    # Configure Nexus logging
    nf.configure_logging(log_level="INFO")
    
    # Create the application
    app = NexusMCPApplication(args.config)
    
    try:
        # List available servers
        available_servers = app.list_available_servers()
        logger.info(f"Available MCP servers: {', '.join(available_servers)}")
        
        # Start the fetch server for web access
        if 'fetch' in available_servers:
            logger.info("Starting the fetch MCP server...")
            if app.start_server('fetch'):
                logger.info("Fetch MCP server started successfully")
            else:
                logger.error("Failed to start fetch MCP server")
                
        # Start the SQLite server for database access
        if 'sqlite' in available_servers:
            logger.info("Starting the SQLite MCP server...")
            if app.start_server('sqlite'):
                logger.info("SQLite MCP server started successfully")
            else:
                logger.error("Failed to start SQLite MCP server")
                
        # Start the GitHub server for repository access
        if 'github' in available_servers:
            logger.info("Starting the GitHub MCP server...")
            if app.start_server('github'):
                logger.info("GitHub MCP server started successfully")
            else:
                logger.error("Failed to start GitHub MCP server")
                
        # List active servers
        active_servers = app.list_active_servers()
        if not active_servers:
            logger.error("No MCP servers could be started. Exiting.")
            return
            
        logger.info(f"Active MCP servers: {', '.join(active_servers)}")
        
        # Create a research team group
        if 'fetch' in active_servers:
            # Define the agents to create
            servers_to_agents = {
                'fetch': [
                    ('user', 'Human'),
                    ('assistant', 'Research Assistant'),
                    ('planner', 'Research Planner'),
                    ('executor', 'Web Searcher')
                ]
            }
            
            # Create the group
            research_group = app.create_agent_group('research_team', servers_to_agents)
            
            if research_group:
                # Run a chat with the research team
                messages = app.run_group_chat(
                    'research_team',
                    "I need to research the latest advancements in AI agent frameworks. Can you help me find relevant information?",
                    max_rounds=5
                )
                
                # Print the chat transcript
                if messages:
                    app.print_chat_messages(messages)
                else:
                    logger.error("No messages returned from research team chat")
        
        # Create a database analysis team if SQLite server is available
        if 'sqlite' in active_servers:
            # Define the agents to create
            servers_to_agents = {
                'sqlite': [
                    ('user', 'Human'),
                    ('assistant', 'Database Assistant'),
                    ('executor', 'SQL Query Executor')
                ]
            }
            
            # Create the group
            db_group = app.create_agent_group('database_team', servers_to_agents)
            
            if db_group:
                # Run a chat with the database team
                messages = app.run_group_chat(
                    'database_team',
                    "I need to analyze the data in the TestSQLbase.db database. Can you help me run some queries and analyze the results?",
                    max_rounds=5
                )
                
                # Print the chat transcript
                if messages:
                    app.print_chat_messages(messages)
                else:
                    logger.error("No messages returned from database team chat")
                    
        # Create a development team if multiple servers are available
        if len(active_servers) >= 2:
            # Define the agents to create using all available servers
            servers_to_agents = {}
            
            if 'fetch' in active_servers:
                servers_to_agents['fetch'] = [
                    ('user', 'Developer'),
                    ('assistant', 'Programming Assistant')
                ]
                
            if 'sqlite' in active_servers:
                servers_to_agents['sqlite'] = [
                    ('executor', 'Database Manager')
                ]
                
            if 'github' in active_servers:
                servers_to_agents['github'] = [
                    ('executor', 'Code Repository Manager')
                ]
                
            # Create the group
            dev_group = app.create_agent_group('development_team', servers_to_agents)
            
            if dev_group:
                # Run a chat with the development team
                messages = app.run_group_chat(
                    'development_team',
                    "I need to develop a new feature for our application that requires database access and code repository management. Can you help me with this task?",
                    max_rounds=5
                )
                
                # Print the chat transcript
                if messages:
                    app.print_chat_messages(messages)
                else:
                    logger.error("No messages returned from development team chat")
    finally:
        # Shutdown the application
        app.shutdown()
        
    logger.info("Nexus MCP Application completed successfully")


if __name__ == "__main__":
    main()
