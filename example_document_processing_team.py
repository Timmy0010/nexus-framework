#!/usr/bin/env python
"""
Example script showing how to use the Agent Team Builder.
This demonstrates creating a specialized team for document processing.
"""

import os
import sys
from agent_team_builder import AgentTeamBuilder

def main():
    # Path to the agent model configuration
    config_path = 'agent_model_config.json'
    
    # Create the team builder
    builder = AgentTeamBuilder(config_path)
    print("Agent Team Builder initialized")
    
    # Define a document processing team configuration
    team_config = [
        {"type": "UserProxy", "name": "Human Interface"},
        {"type": "Assistant", "name": "Orchestration & Operations Agent"},
        {"type": "Assistant", "name": "Multimodal Document Processing Agent"},
        {"type": "Assistant", "name": "Verification & Curation Agent"},
        {"type": "Assistant", "name": "Data Persistence Agent"}
    ]
    
    # Build the team
    print("\nBuilding agent team...")
    agents = builder.build_team(team_config)
    print(f"Created {len(agents)} agents")
    
    # Create a chat manager with more rounds
    chat_manager = builder.create_chat_manager(agents, max_rounds=20)
    print("Created group chat manager")
    
    # Get the user proxy to start the conversation
    user_proxy = builder.get_agent_by_name("Human Interface")
    
    if user_proxy:
        # Define an initial task for the team
        initial_message = """
        We have a new VPAT document to process for a client's product. 
        We need to extract all conformance information and categorize it according to
        WCAG 2.1 standards. Let's develop a plan to divide this work efficiently.
        """
        
        print("\nStarting team chat...")
        # Run the chat
        messages = builder.run_team_chat(
            chat_manager=chat_manager,
            initial_sender=user_proxy,
            initial_message=initial_message
        )
        
        # Print conversation summary
        print(f"\nChat completed with {len(messages)} messages exchanged")
        agents_spoken = set([msg.sender_id for msg in messages])
        print(f"Agents participating: {len(agents_spoken)}")
        
        # Save conversation transcript to file
        save_transcript(messages, "team_conversation_transcript.txt")
        
        # Generate and print a team report
        report = builder.get_team_report()
        print("\nTeam Report:")
        for key, value in report.items():
            if isinstance(value, dict):
                print(f"{key}:")
                for subkey, subvalue in value.items():
                    print(f"  {subkey}: {subvalue}")
            else:
                print(f"{key}: {value}")
        
        # Save the agent configuration
        builder.save_agents_config("document_processing_team_config.json")
    else:
        print("Error: User proxy agent not found in the team")

def save_transcript(messages, filename):
    """Save the conversation transcript to a file."""
    with open(filename, 'w') as f:
        f.write("CONVERSATION TRANSCRIPT\n")
        f.write("======================\n\n")
        
        for msg in messages:
            # Skip system messages
            if msg.sender_id == "group_chat_manager":
                continue
                
            f.write(f"[{msg.timestamp}] {msg.sender_id}: {msg.content[:200]}")
            if len(msg.content) > 200:
                f.write("...")
            f.write("\n\n")
    
    print(f"Saved conversation transcript to {filename}")

if __name__ == "__main__":
    main()
