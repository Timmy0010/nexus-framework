"""
Message broker interface for the Nexus Framework.

This module defines the core interface that all message broker implementations
must adhere to, providing a consistent API for reliable messaging.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Callable, Optional, List

class MessageBroker(ABC):
    """
    Abstract interface for message broker implementations.
    Defines the contract that all broker adapters must fulfill.
    """
    
    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> bool:
        """
        Initialize the broker connection with the provided configuration.
        
        Args:
            config: Broker-specific configuration parameters
            
        Returns:
            True if initialization was successful, False otherwise
        """
        pass
    
    @abstractmethod
    def publish(self, 
                topic: str, 
                message: Dict[str, Any], 
                headers: Optional[Dict[str, Any]] = None) -> str:
        """
        Publish a message to the specified topic.
        
        Args:
            topic: The topic/exchange/subject to publish to
            message: The message payload
            headers: Optional message headers
            
        Returns:
            Message ID of the published message
        """
        pass
    
    @abstractmethod
    def subscribe(self, 
                  topic: str, 
                  callback: Callable[[Dict[str, Any], Dict[str, Any]], None],
                  queue_name: Optional[str] = None,
                  consumer_group: Optional[str] = None) -> str:
        """
        Subscribe to a topic to receive messages.
        
        Args:
            topic: The topic/exchange/subject to subscribe to
            callback: Function to call when messages are received
            queue_name: Optional specific queue name
            consumer_group: Optional consumer group name
            
        Returns:
            Subscription ID that can be used to unsubscribe
        """
        pass
    
    @abstractmethod
    def acknowledge(self, message_id: str) -> bool:
        """
        Acknowledge successful processing of a message.
        
        Args:
            message_id: The ID of the message to acknowledge
            
        Returns:
            True if acknowledgment was successful, False otherwise
        """
        pass
    
    @abstractmethod
    def negative_acknowledge(self, message_id: str, reason: str) -> bool:
        """
        Negatively acknowledge a message, indicating processing failure.
        
        Args:
            message_id: The ID of the message to negatively acknowledge
            reason: The reason for the failure
            
        Returns:
            True if the negative acknowledgment was recorded, False otherwise
        """
        pass
    
    @abstractmethod
    def unsubscribe(self, subscription_id: str) -> bool:
        """
        Unsubscribe from a previously subscribed topic.
        
        Args:
            subscription_id: The ID returned from subscribe()
            
        Returns:
            True if unsubscription was successful, False otherwise
        """
        pass
    
    @abstractmethod
    def create_queue(self, 
                     queue_name: str, 
                     durable: bool = True,
                     dead_letter_queue: Optional[str] = None) -> bool:
        """
        Create a named queue with specified properties.
        
        Args:
            queue_name: Name of the queue to create
            durable: Whether the queue should survive broker restarts
            dead_letter_queue: Optional name of dead letter queue for failed messages
            
        Returns:
            True if queue creation was successful, False otherwise
        """
        pass
    
    @abstractmethod
    def create_topic(self, topic_name: str) -> bool:
        """
        Create a topic/exchange for publishing messages.
        
        Args:
            topic_name: Name of the topic to create
            
        Returns:
            True if topic creation was successful, False otherwise
        """
        pass
    
    @abstractmethod
    def bind_queue_to_topic(self, 
                           queue_name: str, 
                           topic_name: str,
                           routing_key: Optional[str] = None) -> bool:
        """
        Bind a queue to a topic with an optional routing key.
        
        Args:
            queue_name: Name of the queue to bind
            topic_name: Name of the topic to bind to
            routing_key: Optional routing key for message filtering
            
        Returns:
            True if binding was successful, False otherwise
        """
        pass
    
    @abstractmethod
    def close(self) -> None:
        """
        Close broker connections and release resources.
        """
        pass
    
    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """
        Check the health of the broker connection.
        
        Returns:
            Dictionary with health check results
        """
        pass
