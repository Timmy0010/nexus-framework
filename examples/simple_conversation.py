"""
Example usage of the Nexus Advanced Agent Framework.

This script demonstrates how to create and use agents, facilitate communication
between them, and orchestrate a simple conversation.
"""

import logging
import sys
import os

# Add the parent directory to the Python path so we can import the framework
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from nexus_framework import (
    configure_logging,
    UserProxyAgent,
    AssistantAgent,
    PlannerAgent,
    ExecutorAgent,
    CommunicationBus,
    NexusGroupChatManager,
    Message
)


def main():
    """Run a simple demonstration of the Nexus framework."""
    # Configure logging
    configure_logging(log_level=logging.INFO, console=True)
    
    # Create a communication bus
    comm_bus = CommunicationBus()
    
    # Create a user proxy agent
    user_agent = UserProxyAgent(
        agent_name="User",
        # Use input and print for user interaction
        user_input_callback=lambda prompt: input(f"{prompt} "),
        user_output_callback=lambda content: print(f"Assistant: {content}")
    )
    
    # Create an assistant agent
    assistant_agent = AssistantAgent(
        agent_name="Assistant",
        system_prompt="You are a helpful, concise assistant with expertise in Python programming."
    )
    
    # Register agents with the communication bus
    comm_bus.register_agent(user_agent)
    comm_bus.register_agent(assistant_agent)
    
    print("Starting a simple conversation between a user and an assistant.")
    print("Type 'exit', 'quit', or 'end' to terminate the conversation.")
    
    # Option 1: Direct sequential chat
    # This is a simpler approach for two-agent interaction
    initial_message = input("User: ")
    
    conversation = user_agent.initiate_chat(
        recipient=assistant_agent,
        initial_message_content=initial_message
    )
    
    print("\nConversation summary:")
    for i, msg in enumerate(conversation):
        sender = "User" if msg.sender_id == user_agent.agent_id else "Assistant"
        print(f"{i+1}. {sender}: {msg.content[:100]}{'...' if len(msg.content) > 100 else ''}")
    
    # Option 2: Group chat with multiple agents
    # This approach can be extended to include more agents
    print("\nWould you like to start a group chat with more agents? (y/n)")
    if input().lower() == 'y':
        # Create additional agents
        planner_agent = PlannerAgent(
            agent_name="Planner",
            system_prompt="You are a planning agent that excels at breaking down complex tasks."
        )
        
        executor_agent = ExecutorAgent(
            agent_name="Executor",
            system_prompt="You are an executor agent that specializes in carrying out well-defined tasks."
        )
        
        # Register new agents
        comm_bus.register_agent(planner_agent)
        comm_bus.register_agent(executor_agent)
        
        # Create a group chat manager
        group_chat = NexusGroupChatManager(
            agents=[user_agent, assistant_agent, planner_agent, executor_agent],
            communication_bus=comm_bus,
            max_rounds=10
        )
        
        print("\nStarting a group chat with multiple agents.")
        initial_message = input("Enter a complex task or question: ")
        
        group_messages = group_chat.run_chat(
            initial_sender=user_agent,
            initial_message_content=initial_message
        )
        
        print("\nGroup chat summary:")
        for i, msg in enumerate(group_messages):
            # Find the agent name based on sender_id
            sender_name = "Unknown"
            for agent in [user_agent, assistant_agent, planner_agent, executor_agent]:
                if msg.sender_id == agent.agent_id:
                    sender_name = agent.agent_name
                    break
            
            print(f"{i+1}. {sender_name}: {msg.content[:100]}{'...' if len(msg.content) > 100 else ''}")
    
    print("\nThank you for trying the Nexus Advanced Agent Framework!")


if __name__ == "__main__":
    main()
