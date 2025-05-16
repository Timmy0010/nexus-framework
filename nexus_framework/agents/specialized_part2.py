"""
Specialized agent implementations for the Nexus framework - Part 2.

This module defines more concrete agent classes that extend the BaseAgent
abstraction with specific roles and capabilities.
"""

import logging
from typing import Dict, List, Optional, Any, Union, Callable
import json
from datetime import datetime

from nexus_framework.core.agents import BaseAgent, AgentCapability, AgentIdentity
from nexus_framework.core.messaging import Message
from nexus_framework.core.tasks import Task
from nexus_framework.core.state import AgentState
from nexus_framework.core.message_parser import MessageParser, MessageHandler
from nexus_framework.tools.mcp_connector import MCPConnector

# Set up logging
logger = logging.getLogger(__name__)


class AssistantAgent(BaseAgent):
    """
    A general-purpose AI agent powered by a Large Language Model (LLM).
    
    This agent can perform a wide range of tasks such as answering questions,
    generating text or code, summarizing information, and making decisions.
    It may also use external tools via the MCPConnector when appropriate.
    """
    
    def __init__(
        self,
        agent_name: str = "Assistant",
        agent_id: Optional[str] = None,
        system_prompt: str = "You are a helpful, harmless, and honest AI assistant.",
        mcp_connector: Optional[MCPConnector] = None,
        llm_config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize a new AssistantAgent.
        
        Args:
            agent_name: A human-readable name for this agent.
            agent_id: Optional unique identifier for this agent.
            system_prompt: The system prompt that defines this agent's behavior.
            mcp_connector: Optional MCPConnector for accessing external tools.
            llm_config: Optional configuration for the LLM integration.
        """
        super().__init__(agent_name=agent_name, role="assistant", agent_id=agent_id)
        self.system_prompt = system_prompt
        self.mcp_connector = mcp_connector
        self.llm_config = llm_config or {}
        
        # Replace the default state with AgentState
        self.state = AgentState()
        
        # Store the system prompt in working memory
        self.state.set_working_memory("system_prompt", system_prompt)
        
        # Define capabilities
        self.capabilities = [
            AgentCapability(
                name="llm_reasoning",
                description="Ability to leverage an LLM for reasoning and generating responses."
            ),
            AgentCapability(
                name="content_generation",
                description="Ability to generate text, code, or other content based on prompts."
            )
        ]
        
        # Add MCP tool capability if connector is provided
        if mcp_connector:
            self.capabilities.append(
                AgentCapability(
                    name="mcp_tool_invoke",
                    description="Ability to use external tools via MCP."
                )
            )
    
    def process_message(self, message: Message) -> Optional[Message]:
        """
        Process an incoming message using LLM reasoning and potentially tools.
        
        Args:
            message: The incoming Message object to process.
            
        Returns:
            A Message object containing the agent's response.
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
        
        # Prepare conversation history for the LLM
        conversation = self._prepare_conversation_for_llm()
        
        # Get a response from the LLM
        llm_response = self._get_llm_response(conversation)
        
        # Check if the LLM response indicates a tool should be used
        tool_to_use = self._extract_tool_call_from_llm_response(llm_response)
        
        if tool_to_use and self.mcp_connector:
            # The LLM wants to use a tool
            tool_name = tool_to_use.get("tool_name")
            tool_params = tool_to_use.get("parameters", {})
            
            logger.info(f"Using MCP tool: {tool_name} with params: {tool_params}")
            
            try:
                # Call the tool via MCP
                tool_result = self.mcp_connector.invoke_tool(tool_name, tool_params)
                
                # Add the tool call and result to conversation history
                tool_call_msg = Message(
                    sender_id=self.agent_id,
                    recipient_id="mcp_server",  # Placeholder recipient
                    content={"tool_name": tool_name, "parameters": tool_params},
                    content_type="application/json",
                    role="tool_call"
                )
                
                tool_response_msg = Message(
                    sender_id="mcp_server",  # Placeholder sender
                    recipient_id=self.agent_id,
                    content=tool_result,
                    content_type="application/json",
                    role="tool_response"
                )
                
                self.state.add_message(tool_call_msg)
                self.state.add_message(tool_response_msg)
                
                # Prepare updated conversation for the LLM
                conversation = self._prepare_conversation_for_llm()
                
                # Get final response from the LLM after incorporating tool result
                llm_response = self._get_llm_response(conversation)
            except Exception as e:
                logger.error(f"Error using MCP tool: {e}")
                # If the tool fails, fall back to the original LLM response
        
        # Create and return the response message
        return Message(
            sender_id=self.agent_id,
            recipient_id=message.sender_id,
            content=llm_response,
            content_type="text/plain",
            role="assistant"
        )
    
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
    
    def _prepare_conversation_for_llm(self) -> List[Dict[str, Any]]:
        """
        Prepare the conversation history in a format suitable for the LLM.
        
        Returns:
            A list of message dictionaries in the format expected by the LLM.
        """
        # Start with the system prompt
        conversation = [
            {"role": "system", "content": self.system_prompt}
        ]
        
        # Add message history
        for msg in self.state.conversation_history:
            # Map agent roles to LLM expected roles
            role = msg.role or "user"
            if msg.sender_id == self.agent_id:
                role = "assistant"
            elif role == "tool_call":
                # Format tool calls appropriately
                conversation.append({
                    "role": "assistant",
                    "content": f"I need to use the {msg.content.get('tool_name')} tool.",
                    "tool_calls": [
                        {
                            "name": msg.content.get('tool_name'),
                            "parameters": msg.content.get('parameters', {})
                        }
                    ]
                })
                continue
            elif role == "tool_response":
                # Format tool responses appropriately
                conversation.append({
                    "role": "function",
                    "name": self.state.conversation_history[-2].content.get('tool_name'),
                    "content": json.dumps(msg.content) if isinstance(msg.content, (dict, list)) else str(msg.content)
                })
                continue
            
            # Add regular message
            conversation.append({
                "role": role,
                "content": msg.content if isinstance(msg.content, str) else json.dumps(msg.content)
            })
        
        return conversation
    
    def _get_llm_response(self, conversation: List[Dict[str, Any]]) -> str:
        """
        Get a response from the LLM based on the conversation.
        
        Args:
            conversation: The conversation history prepared for the LLM.
            
        Returns:
            The LLM's response as a string.
        """
        # TODO: Replace this placeholder with actual LLM integration
        # This is where we would call the LLM API using the config in self.llm_config
        
        logger.info("Getting response from LLM (placeholder)")
        logger.debug(f"Conversation: {conversation}")
        
        # This is a placeholder that simulates an LLM response
        if len(conversation) <= 2:
            # Initial greeting
            return "Hello! I'm an AI assistant. How can I help you today?"
        
        last_msg = conversation[-1]["content"]
        
        # Some very simple responses for demonstration
        if "hello" in last_msg.lower() or "hi" in last_msg.lower():
            return "Hello! How can I assist you today?"
        elif "help" in last_msg.lower():
            return "I'm here to help! Please let me know what you need assistance with."
        elif "weather" in last_msg.lower() and self.mcp_connector:
            # Simulate wanting to use a weather tool
            return "I'll check the weather for you using a tool."
        else:
            return f"I received your message: \"{last_msg}\". How can I assist you further?"
    
    def _extract_tool_call_from_llm_response(self, response: str) -> Optional[Dict[str, Any]]:
        """
        Determine if the LLM response indicates a tool should be used.
        
        Args:
            response: The LLM's response string.
            
        Returns:
            A dictionary with tool_name and parameters if a tool should be used,
            or None if no tool is needed.
        """
        # TODO: Replace this placeholder with actual tool call extraction logic
        # In a real implementation, this would parse the LLM's response to identify
        # function/tool calling intents, possibly using a structured format or 
        # special markers in the response.
        
        # This is a very simple placeholder that just checks for keywords
        if "tool" in response.lower() and "weather" in response.lower():
            return {
                "tool_name": "get_weather",
                "parameters": {
                    "location": "New York"  # Default location as placeholder
                }
            }
        
        return None
