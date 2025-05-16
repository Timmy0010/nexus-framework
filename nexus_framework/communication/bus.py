"""
Communication bus for the Nexus framework.

This module provides the central communication infrastructure for agents
within the Nexus framework to exchange messages.
"""

import logging
from typing import Dict, List, Optional, Any, Set, Callable
from collections import deque
import threading
import time

from nexus_framework.core.agents import BaseAgent
from nexus_framework.core.messaging import Message

# Set up logging
logger = logging.getLogger(__name__)

class CommunicationBus:
    """
    Central message router for the Nexus framework.
    
    The bus maintains a registry of agents and facilitates message passing
    between them. It decouples agents from direct knowledge of each other,
    promoting modularity and simplifying agent registration and discovery.
    """
    
    def __init__(self):
        """Initialize a new communication bus."""
        # Dictionary mapping agent_id to BaseAgent instance
        self._agent_registry: Dict[str, BaseAgent] = {}
        
        # Dictionary mapping group_id to set of agent_ids
        self._group_registry: Dict[str, Set[str]] = {}
        
        # Optional - for future asynchronous message handling:
        self._message_queue = deque()
        self._running = False
        self._worker_thread = None
    
    def register_agent(self, agent: BaseAgent) -> None:
        """
        Add an agent to the bus's registry.
        
        Args:
            agent: The BaseAgent instance to register.
        """
        if agent.agent_id in self._agent_registry:
            logger.warning(f"Agent with ID {agent.agent_id} already registered. Overwriting.")
        
        self._agent_registry[agent.agent_id] = agent
        logger.info(f"Registered agent: {agent.agent_name} (ID: {agent.agent_id}, Role: {agent.role})")
    
    def unregister_agent(self, agent_id: str) -> None:
        """
        Remove an agent from the bus's registry.
        
        Args:
            agent_id: The ID of the agent to unregister.
        """
        if agent_id in self._agent_registry:
            agent = self._agent_registry.pop(agent_id)
            logger.info(f"Unregistered agent: {agent.agent_name} (ID: {agent_id})")
            
            # Remove from any groups
            for group_id, members in self._group_registry.items():
                if agent_id in members:
                    members.remove(agent_id)
                    logger.info(f"Removed agent {agent_id} from group {group_id}")
        else:
            logger.warning(f"Attempted to unregister unknown agent: {agent_id}")
    
    def create_group(self, group_id: str, agent_ids: List[str]) -> None:
        """
        Create a group of agents for broadcasting messages.
        
        Args:
            group_id: A unique identifier for the group.
            agent_ids: List of agent IDs to include in the group.
        """
        if group_id in self._group_registry:
            logger.warning(f"Group {group_id} already exists. Overwriting.")
        
        # Verify all agents exist
        for agent_id in agent_ids:
            if agent_id not in self._agent_registry:
                raise ValueError(f"Cannot create group: Agent {agent_id} is not registered")
        
        self._group_registry[group_id] = set(agent_ids)
        logger.info(f"Created group {group_id} with {len(agent_ids)} agents")
    
    def add_agent_to_group(self, group_id: str, agent_id: str) -> None:
        """
        Add an agent to an existing group.
        
        Args:
            group_id: The ID of the group.
            agent_id: The ID of the agent to add.
        """
        if group_id not in self._group_registry:
            raise ValueError(f"Group {group_id} does not exist")
        
        if agent_id not in self._agent_registry:
            raise ValueError(f"Agent {agent_id} is not registered")
        
        self._group_registry[group_id].add(agent_id)
        logger.info(f"Added agent {agent_id} to group {group_id}")
    
    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """
        Get a registered agent by ID.
        
        Args:
            agent_id: The ID of the agent to retrieve.
            
        Returns:
            The BaseAgent instance if found, None otherwise.
        """
        return self._agent_registry.get(agent_id)
    
    def get_all_agents(self) -> List[BaseAgent]:
        """
        Get all registered agents.
        
        Returns:
            List of all registered BaseAgent instances.
        """
        return list(self._agent_registry.values())
    
    def send_message(self, message: Message) -> Optional[Message]:
        """
        Route a message to its intended recipient.
        
        This method looks up the recipient_id from the message in the agent
        registry. If found, it delivers the message to the recipient agent's
        process_message method.
        
        Args:
            message: The Message object to route.
            
        Returns:
            The response Message if any, or None if no response.
        
        Raises:
            ValueError: If the recipient is not found.
        """
        recipient_id = message.recipient_id
        
        # Check if it's to a group
        if recipient_id in self._group_registry:
            logger.info(f"Broadcasting message to group {recipient_id}")
            return self._broadcast_to_group(message, recipient_id)
        
        # It's to an individual agent
        if recipient_id not in self._agent_registry:
            raise ValueError(f"Cannot deliver message: Recipient {recipient_id} is not registered")
        
        recipient = self._agent_registry[recipient_id]
        logger.info(f"Delivering message from {message.sender_id} to {recipient_id}")
        
        try:
            # Synchronously deliver message and get response
            response = recipient.process_message(message)
            return response
        except Exception as e:
            logger.error(f"Error delivering message to {recipient_id}: {str(e)}")
            raise
    
    def _broadcast_to_group(self, message: Message, group_id: str) -> List[Message]:
        """
        Broadcast a message to all members of a group.
        
        Args:
            message: The Message object to broadcast.
            group_id: The ID of the target group.
            
        Returns:
            List of response Messages from group members.
        """
        if group_id not in self._group_registry:
            raise ValueError(f"Group {group_id} does not exist")
        
        responses = []
        
        for agent_id in self._group_registry[group_id]:
            # Create a copy of the message with this agent as the specific recipient
            agent_message = Message(
                sender_id=message.sender_id,
                recipient_id=agent_id,
                content=message.content,
                content_type=message.content_type,
                role=message.role,
                metadata=message.metadata.copy() if message.metadata else None
            )
            
            try:
                response = self.send_message(agent_message)
                if response:
                    responses.append(response)
            except Exception as e:
                logger.error(f"Error broadcasting to agent {agent_id}: {str(e)}")
        
        return responses
    
    # === Future Asynchronous Message Handling ===
    
    def start_async_processing(self) -> None:
        """
        Start the asynchronous message processing worker thread.
        
        This is a placeholder for future enhancement to support asynchronous
        message delivery.
        """
        if self._running:
            logger.warning("Async processing already running")
            return
        
        self._running = True
        self._worker_thread = threading.Thread(target=self._process_message_queue)
        self._worker_thread.daemon = True
        self._worker_thread.start()
        logger.info("Started asynchronous message processing")
    
    def stop_async_processing(self) -> None:
        """
        Stop the asynchronous message processing worker thread.
        
        This is a placeholder for future enhancement.
        """
        if not self._running:
            logger.warning("Async processing not running")
            return
        
        self._running = False
        if self._worker_thread:
            self._worker_thread.join(timeout=5.0)
            logger.info("Stopped asynchronous message processing")
    
    def send_message_async(self, message: Message) -> None:
        """
        Queue a message for asynchronous delivery.
        
        This is a placeholder for future enhancement.
        
        Args:
            message: The Message object to queue for delivery.
        """
        if not self._running:
            raise RuntimeError("Async processing not started")
        
        self._message_queue.append(message)
    
    def _process_message_queue(self) -> None:
        """Worker thread method to process the async message queue."""
        while self._running:
            try:
                if self._message_queue:
                    message = self._message_queue.popleft()
                    try:
                        self.send_message(message)
                    except Exception as e:
                        logger.error(f"Error processing queued message: {str(e)}")
                else:
                    # Sleep a bit to avoid busy-waiting
                    time.sleep(0.01)
            except Exception as e:
                logger.error(f"Error in message queue processing: {str(e)}")
                # Sleep a bit to avoid rapid error loops
                time.sleep(0.1)
