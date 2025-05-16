#!/usr/bin/env python
"""
Simplified script to run the Agent Team Builder with proper error handling.
"""

import os
import sys
import traceback
import subprocess
import platform

def check_security_dependencies():
    """Check if security dependencies are installed."""
    try:
        import cryptography
        import keyring
        return True
    except ImportError:
        return False

def main():
    try:
        # Check if security dependencies are installed
        has_security = check_security_dependencies()
        if not has_security:
            print("WARNING: Secure key management packages not installed.")
            print("         API keys will not be stored securely.")
            print("To install secure dependencies: pip install cryptography keyring")
            print()
        
        # Check if we need to set up API keys first
        from nexus_framework.llm_key_manager import LLMKeyManager
        key_manager = LLMKeyManager()
        providers = key_manager.get_all_available_providers()
        
        if not providers:
            print("No API keys configured. Running setup wizard...")
            
            # If running on Windows, try to use the batch file for better UX
            if platform.system() == "Windows" and os.path.exists("secure_key_setup.bat"):
                print("Launching secure key setup wizard...")
                subprocess.call(["secure_key_setup.bat"])
            else:
                # Otherwise use the interactive setup directly
                key_manager.interactive_setup()
            
            # Check if setup was successful
            providers = key_manager.get_all_available_providers()
            if not providers:
                print("API key setup incomplete. Please configure at least one API key to continue.")
                return
        
        # Import the agent team builder
        from agent_team_builder import AgentTeamBuilder
        
        # Path to the agent model configuration
        config_path = 'agent_model_config.json'
        
        # Create the team builder
        builder = AgentTeamBuilder(config_path)
        print("Agent Team Builder initialized")
        print(f"Available providers: {', '.join(providers)}")
        
        # Define a simple team with providers we have keys for
        team_config = [
            {"type": "UserProxy", "name": "Human Interface"}
        ]
        
        # Add appropriate agents based on available providers
        if "anthropic" in providers:
            team_config.append({"type": "Assistant", "name": "Orchestration & Operations Agent"})
        elif "google" in providers:
            team_config.append({"type": "Assistant", "name": "Multimodal Document Processing Agent"})
        elif "openai" in providers:
            team_config.append({"type": "Assistant", "name": "Data Persistence Agent"})
            
        # Ensure we have at least one LLM-powered assistant
        if len(team_config) < 2:
            print("You need at least one configured API key for an LLM provider to create an agent team.")
            return
        
        # Build the team
        print("\nBuilding agent team...")
        agents = builder.build_team(team_config)
        
        if not agents:
            print("Failed to build agent team. Please check your configuration and API keys.")
            return
            
        print(f"Successfully created {len(agents)} agents")
        
        # Create a chat manager
        chat_manager = builder.create_chat_manager(agents)
        print("Created group chat manager")
        
        # Get the user proxy to start the conversation
        user_proxy = builder.get_agent_by_name("Human Interface")
        
        if user_proxy:
            # Run the chat with a simple initial message
            messages = builder.run_team_chat(
                chat_manager=chat_manager,
                initial_sender=user_proxy,
                initial_message="Hello! Can you help me understand what you can do?"
            )
            
            print(f"\nChat completed with {len(messages)} messages")
            
            # Save agent configuration
            builder.save_agents_config("test_team_config.json")
            print("Team configuration saved to test_team_config.json")
        else:
            print("Error: User proxy agent not found in the team")
            
    except ImportError as e:
        print(f"Error importing required modules: {e}")
        print("Make sure you have installed all requirements with: pip install -r requirements.txt")
    except Exception as e:
        print(f"Error running the agent team builder: {e}")
        traceback.print_exc()
        
if __name__ == "__main__":
    main()
