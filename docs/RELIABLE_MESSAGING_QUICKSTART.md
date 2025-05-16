# Reliable Messaging Quick Reference Guide

This guide provides a quick reference for using the reliable messaging features in the Nexus Framework.

## Setup and Initialization

### 1. Initialize the RabbitMQ Broker

```python
from nexus_framework.messaging.rabbit_mq_broker import RabbitMQBroker

# Create the broker
broker = RabbitMQBroker()

# Default configuration for local RabbitMQ
broker_config = {
    'host': 'localhost',
    'port': 5672,
    'vhost': '/',
    'username': 'guest',
    'password': 'guest',
    'heartbeat': 60,
    'connection_attempts': 3
}

# Initialize the broker
initialized = broker.initialize(broker_config)
if not initialized:
    print("Failed to initialize RabbitMQ broker. Using legacy mode.")
    broker = None
```

### 2. Create the Reliable Communication Bus

```python
from nexus_framework.communication.reliable_bus import ReliableCommunicationBus

# Create the communication bus with the broker
communication_bus = ReliableCommunicationBus(
    broker=broker,
    legacy_mode=(broker is None)  # Fallback to legacy mode if broker init failed
)
```

### 3. Create a Reliable Group Chat Manager

```python
from nexus_framework.orchestration.reliable_groupchat import ReliableNexusGroupChatManager

# Create a reliable chat manager
chat_manager = ReliableNexusGroupChatManager(
    agents=your_agents,
    communication_bus=communication_bus,
    max_rounds=15
)

# You can access the workflow ID if needed
workflow_id = chat_manager.workflow_id
```

## Using with Agent Team Builder

```python
from agent_team_builder import AgentTeamBuilder

# Create the team builder
builder = AgentTeamBuilder('agent_model_config.json')

# Replace its communication bus with your reliable one
builder.communication_bus = communication_bus

# Define your team configuration
team_config = [
    {"type": "UserProxy", "name": "Human Interface"},
    {"type": "Assistant", "name": "Task Manager"},
    {"type": "Assistant", "name": "Research Assistant"}
]

# Build the team (will use your reliable communication bus)
agents = builder.build_team(team_config)

# Create a reliable chat manager
chat_manager = ReliableNexusGroupChatManager(
    agents=agents,
    communication_bus=communication_bus,
    max_rounds=15
)

# Now you can run chat sessions with reliable messaging
messages = chat_manager.run_chat(
    initial_sender=agents[0],
    initial_message_content="Hello team, let's work on a task."
)
```

## Advanced Features

### Message Sequence Checking

```python
# Check for missing sequences after a chat session
missing_sequences = chat_manager.sequence_tracker.get_missing_sequences(
    chat_manager.sequence_tracker.next_sequence
)

if missing_sequences:
    print(f"Warning: Missing message sequences detected: {missing_sequences}")
```

### Manual Deduplication

```python
# If you need to manually check for duplicates
message_id = "some-message-id"
if not chat_manager.message_deduplicator.is_duplicate(message_id):
    # Process the message
    process_message(message)
    # Mark it as seen
    chat_manager.message_deduplicator.mark_seen(message_id)
```

### Broker Health Checking

```python
# Check broker health
health_status = broker.health_check()

if health_status['status'] == 'healthy':
    print("Broker is healthy!")
else:
    print(f"Broker is unhealthy: {health_status['details']}")
```

### Graceful Shutdown

```python
# Always close the communication bus when done
communication_bus.close()
```

## Best Practices

1. **Always Check for RabbitMQ**
   - The reliable messaging features require RabbitMQ to be installed and running
   - Implement a fallback to legacy mode if RabbitMQ is not available

2. **Use Workflow IDs for Related Operations**
   - Always use the same workflow ID for related operations
   - This ensures proper message correlation and sequencing

3. **Close Resources Properly**
   - Always close the communication bus when done to release resources
   - This prevents connection leaks and other resource issues

4. **Handle Errors Gracefully**
   - Implement proper error handling for broker operations
   - Use try/except blocks to catch and handle exceptions

5. **Monitor Health Status**
   - Regularly check the health status of the broker and bus
   - Implement health checks in your application

6. **Use Appropriate Timeouts**
   - Configure appropriate timeouts for operations to prevent hanging
   - Implement circuit breakers for external service calls

## Troubleshooting

### Common Issues

1. **Connection Failures**
   - Ensure RabbitMQ is installed and running
   - Check host, port, username, and password
   - Verify that the RabbitMQ server is reachable from your application

2. **Message Delivery Issues**
   - Check for acknowledgment failures
   - Verify that recipients are properly registered
   - Look for errors in message processing

3. **Duplicate Messages**
   - Ensure that message IDs are unique
   - Check that the deduplicator is properly initialized
   - Verify that messages are being marked as seen

4. **Missing Messages**
   - Look for gaps in sequence numbers
   - Check for negative acknowledgments
   - Verify that all agents are properly registered

### Logging

Enable debug logging to get more detailed information:

```python
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

## Reference Documentation

For more detailed information, refer to:

- [Reliable Messaging Implementation](RELIABLE_MESSAGING_IMPLEMENTATION.md)
- [Enhancement Roadmap](ENHANCEMENT_ROADMAP.md)
- [RabbitMQ Documentation](https://www.rabbitmq.com/documentation.html)
