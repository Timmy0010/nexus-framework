#!/usr/bin/env python
import os
import json
import sys
from typing import Dict, List, Any, Optional
import nexus_framework as nf
from nexus_framework.tools.model_provider import ModelManager

class AgentTeamBuilder:
    """A class to build agent teams based on configuration."""
    
    def __init__(self, config_path: str, api_keys_path: str = "api_keys.json"):
        """
        Initialize the Agent Team Builder.
        
        Args:
            config_path: Path to the agent model configuration file
            api_keys_path: Path to the API keys JSON file (default: "api_keys.json")
        """
        self.config_path = config_path
        
        # Ensure the llm_key_manager module is available
        try:
            from nexus_framework.llm_key_manager import LLMKeyManager
            
            # Try to use secure features
            try:
                import cryptography
                import keyring
                print("Secure key management enabled")
            except ImportError:
                print("Warning: Secure key management libraries not found.")
                print("Install with: pip install cryptography keyring")
                print("Falling back to basic key management.")
                
            # Set API keys path for the key manager
            os.environ["API_KEYS_FILE"] = api_keys_path
            
        except ImportError:
            print("Warning: llm_key_manager module not found, some model providers may not work")
            
        # Initialize the model manager
        self.model_manager = ModelManager(config_path)
        self.communication_bus = nf.CommunicationBus()
        self.agents = {}
        
    def build_agent(self, agent_type: str, agent_name: str) -> Optional[nf.BaseAgent]:
        """
        Build an agent with the configured model.
        
        Args:
            agent_type: Type of agent (UserProxy, Assistant, Planner, Executor)
            agent_name: Name of the agent (must match a key in the configuration)
            
        Returns:
            The created agent or None if creation fails
        """
        # Get model configuration for this agent
        model_config = self.model_manager.get_agent_model(agent_name)
        if not model_config:
            print(f"No model configuration found for agent: {agent_name}")
            return self._create_default_agent(agent_type, agent_name)
            
        # Get the provider for this agent
        provider_name = model_config.get("provider")
        if not provider_name:
            print(f"No provider specified for agent: {agent_name}")
            return self._create_default_agent(agent_type, agent_name)
            
        provider = self.model_manager.get_provider(provider_name)
        if not provider:
            print(f"Provider {provider_name} not available for agent: {agent_name}")
            return self._create_default_agent(agent_type, agent_name)
            
        # Create the agent based on type
        agent = None
        
        if agent_type.lower() == "userproxy":
            agent = nf.UserProxyAgent(agent_name=agent_name)
        elif agent_type.lower() == "assistant":
            # Configure the assistant with the specific model
            system_prompt = self._get_system_prompt(agent_name)
            
            # Create the agent with the model parameters
            agent = nf.AssistantAgent(
                agent_name=agent_name,
                system_prompt=system_prompt
            )
            
            # Attach model provider information
            agent.model_provider = provider
            agent.model_id = model_config.get("model_id")
            agent.temperature = model_config.get("temperature", 0.7)
            
        elif agent_type.lower() == "planner":
            system_prompt = self._get_system_prompt(agent_name)
            
            agent = nf.PlannerAgent(
                agent_name=agent_name,
                system_prompt=system_prompt
            )
            
            # Attach model provider information
            agent.model_provider = provider
            agent.model_id = model_config.get("model_id")
            agent.temperature = model_config.get("temperature", 0.7)
            
        elif agent_type.lower() == "executor":
            system_prompt = self._get_system_prompt(agent_name)
            
            agent = nf.ExecutorAgent(
                agent_name=agent_name,
                system_prompt=system_prompt
            )
            
            # Attach model provider information
            agent.model_provider = provider
            agent.model_id = model_config.get("model_id")
            agent.temperature = model_config.get("temperature", 0.7)
            
        else:
            print(f"Unsupported agent type: {agent_type}")
            return None
            
        print(f"Created agent {agent_name} ({agent_type}) with {provider_name}/{model_config.get('model_id')}")
        return agent
        
    def _create_default_agent(self, agent_type: str, agent_name: str) -> Optional[nf.BaseAgent]:
        """Create a default agent without model customization."""
        if agent_type.lower() == "userproxy":
            return nf.UserProxyAgent(agent_name=agent_name)
        elif agent_type.lower() == "assistant":
            return nf.AssistantAgent(agent_name=agent_name)
        elif agent_type.lower() == "planner":
            return nf.PlannerAgent(agent_name=agent_name)
        elif agent_type.lower() == "executor":
            return nf.ExecutorAgent(agent_name=agent_name)
        else:
            print(f"Unsupported agent type: {agent_type}")
            return None
            
    def _get_system_prompt(self, agent_name: str) -> str:
        """Generate appropriate system prompt for each agent."""
        if "Multimodal Document Processing Agent" in agent_name:
            return """You are a specialized document processing assistant focused on extracting structured information from accessibility documents.
Your primary responsibility is to analyze documents such as VPATs and extract conformance information accurately.
When processing documents, you carefully match criteria to the appropriate accessibility standards and extract both
the conformance level and supporting evidence."""
            
        elif "Orchestration & Operations Agent" in agent_name:
            return """You are a workflow coordinator responsible for managing the overall document processing pipeline.
Your role is to delegate tasks to specialized agents, track progress, handle errors, and ensure smooth operation.
You maintain the system TO-DO list, manage README updates, and generate summary reports when requested."""
            
        elif "Verification & Curation Agent" in agent_name:
            return """You are an expert in accessibility standards tasked with verifying and validating extracted information.
Your role is to review data extracted by the document processing agent, correct any errors, and ensure accuracy.
You interface with human reviewers, presenting data alongside document previews and recording all changes."""
            
        elif "Ingestion & Sourcing Agent" in agent_name:
            return """You are specialized in document acquisition and preparation for processing.
Your responsibilities include accepting document uploads, searching for accessibility documents on the web,
and validating that inputs are in acceptable formats before passing them for processing."""
            
        elif "Data Persistence Agent" in agent_name:
            return """You are responsible for securely storing structured accessibility data in the database.
Your role includes validating data against the database schema, executing queries efficiently,
and ensuring data integrity throughout storage operations."""
            
        else:
            return f"You are {agent_name}, a specialized agent in the Nexus Framework."
            
    def build_team(self, team_config: List[Dict[str, str]]) -> List[nf.BaseAgent]:
        """
        Build a team of agents based on the configuration.
        
        Args:
            team_config: List of dictionaries with agent configurations
                Each dictionary should have 'type' and 'name' keys
                
        Returns:
            List of created agents
        """
        agents = []
        
        for agent_config in team_config:
            agent_type = agent_config.get("type")
            agent_name = agent_config.get("name")
            
            if not agent_type or not agent_name:
                print(f"Invalid agent configuration: {agent_config}")
                continue
                
            agent = self.build_agent(agent_type, agent_name)
            if agent:
                agents.append(agent)
                self.agents[agent.agent_id] = agent
                
                # Register with communication bus
                self.communication_bus.register_agent(agent)
                
        return agents
        
    def create_chat_manager(self, agents: List[nf.BaseAgent], max_rounds: int = 10) -> nf.NexusGroupChatManager:
        """
        Create a group chat manager for the agents.
        
        Args:
            agents: List of agents to include in the chat
            max_rounds: Maximum number of chat rounds (default: 10)
            
        Returns:
            A configured NexusGroupChatManager instance
        """
        # Create a group chat manager
        chat_manager = nf.NexusGroupChatManager(
            agents=agents,
            communication_bus=self.communication_bus,
            max_rounds=max_rounds
        )
        
        return chat_manager

    def run_team_chat(self, chat_manager: nf.NexusGroupChatManager, 
                      initial_sender: nf.BaseAgent, initial_message: str) -> List[nf.Message]:
        """
        Run a group chat session with the configured team.
        
        Args:
            chat_manager: The group chat manager to use
            initial_sender: The agent to start the conversation
            initial_message: The initial message content
            
        Returns:
            List of messages exchanged during the chat
        """
        print(f"Starting team chat with initial message from {initial_sender.agent_name}")
        
        # Run the chat
        messages = chat_manager.run_chat(
            initial_sender=initial_sender, 
            initial_message_content=initial_message
        )
        
        print(f"Team chat completed with {len(messages)} messages")
        return messages
        
    def save_agents_config(self, output_path: str) -> None:
        """
        Save the current agent configuration to a file.
        
        Args:
            output_path: Path to save the configuration
        """
        agent_configs = {}
        
        for agent_id, agent in self.agents.items():
            agent_configs[agent_id] = {
                "name": agent.agent_name,
                "role": agent.role,
                "model_id": getattr(agent, "model_id", None),
                "provider": getattr(agent, "model_provider", None),
                "temperature": getattr(agent, "temperature", 0.7)
            }
            
        with open(output_path, 'w') as f:
            json.dump({"agents": agent_configs}, f, indent=2)
            
        print(f"Saved agent configuration to {output_path}")
        
    def get_agent_by_name(self, agent_name: str) -> Optional[nf.BaseAgent]:
        """
        Find an agent by its name.
        
        Args:
            agent_name: Name of the agent to find
            
        Returns:
            The agent if found, None otherwise
        """
        for agent in self.agents.values():
            if agent.agent_name == agent_name:
                return agent
        return None
        
    def get_team_report(self) -> Dict[str, Any]:
        """
        Generate a report about the current team configuration.
        
        Returns:
            Dictionary with team information
        """
        report = {
            "team_size": len(self.agents),
            "agent_types": {},
            "providers": {},
            "models": {}
        }
        
        for agent in self.agents.values():
            # Count agent types
            agent_type = agent.__class__.__name__
            report["agent_types"][agent_type] = report["agent_types"].get(agent_type, 0) + 1
            
            # Count provider usage
            provider = getattr(agent, "model_provider", None)
            if provider:
                provider_name = provider.__class__.__name__
                report["providers"][provider_name] = report["providers"].get(provider_name, 0) + 1
            
            # Count model usage
            model_id = getattr(agent, "model_id", None)
            if model_id:
                report["models"][model_id] = report["models"].get(model_id, 0) + 1
                
        return report


