"""
Reliable group chat implementation for the Nexus framework.

This module provides an enhanced version of the NexusGroupChatManager that
utilizes the reliable messaging infrastructure for resilient communication.
"""

import logging
from typing import Dict, List, Optional, Any, Union, Callable, Set
import uuid
from datetime import datetime
import time
import threading

from nexus_framework.core.agents import BaseAgent
from nexus_framework.core.messaging import Message
from nexus_framework.communication.reliable_bus import ReliableCommunicationBus
from nexus_framework.orchestration.groupchat import NexusGroupChatManager

# Set up logging
logger = logging.getLogger(__name__)


class SequenceTracker:
    """
    Tracks message sequences for a specific workflow.
    
    This ensures messages are processed in the correct order and
    allows for detection and handling of missing messages.
    """
    
    def __init__(self, workflow_id: str):
        """
        Initialize a new sequence tracker.
        
        Args:
            workflow_id: A unique identifier for the workflow.
        """
        self.workflow_id = workflow_id
        self.next_sequence = 0
        self.processed_sequences = set()
        self.lock = threading.Lock()
    
    def get_next_sequence(self) -> int:
        """
        Get the next sequence number in the workflow.
        
        Returns:
            The next sequence number.
        """
        with self.lock:
            seq = self.next_sequence
            self.next_sequence += 1
            return seq
    
    def mark_processed(self, sequence: int) -> None:
        """
        Mark a sequence number as processed.
        
        Args:
            sequence: The sequence number to mark as processed.
        """
        with self.lock:
            self.processed_sequences.add(sequence)
    
    def is_processed(self, sequence: int) -> bool:
        """
        Check if a sequence number has been processed.
        
        Args:
            sequence: The sequence number to check.
            
        Returns:
            True if the sequence has been processed, False otherwise.
        """
        with self.lock:
            return sequence in self.processed_sequences
    
    def get_missing_sequences(self, up_to: int) -> List[int]:
        """
        Get a list of missing sequence numbers up to a specified value.
        
        Args:
            up_to: The maximum sequence number to check.
            
        Returns:
            A list of sequence numbers that have not been processed.
        """
        with self.lock:
            return [seq for seq in range(up_to) if seq not in self.processed_sequences]


class MessageDeduplicator:
    """
    Detects and filters duplicate messages.
    
    This ensures idempotent message processing even if the same
    message is delivered multiple times.
    """
    
    def __init__(self, ttl_seconds: int = 3600):
        """
        Initialize a new message deduplicator.
        
        Args:
            ttl_seconds: Time-to-live for seen messages (in seconds).
        """
        self.seen_messages = {}  # message_id -> timestamp
        self.ttl_seconds = ttl_seconds
        self.lock = threading.Lock()
    
    def is_duplicate(self, message_id: str) -> bool:
        """
        Check if a message is a duplicate.
        
        Args:
            message_id: The ID of the message to check.
            
        Returns:
            True if the message is a duplicate, False otherwise.
        """
        with self.lock:
            self._purge_expired()
            return message_id in self.seen_messages
    
    def mark_seen(self, message_id: str) -> None:
        """
        Mark a message as seen.
        
        Args:
            message_id: The ID of the message to mark as seen.
        """
        with self.lock:
            self.seen_messages[message_id] = time.time()
    
    def _purge_expired(self) -> None:
        """Remove expired message IDs from the seen list."""
        now = time.time()
        expired_ids = [
            msg_id for msg_id, ts in self.seen_messages.items()
            if now - ts > self.ttl_seconds
        ]
        
        for msg_id in expired_ids:
            del self.seen_messages[msg_id]


