"""
Core agent abstractions for the Nexus framework.

This module defines the foundational abstractions for agents within the Nexus framework,
including the BaseAgent abstract base class and related data structures.
"""

import abc
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
import uuid
from datetime import datetime

# ============================================================================
# Agent Capability Definitions
# ============================================================================

@dataclass
class AgentCapability:
    """
    Represents a specific capability or skill that an agent possesses.
    
    This is used to advertise what an agent can do and provide a schema
    for how to invoke the capability if applicable.
    """
    name: str
    description: str
    parameters_schema: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Validate the capability after initialization."""
        if not self.name:
            raise ValueError("Capability name cannot be empty")
        if not self.description:
            raise ValueError("Capability description cannot be empty")


# ============================================================================
# Agent Identity Definition
# ============================================================================

@dataclass
class AgentIdentity:
    """
    Represents the identity of an agent in the Nexus framework.
    
    This is used for agent discovery, identification, and potentially for
    security and auditing purposes.
    """
    id: str
    name: str
    provider_info: Optional[str] = None
    version: str = "1.0.0"
    
    def __post_init__(self):
        """Validate the identity after initialization."""
        if not self.id:
            raise ValueError("Agent ID cannot be empty")
        if not self.name:
            raise ValueError("Agent name cannot be empty")

    def to_dict(self) -> Dict[str, Any]:
        """Convert the identity to a dictionary representation."""
        return {
            "id": self.id,
            "name": self.name,
            "provider_info": self.provider_info,
            "version": self.version
        }


# ============================================================================
# Base Agent Definition
# ============================================================================

class BaseAgent(abc.ABC):
    """
    Abstract base class for all agents in the Nexus framework.
    
    This class defines the common interface and functionality that all
    agents must implement or inherit.
    """
    
    def __init__(
        self, 
        agent_name: str, 
        role: str, 
        agent_id: Optional[str] = None,
        capabilities: Optional[List[AgentCapability]] = None
    ):
        """
        Initialize a new agent.
        
        Args:
            agent_name: A human-readable name for the agent.
            role: The primary function or archetype of the agent.
            agent_id: Optional unique identifier for the agent. If not provided,
                     a UUID will be generated.
            capabilities: Optional list of capabilities this agent possesses.
        """
        # Generate a unique ID if not provided
        self.agent_id = agent_id or str(uuid.uuid4())
        self.agent_name = agent_name
        self.role = role
        self.capabilities = capabilities or []
        
        # Initialize an empty state dictionary
        # In the future, this will be replaced with an AgentState object
        self.state = {
            "conversation_history": [],
            "working_memory": {}
        }
    
    @abc.abstractmethod
    def process_message(self, message: 'Message') -> Optional['Message']:
        """
        Process an incoming message and optionally produce a response.
        
        This is the primary entry point for an agent to receive and respond
        to messages from other agents or external systems.
        
        Args:
            message: The incoming Message object to process.
            
        Returns:
            An optional Message object as a response. If None, no response
            is sent.
        """
        pass
    
    @abc.abstractmethod
    def get_capabilities(self) -> List[AgentCapability]:
        """
        Get the list of capabilities this agent provides.
        
        Returns:
            A list of AgentCapability objects describing what this agent can do.
        """
        pass
    
    @abc.abstractmethod
    def get_identity(self) -> AgentIdentity:
        """
        Get the identity of this agent.
        
        Returns:
            An AgentIdentity object representing this agent.
        """
        pass
    
    def __str__(self) -> str:
        """String representation of the agent."""
        return f"{self.agent_name} ({self.role})"
    
    def __repr__(self) -> str:
        """Detailed string representation of the agent."""
        return (f"{self.__class__.__name__}(agent_id='{self.agent_id}', "
                f"agent_name='{self.agent_name}', role='{self.role}', "
                f"capabilities={len(self.capabilities)})")