# Example usage when script is run directly
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python agent_team_builder.py <config_path>")
        config_path = 'agent_model_config.json'  # Default path
    else:
        config_path = sys.argv[1]
        
    # Create the team builder
    builder = AgentTeamBuilder(config_path)
    
    # Define a team configuration
    team_config = [
        {"type": "UserProxy", "name": "Human Interface"},
        {"type": "Assistant", "name": "Orchestration & Operations Agent"},
        {"type": "Assistant", "name": "Multimodal Document Processing Agent"},
        {"type": "Assistant", "name": "Verification & Curation Agent"}
    ]
    
    # Build the team
    agents = builder.build_team(team_config)
    
    # Create a chat manager
    chat_manager = builder.create_chat_manager(agents)
    
    # Get the user proxy to start the conversation
    user_proxy = builder.get_agent_by_name("Human Interface")
    
    if user_proxy:
        # Run the chat
        builder.run_team_chat(
            chat_manager=chat_manager,
            initial_sender=user_proxy,
            initial_message="Hello team, we have a new document to process. How should we approach this task?"
        )
        
        # Generate and print a team report
        report = builder.get_team_report()
        print("\nTeam Report:")
        for key, value in report.items():
            print(f"{key}: {value}")
        
        # Save the agent configuration
        builder.save_agents_config("agent_team_config.json")
    else:
        print("Error: User proxy agent not found in the team")