class ReliableNexusGroupChatManager(NexusGroupChatManager):
    """
    Enhanced group chat manager with reliable messaging support.
    
    This class extends the NexusGroupChatManager to add reliability features
    such as message sequencing, deduplication, and guaranteed delivery.
    """
    
    def __init__(
        self,
        agents: List[BaseAgent],
        communication_bus: ReliableCommunicationBus,
        messages: Optional[List[Message]] = None,
        max_rounds: int = 10,
        workflow_id: Optional[str] = None
    ):
        """
        Initialize a new reliable group chat manager.
        
        Args:
            agents: A list of BaseAgent instances participating in the group chat.
            communication_bus: The ReliableCommunicationBus for message delivery.
            messages: Optional initial messages to seed the conversation.
            max_rounds: Maximum number of turns in the conversation.
            workflow_id: Optional workflow ID for message tracking.
        """
        # Initialize parent class
        super().__init__(
            agents=agents,
            communication_bus=communication_bus,
            messages=messages,
            max_rounds=max_rounds
        )
        
        # Set workflow ID
        self.workflow_id = workflow_id or f"workflow_{str(uuid.uuid4())[:8]}"
        
        # Initialize sequence tracker
        self.sequence_tracker = SequenceTracker(self.workflow_id)
        
        # Initialize message deduplicator
        self.message_deduplicator = MessageDeduplicator(ttl_seconds=3600)
        
        logger.info(f"Initialized reliable group chat manager with workflow ID: {self.workflow_id}")
    
    def run_chat(self, initial_sender: BaseAgent, initial_message_content: str) -> List[Message]:
        """
        Initiate and manage the group conversation with reliability features.
        
        Args:
            initial_sender: The agent that starts the conversation.
            initial_message_content: The content of the first message.
            
        Returns:
            A list of all messages exchanged during the conversation.
        """
        logger.info(f"Starting reliable group chat with workflow ID: {self.workflow_id}")
        
        # Create the initial message
        initial_message = Message(
            sender_id=initial_sender.agent_id,
            recipient_id=self.group_id,  # Send to the whole group
            content=initial_message_content,
            content_type="text/plain",
            role="user" if initial_sender.role == "user_proxy" else "assistant",
            metadata={
                "workflow_id": self.workflow_id,
                "sequence": self.sequence_tracker.get_next_sequence()
            }
        )
        
        # Add to messages list
        self.messages.append(initial_message)
        
        # Record the sender in speaking history
        self.speaking_history.append(initial_sender.agent_id)
        
        # Mark message as seen to prevent duplicates
        self.message_deduplicator.mark_seen(initial_message.message_id)
        
        # Broadcast the initial message to all agents except the sender
        responses = self._broadcast_to_group(initial_message, exclude_ids=[initial_sender.agent_id])
        
        # Add responses to messages list and mark as processed
        for response in responses:
            # Check for duplicates
            if not self.message_deduplicator.is_duplicate(response.message_id):
                self.messages.append(response)
                self.message_deduplicator.mark_seen(response.message_id)
                
                # Track sequence if available
                if response.metadata and 'sequence' in response.metadata:
                    self.sequence_tracker.mark_processed(response.metadata['sequence'])
        
        # Run the conversation for max_rounds
        round_count = 1
        
        while round_count < self.max_rounds:
            logger.info(f"Reliable group chat round {round_count} for workflow: {self.workflow_id}")
            
            # Select the next speaker
            next_speaker = self.select_next_speaker(
                self.get_agent_by_id(self.speaking_history[-1]),
                self.messages
            )
            
            if not next_speaker:
                logger.info("No next speaker selected, ending conversation")
                break
            
            logger.info(f"Selected next speaker: {next_speaker.agent_name}")
            
            # Construct a prompt for the next speaker
            prompt = self._construct_prompt_for_agent(next_speaker)
            
            # Create a message for the next speaker with sequencing
            message = Message(
                sender_id="group_chat_manager",
                recipient_id=next_speaker.agent_id,
                content=prompt,
                content_type="text/plain",
                role="system",
                metadata={
                    "is_prompt": True,
                    "workflow_id": self.workflow_id,
                    "sequence": self.sequence_tracker.get_next_sequence()
                }
            )
            
            # Mark message as seen to prevent duplicates
            self.message_deduplicator.mark_seen(message.message_id)
            
            # Get a response from the next speaker
            response = next_speaker.process_message(message)
            
            if not response:
                logger.warning(f"No response from {next_speaker.agent_name}, ending conversation")
                break
            
            # Update the sender to be the actual agent (not group_chat_manager)
            response.sender_id = next_speaker.agent_id
            response.recipient_id = self.group_id
            
            # Add sequence number if not present
            if not response.metadata:
                response.metadata = {}
            if 'sequence' not in response.metadata:
                response.metadata['sequence'] = self.sequence_tracker.get_next_sequence()
            if 'workflow_id' not in response.metadata:
                response.metadata['workflow_id'] = self.workflow_id
                
            # Add to messages list
            self.messages.append(response)
            
            # Mark message as seen to prevent duplicates
            self.message_deduplicator.mark_seen(response.message_id)
            
            # Record the speaker in speaking history
            self.speaking_history.append(next_speaker.agent_id)
            
            # Broadcast the response to all agents except the sender
            responses = self._broadcast_to_group(response, exclude_ids=[next_speaker.agent_id])
            
            # Add responses to messages list and mark as processed
            for resp in responses:
                # Check for duplicates
                if not self.message_deduplicator.is_duplicate(resp.message_id):
                    self.messages.append(resp)
                    self.message_deduplicator.mark_seen(resp.message_id)
                    
                    # Track sequence if available
                    if resp.metadata and 'sequence' in resp.metadata:
                        self.sequence_tracker.mark_processed(resp.metadata['sequence'])
            
            # Check for termination conditions
            if self._should_terminate(response):
                logger.info("Termination condition met, ending conversation")
                break
            
            round_count += 1
        
        logger.info(f"Reliable group chat ended after {round_count} rounds")
        
        # Check for missing sequences and log them
        missing = self.sequence_tracker.get_missing_sequences(self.sequence_tracker.next_sequence)
        if missing:
            logger.warning(f"Missing sequences detected: {missing}")
        
        return self.messages
    
    def _broadcast_to_group(self, message: Message, exclude_ids: List[str] = None) -> List[Message]:
        """
        Broadcast a message to all agents in the group with reliable delivery.
        
        Args:
            message: The message to broadcast.
            exclude_ids: Optional list of agent IDs to exclude from the broadcast.
            
        Returns:
            A list of response messages from the agents.
        """
        exclude_ids = exclude_ids or []
        responses = []
        
        for agent in self.agents:
            if agent.agent_id in exclude_ids:
                continue
            
            # Create a copy of the message with this agent as the specific recipient
            agent_message = Message(
                sender_id=message.sender_id,
                recipient_id=agent.agent_id,
                content=message.content,
                content_type=message.content_type,
                role=message.role,
                metadata=message.metadata.copy() if message.metadata else {}
            )
            
            # Ensure metadata contains workflow_id and sequence
            if 'workflow_id' not in agent_message.metadata:
                agent_message.metadata['workflow_id'] = self.workflow_id
            if 'sequence' not in agent_message.metadata:
                agent_message.metadata['sequence'] = self.sequence_tracker.get_next_sequence()
            
            try:
                # Send message with reliable delivery
                if isinstance(self.communication_bus, ReliableCommunicationBus):
                    response = self.communication_bus.send_message(agent_message)
                else:
                    # Fall back to standard delivery if not a reliable bus
                    response = agent.process_message(agent_message)
                    
                if response:
                    # Add sequence and workflow info to response if not present
                    if not response.metadata:
                        response.metadata = {}
                    if 'workflow_id' not in response.metadata:
                        response.metadata['workflow_id'] = self.workflow_id
                    if 'sequence' not in response.metadata:
                        response.metadata['sequence'] = self.sequence_tracker.get_next_sequence()
                        
                    responses.append(response)
            except Exception as e:
                logger.error(f"Error broadcasting to agent {agent.agent_id}: {e}")
        
        return responses
    
    def resume_chat(self, messages: List[Message]) -> List[Message]:
        """
        Resume a previous conversation with reliability features.
        
        Args:
            messages: The history of messages from the conversation to resume.
            
        Returns:
            A list of all messages exchanged during the resumed conversation.
        """
        logger.info(f"Resuming reliable group chat with workflow ID: {self.workflow_id}")
        
        # Replace the current messages with the provided ones
        self.messages = messages
        
        # Reconstruct the speaking history from the messages
        self.speaking_history = [msg.sender_id for msg in messages 
                               if msg.sender_id != "group_chat_manager"]
        
        # Rebuild the sequence tracker state
        max_sequence = 0
        for msg in messages:
            if msg.metadata and 'sequence' in msg.metadata:
                sequence = msg.metadata['sequence']
                self.sequence_tracker.mark_processed(sequence)
                max_sequence = max(max_sequence, sequence)
                
                # Mark message as seen to prevent duplicates
                self.message_deduplicator.mark_seen(msg.message_id)
        
        # Set next sequence
        self.sequence_tracker.next_sequence = max_sequence + 1
        
        # Now continue with the regular resume logic
        return super().resume_chat(messages)
