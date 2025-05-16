#!/usr/bin/env python
"""
Example script demonstrating the reliable messaging infrastructure.

This example creates a team of agents that communicate using the reliable
messaging infrastructure with guaranteed message delivery.
"""

import os
import sys
import logging
import time

from agent_team_builder import AgentTeamBuilder
from nexus_framework.communication.reliable_bus import ReliableCommunicationBus
from nexus_framework.orchestration.reliable_groupchat import ReliableNexusGroupChatManager
from nexus_framework.messaging.rabbit_mq_broker import RabbitMQBroker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("reliable_team_example.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def main():
    # Initialize the RabbitMQ broker
    broker = RabbitMQBroker()
    
    # Default configuration for local RabbitMQ server
    broker_config = {
        'host': 'localhost',
        'port': 5672,
        'vhost': '/',
        'username': 'guest',
        'password': 'guest',
        'heartbeat': 60,
        'connection_attempts': 3
    }
    
    # Initialize the broker
    logger.info("Initializing RabbitMQ broker...")
    if not broker.initialize(broker_config):
        logger.error("Failed to initialize RabbitMQ broker. Is RabbitMQ running?")
        logger.info("Falling back to legacy mode (in-memory messaging)")
        broker = None
    
    # Create the reliable communication bus
    communication_bus = ReliableCommunicationBus(broker=broker, legacy_mode=(broker is None))
    logger.info(f"Created communication bus (legacy_mode={broker is None})")
    
    # Path to the agent model configuration
    config_path = 'agent_model_config.json'
    
    # Create the team builder (pass our communication bus to it)
    builder = AgentTeamBuilder(config_path)
    builder.communication_bus = communication_bus  # Replace the default bus
    logger.info("Agent Team Builder initialized with reliable communication bus")
    
    # Define a document processing team configuration
    team_config = [
        {"type": "UserProxy", "name": "Human Interface"},
        {"type": "Assistant", "name": "Orchestration & Operations Agent"},
        {"type": "Assistant", "name": "Multimodal Document Processing Agent"},
        {"type": "Assistant", "name": "Verification & Curation Agent"}
    ]
    
    # Build the team
    logger.info("Building agent team...")
    agents = builder.build_team(team_config)
    logger.info(f"Created {len(agents)} agents")
    
    # Create a reliable chat manager
    chat_manager = ReliableNexusGroupChatManager(
        agents=agents,
        communication_bus=communication_bus,
        max_rounds=15
    )
    logger.info(f"Created reliable group chat manager with workflow ID: {chat_manager.workflow_id}")
    
    # Get the user proxy to start the conversation
    user_proxy = builder.get_agent_by_name("Human Interface")
    
    if user_proxy:
        # Define an initial task for the team
        initial_message = """
        We have a new accessibility compliance document to process. 
        Let's develop a reliable processing pipeline with the following requirements:
        
        1. Each document must be fully parsed and indexed
        2. All metadata must be extracted and validated
        3. Processing must be resilient to failures
        
        Let's discuss how to implement this with reliable messaging.
        """
        
        logger.info("Starting reliable team chat...")
        # Run the chat with reliable messaging
        messages = chat_manager.run_chat(
            initial_sender=user_proxy,
            initial_message_content=initial_message
        )
        
        # Print conversation summary
        logger.info(f"Chat completed with {len(messages)} messages exchanged")
        agents_spoken = set([msg.sender_id for msg in messages])
        logger.info(f"Agents participating: {len(agents_spoken)}")
        
        # Check for reliable messaging metadata
        sequence_numbers = [
            msg.metadata.get('sequence') for msg in messages 
            if msg.metadata and 'sequence' in msg.metadata
        ]
        logger.info(f"Total messages with sequence numbers: {len(sequence_numbers)}")
        
        workflow_ids = set([
            msg.metadata.get('workflow_id') for msg in messages 
            if msg.metadata and 'workflow_id' in msg.metadata
        ])
        logger.info(f"Workflow IDs in conversation: {workflow_ids}")
        
        # Save conversation transcript to file
        save_transcript(messages, "reliable_team_conversation.txt")
        
        # Generate and print a team report
        report = builder.get_team_report()
        logger.info("Team Report:")
        for key, value in report.items():
            if isinstance(value, dict):
                logger.info(f"{key}:")
                for subkey, subvalue in value.items():
                    logger.info(f"  {subkey}: {subvalue}")
            else:
                logger.info(f"{key}: {value}")
        
        # Save the agent configuration
        builder.save_agents_config("reliable_team_config.json")
    else:
        logger.error("Error: User proxy agent not found in the team")
    
    # Close the communication bus
    logger.info("Shutting down communication bus...")
    communication_bus.close()
    
    logger.info("Example completed successfully!")

def save_transcript(messages, filename):
    """Save the conversation transcript to a file."""
    with open(filename, 'w') as f:
        f.write("RELIABLE CONVERSATION TRANSCRIPT\n")
        f.write("===============================\n\n")
        
        for msg in messages:
            # Skip system messages
            if msg.sender_id == "group_chat_manager":
                continue
                
            # Extract sequence and workflow info if available
            seq_info = ""
            if msg.metadata:
                seq = msg.metadata.get('sequence', '')
                workflow = msg.metadata.get('workflow_id', '')
                if seq or workflow:
                    seq_info = f" [Seq: {seq}, Workflow: {workflow}]"
                    
            f.write(f"[{msg.timestamp}] {msg.sender_id}{seq_info}: {msg.content[:200]}")
            if len(msg.content) > 200:
                f.write("...")
            f.write("\n\n")
    
    logger.info(f"Saved conversation transcript to {filename}")

if __name__ == "__main__":
    main()
