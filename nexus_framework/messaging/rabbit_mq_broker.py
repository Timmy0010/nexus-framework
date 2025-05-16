"""
RabbitMQ broker implementation for the Nexus Framework.

This module provides a production-grade implementation of the MessageBroker
interface using RabbitMQ as the underlying messaging system.
"""

import pika
import uuid
import json
import logging
import time
import threading
from typing import Dict, Any, Callable, Optional, List, Tuple
from dataclasses import dataclass

from nexus_framework.messaging.broker import MessageBroker

logger = logging.getLogger(__name__)

@dataclass
class SubscriptionInfo:
    """Store information about active subscriptions."""
    callback: Callable
    consumer_tag: str
    queue_name: str
    channel: Any

class RabbitMQBroker(MessageBroker):
    """
    RabbitMQ implementation of the MessageBroker interface providing
    reliable message delivery with persistence and acknowledgments.
    """
    
    def __init__(self):
        """Initialize the RabbitMQ broker adapter."""
        self.connection = None
        self.channels = {}
        self.subscriptions = {}
        self.lock = threading.Lock()
        self.reconnect_thread = None
        self.should_reconnect = False
        self.connection_params = None
        self.unacked_messages = {}  # For tracking unacknowledged messages
        self.delivery_tags = {}  # For mapping message_id to channel and delivery_tag
        
    def initialize(self, config: Dict[str, Any]) -> bool:
        """
        Initialize the RabbitMQ connection.
        
        Args:
            config: RabbitMQ connection parameters
            
        Returns:
            True if connection was established, False otherwise
        """
        self.connection_params = config
        
        try:
            # Create connection parameters
            credentials = pika.PlainCredentials(
                config.get('username', 'guest'),
                config.get('password', 'guest')
            )
            
            parameters = pika.ConnectionParameters(
                host=config.get('host', 'localhost'),
                port=config.get('port', 5672),
                virtual_host=config.get('vhost', '/'),
                credentials=credentials,
                heartbeat=config.get('heartbeat', 60),
                connection_attempts=config.get('connection_attempts', 3)
            )
            
            # Establish connection
            self.connection = pika.BlockingConnection(parameters)
            logger.info("RabbitMQ connection established successfully")
            
            # Create dead letter exchange
            self._create_dead_letter_exchange()
            
            # Start reconnection thread
            self.should_reconnect = True
            self.reconnect_thread = threading.Thread(target=self._monitor_connection)
            self.reconnect_thread.daemon = True
            self.reconnect_thread.start()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize RabbitMQ connection: {e}")
            return False
    
    def _create_dead_letter_exchange(self):
        """Create the dead letter exchange and queue."""
        try:
            channel = self.connection.channel()
            
            # Declare dead letter exchange
            channel.exchange_declare(
                exchange='dead_letter',
                exchange_type='direct',
                durable=True
            )
            
            # Declare dead letter queue
            channel.queue_declare(
                queue='dead_letter_queue',
                durable=True
            )
            
            # Bind queue to exchange
            channel.queue_bind(
                queue='dead_letter_queue',
                exchange='dead_letter',
                routing_key='#'  # Catch all routing keys
            )
            
            channel.close()
            logger.info("Dead letter exchange and queue created")
            
        except Exception as e:
            logger.error(f"Failed to create dead letter exchange: {e}")
    
    def publish(self, 
                topic: str, 
                message: Dict[str, Any], 
                headers: Optional[Dict[str, Any]] = None) -> str:
        """
        Publish a message to the specified exchange.
        
        Args:
            topic: The exchange to publish to
            message: The message payload
            headers: Optional message headers
            
        Returns:
            Message ID of the published message
        """
        if headers is None:
            headers = {}
        
        # Generate a unique message ID if not provided
        message_id = headers.get('message_id', str(uuid.uuid4()))
        headers['message_id'] = message_id
        
        # Add timestamp if not present
        if 'timestamp' not in headers:
            headers['timestamp'] = int(time.time() * 1000)
        
        # Add sequence number if workflow_id is provided
        if 'workflow_id' in headers:
            if 'sequence_number' not in headers:
                # This would use a distributed sequence generator in production
                # For simplicity, we'll use timestamps for now
                headers['sequence_number'] = int(time.time() * 1000000)
        
        try:
            # Get or create a channel
            with self.lock:
                if 'publish' not in self.channels or self.channels['publish'].is_closed:
                    self.channels['publish'] = self.connection.channel()
                    
                channel = self.channels['publish']
            
            # Ensure the exchange exists
            channel.exchange_declare(
                exchange=topic,
                exchange_type='topic',
                durable=True
            )
            
            # Publish the message
            channel.basic_publish(
                exchange=topic,
                routing_key=headers.get('routing_key', ''),
                body=json.dumps(message).encode(),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Make message persistent
                    headers=headers,
                    message_id=message_id,
                    content_type='application/json',
                    content_encoding='utf-8'
                )
            )
            
            logger.debug(f"Published message {message_id} to {topic}")
            return message_id
            
        except Exception as e:
            logger.error(f"Failed to publish message to {topic}: {e}")
            self._handle_connection_failure()
            raise
    
    def subscribe(self, 
                  topic: str, 
                  callback: Callable[[Dict[str, Any], Dict[str, Any]], None],
                  queue_name: Optional[str] = None,
                  consumer_group: Optional[str] = None) -> str:
        """
        Subscribe to a topic to receive messages.
        
        Args:
            topic: The exchange to subscribe to
            callback: Function to call when messages are received
            queue_name: Optional specific queue name
            consumer_group: Optional consumer group name
            
        Returns:
            Subscription ID
        """
        try:
            # Generate a subscription ID
            subscription_id = str(uuid.uuid4())
            
            # Create a new channel for this subscription
            channel = self.connection.channel()
            
            # Set prefetch count to limit number of unacked messages
            channel.basic_qos(prefetch_count=10)
            
            # Ensure the exchange exists
            channel.exchange_declare(
                exchange=topic,
                exchange_type='topic',
                durable=True
            )
            
            # Use provided queue name or generate one
            actual_queue_name = queue_name 
            
            # If consumer group is provided, use it as a shared queue name
            if consumer_group:
                actual_queue_name = f"{topic}_{consumer_group}"
            
            # If no queue name provided, generate a unique one
            if not actual_queue_name:
                actual_queue_name = f"{topic}_{subscription_id}"
            
            # Declare the queue with dead letter exchange
            result = channel.queue_declare(
                queue=actual_queue_name,
                durable=True,
                arguments={
                    'x-dead-letter-exchange': 'dead_letter',
                    'x-dead-letter-routing-key': actual_queue_name
                }
            )
            
            # Bind queue to exchange
            channel.queue_bind(
                queue=actual_queue_name,
                exchange=topic,
                routing_key='#'  # Subscribe to all messages by default
            )
            
            # Wrap the callback to handle message deserialization
            def on_message(ch, method, properties, body):
                try:
                    # Parse the message
                    message_data = json.loads(body.decode())
                    
                    # Extract headers
                    headers = properties.headers or {}
                    headers['message_id'] = properties.message_id
                    
                    # Store delivery info for acknowledgment
                    self.delivery_tags[properties.message_id] = (ch, method.delivery_tag)
                    
                    # Call the user callback
                    callback(message_data, headers)
                    
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    # Negative acknowledge in case of processing error
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
            
            # Start consuming messages
            consumer_tag = channel.basic_consume(
                queue=actual_queue_name,
                on_message_callback=on_message,
                auto_ack=False  # Disable auto-ack for manual acknowledgment
            )
            
            # Store subscription info
            self.subscriptions[subscription_id] = SubscriptionInfo(
                callback=callback,
                consumer_tag=consumer_tag,
                queue_name=actual_queue_name,
                channel=channel
            )
            
            logger.info(f"Subscribed to {topic} with queue {actual_queue_name}")
            return subscription_id
            
        except Exception as e:
            logger.error(f"Failed to subscribe to {topic}: {e}")
            self._handle_connection_failure()
            raise
    
    def acknowledge(self, message_id: str) -> bool:
        """
        Acknowledge successful processing of a message.
        
        Args:
            message_id: The ID of the message to acknowledge
            
        Returns:
            True if acknowledgment was successful, False otherwise
        """
        try:
            if message_id in self.delivery_tags:
                channel, delivery_tag = self.delivery_tags.pop(message_id)
                channel.basic_ack(delivery_tag=delivery_tag)
                logger.debug(f"Acknowledged message {message_id}")
                return True
            else:
                logger.warning(f"No delivery tag found for message {message_id}")
                return False
        except Exception as e:
            logger.error(f"Failed to acknowledge message {message_id}: {e}")
            return False
    
    def negative_acknowledge(self, message_id: str, reason: str = "") -> bool:
        """
        Negatively acknowledge a message, indicating processing failure.
        
        Args:
            message_id: The ID of the message to negatively acknowledge
            reason: The reason for the failure
            
        Returns:
            True if the negative acknowledgment was recorded, False otherwise
        """
        try:
            if message_id in self.delivery_tags:
                channel, delivery_tag = self.delivery_tags.pop(message_id)
                
                # Add reason to headers if possible
                if reason:
                    logger.warning(f"NACK reason: {reason} for message {message_id}")
                
                # Negative acknowledge with requeue=False to send to dead letter queue
                channel.basic_nack(delivery_tag=delivery_tag, requeue=False)
                logger.debug(f"Negatively acknowledged message {message_id}")
                return True
            else:
                logger.warning(f"No delivery tag found for message {message_id}")
                return False
        except Exception as e:
            logger.error(f"Failed to negatively acknowledge message {message_id}: {e}")
            return False
    
    def unsubscribe(self, subscription_id: str) -> bool:
        """
        Unsubscribe from a previously subscribed topic.
        
        Args:
            subscription_id: The ID returned from subscribe()
            
        Returns:
            True if unsubscription was successful, False otherwise
        """
        try:
            if subscription_id in self.subscriptions:
                info = self.subscriptions.pop(subscription_id)
                
                # Cancel the consumer
                info.channel.basic_cancel(info.consumer_tag)
                
                # Close the channel
                info.channel.close()
                
                logger.info(f"Unsubscribed from {subscription_id}")
                return True
            else:
                logger.warning(f"No subscription found for ID {subscription_id}")
                return False
        except Exception as e:
            logger.error(f"Failed to unsubscribe {subscription_id}: {e}")
            return False
    
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
        try:
            with self.lock:
                if 'admin' not in self.channels or self.channels['admin'].is_closed:
                    self.channels['admin'] = self.connection.channel()
                    
                channel = self.channels['admin']
            
            arguments = {}
            
            if dead_letter_queue:
                arguments['x-dead-letter-exchange'] = 'dead_letter'
                arguments['x-dead-letter-routing-key'] = dead_letter_queue
            
            # Declare the queue
            channel.queue_declare(
                queue=queue_name,
                durable=durable,
                arguments=arguments
            )
            
            logger.info(f"Created queue {queue_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create queue {queue_name}: {e}")
            self._handle_connection_failure()
            return False
    
    def create_topic(self, topic_name: str) -> bool:
        """
        Create a topic/exchange for publishing messages.
        
        Args:
            topic_name: Name of the topic to create
            
        Returns:
            True if topic creation was successful, False otherwise
        """
        try:
            with self.lock:
                if 'admin' not in self.channels or self.channels['admin'].is_closed:
                    self.channels['admin'] = self.connection.channel()
                    
                channel = self.channels['admin']
            
            # Declare the exchange
            channel.exchange_declare(
                exchange=topic_name,
                exchange_type='topic',
                durable=True
            )
            
            logger.info(f"Created topic {topic_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create topic {topic_name}: {e}")
            self._handle_connection_failure()
            return False
    
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
        try:
            with self.lock:
                if 'admin' not in self.channels or self.channels['admin'].is_closed:
                    self.channels['admin'] = self.connection.channel()
                    
                channel = self.channels['admin']
            
            # Use provided routing key or default
            actual_routing_key = routing_key or '#'
            
            # Bind queue to exchange
            channel.queue_bind(
                queue=queue_name,
                exchange=topic_name,
                routing_key=actual_routing_key
            )
            
            logger.info(f"Bound queue {queue_name} to topic {topic_name} with routing key {actual_routing_key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to bind queue {queue_name} to topic {topic_name}: {e}")
            self._handle_connection_failure()
            return False
    
    def close(self) -> None:
        """Close broker connections and release resources."""
        self.should_reconnect = False
        
        # Close all subscription channels
        for subscription_id, info in self.subscriptions.items():
            try:
                info.channel.close()
            except Exception:
                pass
        
        self.subscriptions.clear()
        
        # Close all other channels
        for channel_name, channel in self.channels.items():
            try:
                channel.close()
            except Exception:
                pass
        
        self.channels.clear()
        
        # Close the connection
        if self.connection and self.connection.is_open:
            try:
                self.connection.close()
            except Exception:
                pass
        
        logger.info("RabbitMQ broker closed")
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check the health of the broker connection.
        
        Returns:
            Dictionary with health check results
        """
        result = {
            'status': 'healthy',
            'details': {
                'connection': 'connected' if self.connection and self.connection.is_open else 'disconnected',
                'channels': {},
                'subscriptions': len(self.subscriptions)
            }
        }
        
        # Check each channel
        for name, channel in self.channels.items():
            result['details']['channels'][name] = 'open' if channel.is_open else 'closed'
        
        # Set overall status
        if not self.connection or not self.connection.is_open:
            result['status'] = 'unhealthy'
            
        return result
    
    def _handle_connection_failure(self) -> None:
        """Handle connection failures by triggering reconnection."""
        if self.connection and not self.connection.is_open:
            logger.warning("Connection failure detected")
            # The reconnection thread will handle reconnecting
    
    def _monitor_connection(self) -> None:
        """Monitor the connection and reconnect if needed."""
        while self.should_reconnect:
            if not self.connection or not self.connection.is_open:
                try:
                    logger.info("Attempting to reconnect to RabbitMQ")
                    
                    # Create new connection parameters
                    credentials = pika.PlainCredentials(
                        self.connection_params.get('username', 'guest'),
                        self.connection_params.get('password', 'guest')
                    )
                    
                    parameters = pika.ConnectionParameters(
                        host=self.connection_params.get('host', 'localhost'),
                        port=self.connection_params.get('port', 5672),
                        virtual_host=self.connection_params.get('vhost', '/'),
                        credentials=credentials,
                        heartbeat=self.connection_params.get('heartbeat', 60),
                        connection_attempts=self.connection_params.get('connection_attempts', 3)
                    )
                    
                    # Establish connection
                    self.connection = pika.BlockingConnection(parameters)
                    logger.info("RabbitMQ connection re-established successfully")
                    
                    # Re-create channels
                    self.channels.clear()
                    
                    # Re-create dead letter exchange
                    self._create_dead_letter_exchange()
                    
                    # Re-subscribe to all topics
                    self._resubscribe_all()
                    
                except Exception as e:
                    logger.error(f"Failed to reconnect to RabbitMQ: {e}")
                    # Wait before retrying
                    time.sleep(5)
            
            # Check connection status periodically
            time.sleep(10)
    
    def _resubscribe_all(self) -> None:
        """Re-subscribe to all topics after reconnection."""
        old_subscriptions = self.subscriptions.copy()
        self.subscriptions.clear()
        
        for subscription_id, info in old_subscriptions.items():
            try:
                logger.info(f"Re-subscribing to {info.queue_name}")
                
                # Create a new channel
                channel = self.connection.channel()
                
                # Set prefetch count
                channel.basic_qos(prefetch_count=10)
                
                # Declare the queue (it should already exist if durable)
                channel.queue_declare(
                    queue=info.queue_name,
                    durable=True,
                    passive=True  # Just check if it exists, don't create
                )
                
                # Start consuming messages
                consumer_tag = channel.basic_consume(
                    queue=info.queue_name,
                    on_message_callback=lambda ch, method, properties, body: self._on_message_wrapper(
                        ch, method, properties, body, info.callback
                    ),
                    auto_ack=False
                )
                
                # Store subscription info
                self.subscriptions[subscription_id] = SubscriptionInfo(
                    callback=info.callback,
                    consumer_tag=consumer_tag,
                    queue_name=info.queue_name,
                    channel=channel
                )
                
                logger.info(f"Re-subscribed to {info.queue_name}")
                
            except Exception as e:
                logger.error(f"Failed to re-subscribe to {info.queue_name}: {e}")
    
    def _on_message_wrapper(self, ch, method, properties, body, callback):
        """Wrapper for handling messages after reconnection."""
        try:
            # Parse the message
            message_data = json.loads(body.decode())
            
            # Extract headers
            headers = properties.headers or {}
            headers['message_id'] = properties.message_id
            
            # Store delivery info for acknowledgment
            self.delivery_tags[properties.message_id] = (ch, method.delivery_tag)
            
            # Call the user callback
            callback(message_data, headers)
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            # Negative acknowledge in case of processing error
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
