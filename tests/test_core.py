"""
Tests for the core components of the Nexus framework.
"""

import pytest
from nexus_framework.core.agents import AgentCapability, AgentIdentity, BaseAgent
from nexus_framework.core.messaging import Message
from nexus_framework.core.tasks import Task
from nexus_framework.core.state import AgentState

# Test AgentCapability
def test_agent_capability():
    # Create a capability
    capability = AgentCapability(
        name="test_capability",
        description="Test capability description"
    )
    
    # Check attributes
    assert capability.name == "test_capability"
    assert capability.description == "Test capability description"
    assert capability.parameters_schema is None
    
    # Test with parameters schema
    params_schema = {
        "type": "object",
        "properties": {
            "param1": {"type": "string"},
            "param2": {"type": "number"}
        }
    }
    
    capability_with_params = AgentCapability(
        name="parameterized_capability",
        description="Capability with parameters",
        parameters_schema=params_schema
    )
    
    assert capability_with_params.parameters_schema == params_schema

# Test AgentIdentity
def test_agent_identity():
    # Create an identity
    identity = AgentIdentity(
        id="test-agent-123",
        name="Test Agent",
        provider_info="Test Provider",
        version="1.0.0"
    )
    
    # Check attributes
    assert identity.id == "test-agent-123"
    assert identity.name == "Test Agent"
    assert identity.provider_info == "Test Provider"
    assert identity.version == "1.0.0"
    
    # Test to_dict method
    identity_dict = identity.to_dict()
    assert identity_dict["id"] == "test-agent-123"
    assert identity_dict["name"] == "Test Agent"
    assert identity_dict["provider_info"] == "Test Provider"
    assert identity_dict["version"] == "1.0.0"

# Test Message
def test_message():
    # Create a message
    message = Message(
        sender_id="sender-123",
        recipient_id="recipient-456",
        content="Hello, world!",
        content_type="text/plain",
        role="user"
    )
    
    # Check attributes
    assert message.sender_id == "sender-123"
    assert message.recipient_id == "recipient-456"
    assert message.content == "Hello, world!"
    assert message.content_type == "text/plain"
    assert message.role == "user"
    
    # Test to_dict and from_dict methods
    message_dict = message.to_dict()
    recreated_message = Message.from_dict(message_dict)
    
    assert recreated_message.sender_id == message.sender_id
    assert recreated_message.recipient_id == message.recipient_id
    assert recreated_message.content == message.content
    assert recreated_message.content_type == message.content_type
    assert recreated_message.role == message.role

# Test Task
def test_task():
    # Create a task
    task = Task(description="Test task")
    
    # Check attributes
    assert task.description == "Test task"
    assert task.status == "pending"
    assert task.assigned_to is None
    assert task.sub_tasks == []
    assert task.result is None
    assert task.dependencies == []
    
    # Test status update
    task.update_status("in_progress")
    assert task.status == "in_progress"
    
    # Test adding a sub-task
    sub_task = Task(description="Sub-task")
    task.add_sub_task(sub_task)
    assert len(task.sub_tasks) == 1
    assert task.sub_tasks[0].description == "Sub-task"
    
    # Test setting result
    task.set_result("Completed successfully")
    assert task.result == "Completed successfully"

# Test AgentState
def test_agent_state():
    # Create an agent state
    state = AgentState()
    
    # Check initial state
    assert state.conversation_history == []
    assert state.current_task_id is None
    assert state.working_memory == {}
    
    # Test adding messages
    message1 = Message(
        sender_id="sender-123",
        recipient_id="recipient-456",
        content="Message 1",
        content_type="text/plain"
    )
    
    message2 = Message(
        sender_id="recipient-456",
        recipient_id="sender-123",
        content="Message 2",
        content_type="text/plain"
    )
    
    state.add_message(message1)
    state.add_message(message2)
    
    assert len(state.conversation_history) == 2
    assert state.conversation_history[0].content == "Message 1"
    assert state.conversation_history[1].content == "Message 2"
    
    # Test getting recent messages
    recent_messages = state.get_recent_messages(1)
    assert len(recent_messages) == 1
    assert recent_messages[0].content == "Message 2"
    
    # Test working memory operations
    state.set_working_memory("key1", "value1")
    state.set_working_memory("key2", 42)
    
    assert state.get_working_memory("key1") == "value1"
    assert state.get_working_memory("key2") == 42
    assert state.get_working_memory("non_existent_key", "default") == "default"
    
    # Test current task
    state.set_current_task("task-123")
    assert state.current_task_id == "task-123"
    
    # Test clearing working memory
    state.clear_working_memory()
    assert state.working_memory == {}
