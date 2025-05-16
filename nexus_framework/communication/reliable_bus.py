"""
Reliable communication bus for the Nexus framework.

This module implements a reliable version of the CommunicationBus that uses
a message broker for guaranteed message delivery.
"""

import logging
import uuid
import json
import time
from typing import Dict, List, Optional, Any, Set, Callable
from collections import deque
import threading

from nexus_framework.core.agents import BaseAgent
from nexus_framework.core.messaging import Message
from nexus_framework.messaging.broker import MessageBroker
from nexus_framework.messaging.rabbit_mq_broker import RabbitMQBroker

# Set up logging
logger = logging.getLogger(__name__)

class ReliableCommunicationBus:
    """
    Reliable message router for the Nexus framework.
    
    This implementation uses a message broker (RabbitMQ by default) to provide
    reliable message delivery with acknowledgments and dead letter handling.
    It maintains the same API as the base CommunicationBus for backward compatibility.
    """
    
    def __init__(self, broker: Optional[MessageBroker] = None, legacy_mode: bool = False):
        """
        Initialize a new reliable communication bus.
        
        Args:
            broker: Optional MessageBroker instance to use.
                   If None, a RabbitMQBroker is created and initialized.
            legacy_mode: If True, operates in compatibility mode with the original CommunicationBus.
        """
        # Dictionary mapping agent_id to BaseAgent instance
        self._agent_registry: Dict[str, BaseAgent] = {}
        
        # Dictionary mapping group_id to set of agent_ids
        self._group_registry: Dict[str, Set[str]] = {}
        
        # Dictionary mapping subscription_id to callback functions
        self._message_callbacks: Dict[str, Callable] = {}
        
        # Use provided broker or create default implementation
        self._broker = broker or self._create_default_broker()
        self._legacy_mode = legacy_mode
        
        # Only used in legacy mode
        self._message_queue = deque()
        self._running = False
        self._worker_thread = None
        
        # Set up standard topics
        self._initialize_standard_topics()
    
    def _create_default_broker(self) -> MessageBroker:
        """Create and initialize a default RabbitMQ broker."""
        broker = RabbitMQBroker()
        
        # Default configuration for local RabbitMQ server
        config = {
            'host': 'localhost',
            'port': 5672,
            'vhost': '/',
            'username': 'guest',
            'password': 'guest',
            'heartbeat': 60,
            'connection_attempts': 3
        }
        
        initialized = broker.initialize(config)
        if not initialized:
            logger.warning("Failed to initialize default RabbitMQ broker. Using in-memory mode.")
            self._legacy_mode = True
        
        return broker
    
    def _initialize_standard_topics(self) -> None:
        """Initialize the standard topics used by the framework."""
        if self._legacy_mode:
            return
            
        # Create standard topics
        topics = [
            'nexus.agents',         # For direct agent-to-agent messages
            'nexus.commands',       # For system commands
            'nexus.events',         # For system events
            'nexus.tools'           # For tool-related messages
        ]
        
        for topic in topics:
            try:
                self._broker.create_topic(topic)
            except Exception as e:
                logger.error(f"Failed to create topic {topic}: {e}")
    
    def register_agent(self, agent: BaseAgent) -> None:
        """
        Add an agent to the bus's registry and create agent-specific queue.
        
        Args:
            agent: The BaseAgent instance to register.
        """
        if agent.agent_id in self._agent_registry:
            logger.warning(f"Agent with ID {agent.agent_id} already registered. Overwriting.")
        
        self._agent_registry[agent.agent_id] = agent
        logger.info(f"Registered agent: {agent.agent_name} (ID: {agent.agent_id}, Role: {agent.role})")
        
        if not self._legacy_mode:
            # Create agent-specific queue
            queue_name = f"agent_{agent.agent_id}"
            self._broker.create_queue(queue_name, durable=True)
            
            # Subscribe to agent's queue
            subscription_id = self._broker.subscribe(
                topic="nexus.agents",
                callback=self._on_message_received,
                queue_name=queue_name
            )
            
            # Store subscription
            self._message_callbacks[subscription_id] = lambda msg, headers: self._route_to_agent(agent.agent_id, msg, headers)
    
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
                    
            # Unsubscribe from agent's queue
            if not self._legacy_mode:
                # Find and remove subscriptions for this agent
                for sub_id, callback in list(self._message_callbacks.items()):
                    if getattr(callback, '_agent_id', None) == agent_id:
                        self._broker.unsubscribe(sub_id)
                        del self._message_callbacks[sub_id]
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
        
        if not self._legacy_mode:
            # Create a queue for the group
            queue_name = f"group_{group_id}"
            self._broker.create_queue(queue_name, durable=True)
            
            # Bind the queue to the agents topic
            self._broker.bind_queue_to_topic(queue_name, "nexus.agents", routing_key=group_id)
    
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
        Route a message to its intended recipient using the message broker.
        
        Args:
            message: The Message object to route.
            
        Returns:
            The response Message if any, or None if no response.
        
        Raises:
            ValueError: If the recipient is not found.
        """
        recipient_id = message.recipient_id
        
        # If in legacy mode, use the original implementation
        if self._legacy_mode:
            return self._send_message_legacy(message)
        
        # Check if it's to a group
        if recipient_id in self._group_registry:
            logger.info(f"Broadcasting message to group {recipient_id}")
            return self._broadcast_to_group(message, recipient_id)
        
        # It's to an individual agent
        if recipient_id not in self._agent_registry:
            raise ValueError(f"Cannot deliver message: Recipient {recipient_id} is not registered")
        
        # Convert Message to dictionary for broker
        message_dict = message.to_dict()
        
        # Set up headers
        headers = {
            'message_id': message.message_id,
            'sender_id': message.sender_id,
            'recipient_id': message.recipient_id,
            'timestamp': int(time.time() * 1000),
            'content_type': message.content_type,
            'routing_key': recipient_id  # Use recipient_id as routing key
        }
        
        try:
            # Publish the message to the broker
            self._broker.publish(
                topic="nexus.agents",
                message=message_dict,
                headers=headers
            )
            
            logger.info(f"Published message from {message.sender_id} to {recipient_id}")
            
            # For now, still use direct delivery for responses
            # This ensures compatibility with the existing framework
            # In a future version, this would be handled asynchronously
            recipient = self._agent_registry[recipient_id]
            response = recipient.process_message(message)
            
            # Acknowledge the message
            self._broker.acknowledge(headers['message_id'])
            
            return response
            
        except Exception as e:
            logger.error(f"Error delivering message to {recipient_id}: {str(e)}")
            
            # Negative acknowledge the message
            if 'message_id' in headers:
                self._broker.negative_acknowledge(headers['message_id'], str(e))
                
            raise
    
    def _send_message_legacy(self, message: Message) -> Optional[Message]:
        """Legacy implementation of send_message for compatibility."""
        recipient_id = message.recipient_id
        
        # Check if it's to a group
        if recipient_id in self._group_registry:
            logger.info(f"Broadcasting message to group {recipient_id}")
            return self._broadcast_to_group_legacy(message, recipient_id)
        
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
        Broadcast a message to all members of a group using the broker.
        
        Args:
            message: The Message object to broadcast.
            group_id: The ID of the target group.
            
        Returns:
            List of response Messages from group members.
        """
        if self._legacy_mode:
            return self._broadcast_to_group_legacy(message, group_id)
            
        if group_id not in self._group_registry:
            raise ValueError(f"Group {group_id} does not exist")
        
        # Convert Message to dictionary for broker
        message_dict = message.to_dict()
        
        # Set up headers
        headers = {
            'message_id': message.message_id,
            'sender_id': message.sender_id,
            'recipient_id': group_id,  # Group ID as recipient
            'timestamp': int(time.time() * 1000),
            'content_type': message.content_type,
            'routing_key': group_id,  # Use group_id as routing key
            'is_group_message': True
        }
        
        try:
            # Publish the message to the broker with group routing key
            self._broker.publish(
                topic="nexus.agents",
                message=message_dict,
                headers=headers
            )
            
            logger.info(f"Published group message from {message.sender_id} to group {group_id}")
            
            # For backward compatibility, directly process messages for each agent
            # In a future version, this would be handled asynchronously
            responses = []
            for agent_id in self._group_registry[group_id]:
                if agent_id == message.sender_id:
                    continue  # Skip the sender
                    
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
                    agent = self._agent_registry[agent_id]
                    response = agent.process_message(agent_message)
                    if response:
                        responses.append(response)
                except Exception as e:
                    logger.error(f"Error broadcasting to agent {agent_id}: {str(e)}")
            
            # Acknowledge the message
            self._broker.acknowledge(headers['message_id'])
            
            return responses
            
        except Exception as e:
            logger.error(f"Error broadcasting to group {group_id}: {str(e)}")
            
            # Negative acknowledge the message
            if 'message_id' in headers:
                self._broker.negative_acknowledge(headers['message_id'], str(e))
                
            raise
    
    def _broadcast_to_group_legacy(self, message: Message, group_id: str) -> List[Message]:
        """Legacy implementation of broadcast_to_group for compatibility."""
        if group_id not in self._group_registry:
            raise ValueError(f"Group {group_id} does not exist")
        
        responses = []
        
        for agent_id in self._group_registry[group_id]:
            if agent_id == message.sender_id:
                continue  # Skip the sender
                
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
                agent = self._agent_registry[agent_id]
                response = agent.process_message(agent_message)
                if response:
                    responses.append(response)
            except Exception as e:
                logger.error(f"Error broadcasting to agent {agent_id}: {str(e)}")
        
        return responses
    
    def _on_message_received(self, message_data: Dict[str, Any], headers: Dict[str, Any]) -> None:
        """
        Handle messages received from the broker.
        
        Args:
            message_data: The message payload.
            headers: Message headers.
        """
        try:
            # Convert dictionary back to Message object
            message = Message.from_dict(message_data)
            
            # Get the recipient agent
            recipient_id = headers.get('recipient_id') or message.recipient_id
            
            if recipient_id in self._agent_registry:
                recipient = self._agent_registry[recipient_id]
                
                # Process the message
                response = recipient.process_message(message)
                
                # If there's a response, send it back
                if response:
                    self.send_message(response)
                    
                # Acknowledge the message
                self._broker.acknowledge(headers['message_id'])
                
            else:
                logger.warning(f"Message received for unknown agent: {recipient_id}")
                
                # Negative acknowledge the message
                self._broker.negative_acknowledge(
                    headers['message_id'],
                    f"Unknown recipient: {recipient_id}"
                )
                
        except Exception as e:
            logger.error(f"Error processing received message: {str(e)}")
            
            # Negative acknowledge the message
            if 'message_id' in headers:
                self._broker.negative_acknowledge(headers['message_id'], str(e))
    
    def _route_to_agent(self, agent_id: str, message_data: Dict[str, Any], headers: Dict[str, Any]) -> None:
        """
        Route a message to a specific agent.
        
        Args:
            agent_id: The ID of the target agent.
            message_data: The message payload.
            headers: Message headers.
        """
        # Set attribute for unsubscription
        setattr(self._route_to_agent, '_agent_id', agent_id)
        
        if agent_id in self._agent_registry:
            try:
                # Convert dictionary back to Message object
                message = Message.from_dict(message_data)
                
                # Process the message
                agent = self._agent_registry[agent_id]
                response = agent.process_message(message)
                
                # If there's a response, send it back
                if response:
                    self.send_message(response)
                    
                # Acknowledge the message
                self._broker.acknowledge(headers['message_id'])
                
            except Exception as e:
                logger.error(f"Error routing message to agent {agent_id}: {str(e)}")
                
                # Negative acknowledge the message
                self._broker.negative_acknowledge(headers['message_id'], str(e))
        else:
            logger.warning(f"Attempted to route message to unknown agent: {agent_id}")
            
            # Negative acknowledge the message
            self._broker.negative_acknowledge(
                headers['message_id'],
                f"Unknown agent: {agent_id}"
            )
    
    # === Async message handling methods ===
    
    def start_async_processing(self) -> None:
        """
        Start the asynchronous message processing worker thread.
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
    
    def close(self) -> None:
        """Close the communication bus and release resources."""
        # Stop async processing if running
        if self._running:
            self.stop_async_processing()
        
        # Close the broker connection if not in legacy mode
        if not self._legacy_mode and self._broker:
            self._broker.close()
            
        logger.info("Closed reliable communication bus")
