"""
Core messaging structures for the Nexus framework.

This module defines the fundamental data structures for communication
between agents within the Nexus framework.
"""

from dataclasses import dataclass, field
from datetime import datetime
import uuid
from typing import Dict, Any, Optional, Union

@dataclass
class Message:
    """
    Represents a message exchanged between agents in the Nexus framework.
    
    A message is the standard unit of communication and contains metadata
    about the sender, recipient, and the actual content being transmitted.
    """
    sender_id: str
    recipient_id: str
    content: Any
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    content_type: str = "text/plain"
    role: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Validate the message after initialization."""
        if not self.sender_id:
            raise ValueError("Sender ID cannot be empty")
        if not self.recipient_id:
            raise ValueError("Recipient ID cannot be empty")
        
        # Initialize metadata if None
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the message to a dictionary representation."""
        return {
            "message_id": self.message_id,
            "sender_id": self.sender_id,
            "recipient_id": self.recipient_id,
            "timestamp": self.timestamp.isoformat(),
            "content": self.content,
            "content_type": self.content_type,
            "role": self.role,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """Create a Message instance from a dictionary."""
        # Convert ISO timestamp string back to datetime
        if isinstance(data.get('timestamp'), str):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        
        return cls(**data)
    
    def __str__(self) -> str:
        """String representation of the message."""
        return (f"Message from {self.sender_id} to {self.recipient_id} "
                f"({self.content_type}): {str(self.content)[:50]}...")
