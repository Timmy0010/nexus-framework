"""
Specialized agent implementations for the Nexus framework - Part 1.

This module defines concrete agent classes that extend the BaseAgent
abstraction with specific roles and capabilities.
"""

import logging
from typing import Dict, List, Optional, Any, Union, Callable
import json
import uuid
from datetime import datetime

from nexus_framework.core.agents import BaseAgent, AgentCapability, AgentIdentity
from nexus_framework.core.messaging import Message
from nexus_framework.core.tasks import Task
from nexus_framework.core.state import AgentState
from nexus_framework.core.message_parser import MessageParser, MessageHandler
from nexus_framework.tools.mcp_connector import MCPConnector

# Set up logging
logger = logging.getLogger(__name__)


class UserProxyAgent(BaseAgent):
    """
    An agent that acts as a representative for a human user.
    
    This agent is responsible for soliciting input from a human user,
    relaying user requests to other agents, and presenting results or
    information back to the user.
    """
    
    def __init__(
        self,
        agent_name: str = "User Proxy",
        agent_id: Optional[str] = None,
        user_input_callback: Optional[Callable[[str], str]] = None,
        user_output_callback: Optional[Callable[[Any], None]] = None
    ):
        """
        Initialize a new UserProxyAgent.
        
        Args:
            agent_name: A human-readable name for this agent.
            agent_id: Optional unique identifier for this agent.
            user_input_callback: Optional callback function that prompts the user
                                for input and returns their response as a string.
            user_output_callback: Optional callback function that presents
                                 information to the user.
        """
        super().__init__(agent_name=agent_name, role="user_proxy", agent_id=agent_id)
        self.user_input_callback = user_input_callback
        self.user_output_callback = user_output_callback
        
        # Replace the default state with AgentState
        self.state = AgentState()
        
        # Define capabilities
        self.capabilities = [
            AgentCapability(
                name="human_interaction",
                description="Ability to solicit input from and present information to a human user."
            )
        ]
    
    def process_message(self, message: Message) -> Optional[Message]:
        """
        Process an incoming message and optionally produce a response.
        
        If the message requires user input or presents results for the user,
        this agent handles the appropriate interaction with the user.
        
        Args:
            message: The incoming Message object to process.
            
        Returns:
            An optional Message object as a response.
        """
        # Add the message to conversation history
        self.state.add_message(message)
        
        # Parse the message based on content_type and role
        try:
            parsed_message = MessageHandler.handle_by_role(message)
            logger.debug(f"Parsed message: {parsed_message}")
        except ValueError as e:
            logger.error(f"Error parsing message: {e}")
            return Message(
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                content=f"Error processing your message: {str(e)}",
                content_type="text/plain",
                role="assistant"
            )
        
        # Check if this is a message that should be displayed to the user
        if message.role in ["assistant", "tool_response", None]:
            self._present_to_user(parsed_message["content"])
        
        # Check if this message requires user input
        if message.metadata and message.metadata.get("requires_user_input", False):
            user_response = self._get_user_input(
                prompt=message.metadata.get("user_prompt", "Please provide your input:")
            )
            
            # Create a response message with the user's input
            return Message(
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                content=user_response,
                content_type="text/plain",
                role="user"
            )
        
        # For other types of messages, no response is needed
        return None
    
    def get_capabilities(self) -> List[AgentCapability]:
        """
        Get the list of capabilities this agent provides.
        
        Returns:
            A list of AgentCapability objects.
        """
        return self.capabilities
    
    def get_identity(self) -> AgentIdentity:
        """
        Get the identity of this agent.
        
        Returns:
            An AgentIdentity object.
        """
        return AgentIdentity(
            id=self.agent_id,
            name=self.agent_name,
            provider_info="Nexus Framework",
            version="1.0.0"
        )
    
    def _get_user_input(self, prompt: str) -> str:
        """
        Solicit input from the user.
        
        Args:
            prompt: A prompt to display to the user.
            
        Returns:
            The user's response as a string.
        """
        if self.user_input_callback:
            return self.user_input_callback(prompt)
        else:
            # Default implementation that uses console input
            return input(f"{prompt} ")
    
    def _present_to_user(self, content: Any) -> None:
        """
        Present information to the user.
        
        Args:
            content: The information to present.
        """
        if self.user_output_callback:
            self.user_output_callback(content)
        else:
            # Default implementation that prints to console
            if isinstance(content, (dict, list)):
                # Pretty-print dictionaries and lists
                print(json.dumps(content, indent=2))
            else:
                print(content)
    
    def initiate_chat(self, recipient: BaseAgent, initial_message_content: str) -> List[Message]:
        """
        Start a conversation with another agent.
        
        Args:
            recipient: The agent to start a conversation with.
            initial_message_content: The content of the first message.
            
        Returns:
            A list of all messages exchanged during the conversation.
        """
        conversation = []
        
        # Create the initial message
        initial_message = Message(
            sender_id=self.agent_id,
            recipient_id=recipient.agent_id,
            content=initial_message_content,
            content_type="text/plain",
            role="user"
        )
        
        # Add to conversation history
        self.state.add_message(initial_message)
        conversation.append(initial_message)
        
        # Send the initial message to the recipient
        response = recipient.process_message(initial_message)
        
        # Continue the conversation until no more responses
        while response is not None:
            # Add response to conversation history
            self.state.add_message(response)
            conversation.append(response)
            
            # Present the response to the user
            self._present_to_user(response.content)
            
            # Ask for user input for the next turn
            user_input = self._get_user_input("Your response: ")
            
            # If the user entered a termination keyword, end the conversation
            if user_input.lower() in ["exit", "quit", "stop", "end"]:
                break
            
            # Create a new message with the user's input
            next_message = Message(
                sender_id=self.agent_id,
                recipient_id=recipient.agent_id,
                content=user_input,
                content_type="text/plain",
                role="user"
            )
            
            # Add to conversation history
            self.state.add_message(next_message)
            conversation.append(next_message)
            
            # Send to recipient and get next response
            response = recipient.process_message(next_message)
        
        return conversation
