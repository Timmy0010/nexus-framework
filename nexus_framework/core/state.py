"""
State management structures for the Nexus framework.

This module defines the structures used to manage the internal state
of agents within the Nexus framework.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime

from nexus_framework.core.messaging import Message

@dataclass
class AgentState:
    """
    Encapsulates the internal state of an agent.
    
    This structure is used to maintain an agent's contextual information,
    including its conversation history and any working memory needed for
    its operations.
    """
    conversation_history: List[Message] = field(default_factory=list)
    current_task_id: Optional[str] = None
    working_memory: Dict[str, Any] = field(default_factory=dict)
    last_updated: datetime = field(default_factory=datetime.now)
    
    def add_message(self, message: Message) -> None:
        """
        Add a message to the conversation history.
        
        Args:
            message: The Message object to add to history.
        """
        self.conversation_history.append(message)
        self.last_updated = datetime.now()
    
    def set_current_task(self, task_id: Optional[str]) -> None:
        """
        Set the ID of the task the agent is currently focused on.
        
        Args:
            task_id: The ID of the current task or None if no active task.
        """
        self.current_task_id = task_id
        self.last_updated = datetime.now()
    
    def get_recent_messages(self, count: int = 5) -> List[Message]:
        """
        Get the most recent messages from the conversation history.
        
        Args:
            count: Maximum number of messages to retrieve.
            
        Returns:
            A list of the most recent Message objects.
        """
        return self.conversation_history[-count:] if self.conversation_history else []
    
    def set_working_memory(self, key: str, value: Any) -> None:
        """
        Store a value in the agent's working memory.
        
        Args:
            key: The key under which to store the value.
            value: The value to store.
        """
        self.working_memory[key] = value
        self.last_updated = datetime.now()
    
    def get_working_memory(self, key: str, default: Any = None) -> Any:
        """
        Retrieve a value from the agent's working memory.
        
        Args:
            key: The key for which to retrieve the value.
            default: The default value to return if the key is not found.
            
        Returns:
            The value associated with the key, or the default if not found.
        """
        return self.working_memory.get(key, default)
    
    def clear_working_memory(self) -> None:
        """Clear all entries in the agent's working memory."""
        self.working_memory.clear()
        self.last_updated = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the agent state to a dictionary representation."""
        return {
            "conversation_history": [msg.to_dict() for msg in self.conversation_history],
            "current_task_id": self.current_task_id,
            "working_memory": self.working_memory,
            "last_updated": self.last_updated.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentState':
        """Create an AgentState instance from a dictionary."""
        # Handle nested message history
        conversation_data = data.pop('conversation_history', [])
        conversation_history = [Message.from_dict(msg) for msg in conversation_data]
        
        # Convert ISO timestamp string back to datetime
        if isinstance(data.get('last_updated'), str):
            data['last_updated'] = datetime.fromisoformat(data['last_updated'])
        
        # Create the state
        state = cls(**data)
        state.conversation_history = conversation_history
        
        return state
