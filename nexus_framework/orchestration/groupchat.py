"""
Group chat implementation for the Nexus framework.

This module provides the components for managing conversations among
multiple agents within the Nexus framework.
"""

import logging
from typing import Dict, List, Optional, Any, Union, Callable, Set
import uuid
from datetime import datetime
import time

from nexus_framework.core.agents import BaseAgent
from nexus_framework.core.messaging import Message
from nexus_framework.communication.bus import CommunicationBus

# Set up logging
logger = logging.getLogger(__name__)


class NexusGroupChatManager:
    """
    Orchestrates conversations among a group of agents.
    
    This class manages the flow of messages, selects the next speaker,
    and maintains the shared context of the conversation.
    """
    
    def __init__(
        self,
        agents: List[BaseAgent],
        communication_bus: CommunicationBus,
        messages: Optional[List[Message]] = None,
        max_rounds: int = 10
    ):
        """
        Initialize a new group chat manager.
        
        Args:
            agents: A list of BaseAgent instances participating in the group chat.
            communication_bus: The CommunicationBus for message delivery.
            messages: Optional initial messages to seed the conversation.
            max_rounds: Maximum number of turns in the conversation.
        """
        self.agents = agents
        self.communication_bus = communication_bus
        self.messages = messages or []
        self.max_rounds = max_rounds
        
        # Generate a unique ID for this group chat
        self.group_id = f"group_{str(uuid.uuid4())[:8]}"
        
        # Register all agents with the communication bus
        for agent in self.agents:
            if not self.communication_bus.get_agent(agent.agent_id):
                self.communication_bus.register_agent(agent)
        
        # Create a group in the communication bus
        self.communication_bus.create_group(
            self.group_id,
            [agent.agent_id for agent in self.agents]
        )
        
        # Keep track of which agents have spoken
        self.speaking_history: List[str] = []
    
    def run_chat(self, initial_sender: BaseAgent, initial_message_content: str) -> List[Message]:
        """
        Initiate and manage the group conversation.
        
        Args:
            initial_sender: The agent that starts the conversation.
            initial_message_content: The content of the first message.
            
        Returns:
            A list of all messages exchanged during the conversation.
        """
        logger.info(f"Starting group chat with initial sender: {initial_sender.agent_name}")
        
        # Create the initial message
        initial_message = Message(
            sender_id=initial_sender.agent_id,
            recipient_id=self.group_id,  # Send to the whole group
            content=initial_message_content,
            content_type="text/plain",
            role="user" if initial_sender.role == "user_proxy" else "assistant"
        )
        
        # Add to messages list
        self.messages.append(initial_message)
        
        # Record the sender in speaking history
        self.speaking_history.append(initial_sender.agent_id)
        
        # Broadcast the initial message to all agents except the sender
        responses = self._broadcast_to_group(initial_message, exclude_ids=[initial_sender.agent_id])
        
        # Add responses to messages list
        self.messages.extend(responses)
        
        # Run the conversation for max_rounds
        round_count = 1
        
        while round_count < self.max_rounds:
            logger.info(f"Group chat round {round_count}")
            
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
            
            # Create a message for the next speaker
            message = Message(
                sender_id="group_chat_manager",
                recipient_id=next_speaker.agent_id,
                content=prompt,
                content_type="text/plain",
                role="system",
                metadata={"is_prompt": True}
            )
            
            # Get a response from the next speaker
            response = next_speaker.process_message(message)
            
            if not response:
                logger.warning(f"No response from {next_speaker.agent_name}, ending conversation")
                break
            
            # Update the sender to be the actual agent (not group_chat_manager)
            response.sender_id = next_speaker.agent_id
            response.recipient_id = self.group_id
            
            # Add to messages list
            self.messages.append(response)
            
            # Record the speaker in speaking history
            self.speaking_history.append(next_speaker.agent_id)
            
            # Broadcast the response to all agents except the sender
            responses = self._broadcast_to_group(response, exclude_ids=[next_speaker.agent_id])
            
            # Add responses to messages list
            self.messages.extend(responses)
            
            # Check for termination conditions
            if self._should_terminate(response):
                logger.info("Termination condition met, ending conversation")
                break
            
            round_count += 1
        
        logger.info(f"Group chat ended after {round_count} rounds")
        return self.messages
    
    def select_next_speaker(self, last_speaker: BaseAgent, chat_history: List[Message]) -> Optional[BaseAgent]:
        """
        Determine which agent should speak next.
        
        Args:
            last_speaker: The agent that spoke last.
            chat_history: The history of messages exchanged so far.
            
        Returns:
            The BaseAgent that should speak next, or None to end the conversation.
        """
        # Simple round-robin selection for now
        # Identify who hasn't spoken in this round
        agent_ids = [agent.agent_id for agent in self.agents]
        
        # Filter out agents who have already spoken in the current round
        # We consider a 'round' to be when all agents have spoken once
        if len(set(self.speaking_history[-len(agent_ids):])) < len(agent_ids):
            # Not all agents have spoken in this round yet
            # Find the next agent who hasn't spoken in this round
            for agent_id in agent_ids:
                if agent_id not in self.speaking_history[-len(agent_ids):]:
                    return self.get_agent_by_id(agent_id)
        
        # All agents have spoken in this round or it's the first round
        # Just pick the next agent in the list after the last speaker
        last_speaker_index = None
        for i, agent in enumerate(self.agents):
            if agent.agent_id == last_speaker.agent_id:
                last_speaker_index = i
                break
        
        if last_speaker_index is not None:
            next_speaker_index = (last_speaker_index + 1) % len(self.agents)
            return self.agents[next_speaker_index]
        
        # If we couldn't find the last speaker (shouldn't happen normally),
        # just return the first agent
        return self.agents[0] if self.agents else None
    
    def resume_chat(self, messages: List[Message]) -> List[Message]:
        """
        Resume a previous conversation with a new list of messages.
        
        Args:
            messages: The history of messages from the conversation to resume.
            
        Returns:
            A list of all messages exchanged during the resumed conversation.
        """
        logger.info("Resuming group chat")
        
        # Replace the current messages with the provided ones
        self.messages = messages
        
        # Reconstruct the speaking history from the messages
        self.speaking_history = [msg.sender_id for msg in messages 
                               if msg.sender_id != "group_chat_manager"]
        
        # Check if there are messages to resume from
        if not self.messages:
            logger.warning("No messages to resume from")
            return []
        
        # Determine the last speaker
        last_speaker_id = self.speaking_history[-1] if self.speaking_history else None
        
        if not last_speaker_id:
            logger.warning("Could not determine last speaker, using first agent")
            last_speaker = self.agents[0] if self.agents else None
        else:
            last_speaker = self.get_agent_by_id(last_speaker_id)
        
        if not last_speaker:
            logger.error(f"Last speaker {last_speaker_id} not found in agent list")
            return self.messages
        
        # Select the next speaker
        next_speaker = self.select_next_speaker(last_speaker, self.messages)
        
        if not next_speaker:
            logger.warning("No next speaker selected, ending resumed conversation")
            return self.messages
        
        logger.info(f"Resuming with next speaker: {next_speaker.agent_name}")
        
        # Construct a prompt for the next speaker
        prompt = self._construct_prompt_for_agent(next_speaker)
        
        # Create a message for the next speaker
        message = Message(
            sender_id="group_chat_manager",
            recipient_id=next_speaker.agent_id,
            content=prompt,
            content_type="text/plain",
            role="system",
            metadata={"is_prompt": True, "resumed_chat": True}
        )
        
        # Get a response from the next speaker
        response = next_speaker.process_message(message)
        
        if not response:
            logger.warning(f"No response from {next_speaker.agent_name}, ending resumed conversation")
            return self.messages
        
        # Update the sender to be the actual agent (not group_chat_manager)
        response.sender_id = next_speaker.agent_id
        response.recipient_id = self.group_id
        
        # Add to messages list
        self.messages.append(response)
        
        # Record the speaker in speaking history
        self.speaking_history.append(next_speaker.agent_id)
        
        # Continue the conversation using run_chat logic
        # This is simplistic; a real implementation would have more
        # sophisticated logic to handle the continuation
        round_count = len(self.speaking_history)
        
        while round_count < self.max_rounds:
            logger.info(f"Resumed group chat round {round_count}")
            
            # Broadcast the last message to all agents except the sender
            responses = self._broadcast_to_group(
                self.messages[-1], 
                exclude_ids=[self.messages[-1].sender_id]
            )
            
            # Add responses to messages list
            self.messages.extend(responses)
            
            # Select the next speaker
            next_speaker = self.select_next_speaker(
                self.get_agent_by_id(self.speaking_history[-1]),
                self.messages
            )
            
            if not next_speaker:
                logger.info("No next speaker selected, ending resumed conversation")
                break
            
            logger.info(f"Selected next speaker: {next_speaker.agent_name}")
            
            # Construct a prompt for the next speaker
            prompt = self._construct_prompt_for_agent(next_speaker)
            
            # Create a message for the next speaker
            message = Message(
                sender_id="group_chat_manager",
                recipient_id=next_speaker.agent_id,
                content=prompt,
                content_type="text/plain",
                role="system",
                metadata={"is_prompt": True}
            )
            
            # Get a response from the next speaker
            response = next_speaker.process_message(message)
            
            if not response:
                logger.warning(f"No response from {next_speaker.agent_name}, ending conversation")
                break
            
            # Update the sender to be the actual agent (not group_chat_manager)
            response.sender_id = next_speaker.agent_id
            response.recipient_id = self.group_id
            
            # Add to messages list
            self.messages.append(response)
            
            # Record the speaker in speaking history
            self.speaking_history.append(next_speaker.agent_id)
            
            # Check for termination conditions
            if self._should_terminate(response):
                logger.info("Termination condition met, ending resumed conversation")
                break
            
            round_count += 1
        
        logger.info(f"Resumed group chat ended after {round_count} rounds")
        return self.messages
    
    def get_agent_by_id(self, agent_id: str) -> Optional[BaseAgent]:
        """
        Get an agent by its ID.
        
        Args:
            agent_id: The ID of the agent to find.
            
        Returns:
            The BaseAgent with the matching ID, or None if not found.
        """
        for agent in self.agents:
            if agent.agent_id == agent_id:
                return agent
        return None
    
    def _broadcast_to_group(self, message: Message, exclude_ids: List[str] = None) -> List[Message]:
        """
        Broadcast a message to all agents in the group except those in exclude_ids.
        
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
                metadata=message.metadata.copy() if message.metadata else None
            )
            
            try:
                response = agent.process_message(agent_message)
                if response:
                    responses.append(response)
            except Exception as e:
                logger.error(f"Error broadcasting to agent {agent.agent_id}: {e}")
        
        return responses
    
    def _construct_prompt_for_agent(self, agent: BaseAgent) -> str:
        """
        Construct a prompt for an agent based on the conversation history.
        
        Args:
            agent: The agent to construct a prompt for.
            
        Returns:
            A string containing the prompt for the agent.
        """
        # This is a simple implementation; a more sophisticated version would
        # consider the agent's role, previous contributions, and the current
        # state of the conversation
        
        prompt_lines = [
            f"Group Chat: It's your turn to contribute to the conversation.",
            f"You are {agent.agent_name}, a {agent.role}.",
            f"There are {len(self.agents)} participants in this conversation.",
            ""
        ]
        
        # Add a summary of who has spoken
        speaker_summary = {}
        for msg in self.messages[-10:]:  # Last 10 messages
            sender_id = msg.sender_id
            if sender_id == "group_chat_manager":
                continue
                
            sender_agent = self.get_agent_by_id(sender_id)
            if sender_agent:
                speaker_name = sender_agent.agent_name
                speaker_summary[speaker_name] = speaker_summary.get(speaker_name, 0) + 1
        
        if speaker_summary:
            prompt_lines.append("Recent speakers:")
            for name, count in speaker_summary.items():
                prompt_lines.append(f"- {name}: {count} message(s)")
            prompt_lines.append("")
        
        # Add the last few messages for context
        prompt_lines.append("Recent conversation:")
        for i, msg in enumerate(self.messages[-5:]):  # Last 5 messages
            if msg.sender_id == "group_chat_manager":
                continue
                
            sender_agent = self.get_agent_by_id(msg.sender_id)
            sender_name = sender_agent.agent_name if sender_agent else msg.sender_id
            
            content = msg.content
            if isinstance(content, dict):
                content = str(content)
            elif not isinstance(content, str):
                content = str(content)
            
            # Truncate long messages for the prompt
            if len(content) > 500:
                content = content[:497] + "..."
                
            prompt_lines.append(f"{sender_name}: {content}")
        
        prompt_lines.append("")
        prompt_lines.append("Please respond to the conversation as appropriate for your role.")
        
        return "\n".join(prompt_lines)
    
    def _should_terminate(self, message: Message) -> bool:
        """
        Determine if the conversation should terminate based on the last message.
        
        Args:
            message: The last message in the conversation.
            
        Returns:
            True if the conversation should terminate, False otherwise.
        """
        # Check if the message content contains termination keywords
        if isinstance(message.content, str):
            termination_keywords = [
                "end conversation",
                "terminate conversation",
                "conversation complete",
                "we're done",
                "that concludes our discussion"
            ]
            
            for keyword in termination_keywords:
                if keyword.lower() in message.content.lower():
                    return True
        
        # Check if the message metadata indicates termination
        if message.metadata and message.metadata.get("terminate_conversation", False):
            return True
        
        return False
