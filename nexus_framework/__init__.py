"""
Nexus Advanced Agent Framework

A flexible, extensible framework for building and managing AI agent systems.

This framework provides the foundational infrastructure for creating intelligent
agents that can collaborate, reason, and interact with various tools and data
sources to automate complex tasks and build next-generation software applications.
"""

__version__ = "0.1.0"

# Make core components available at the package level
from nexus_framework.core.agents import BaseAgent, AgentCapability, AgentIdentity
from nexus_framework.core.messaging import Message
from nexus_framework.core.tasks import Task
from nexus_framework.core.state import AgentState
from nexus_framework.core.message_parser import MessageParser, MessageHandler
from nexus_framework.core.exceptions import (
    NexusError, NexusAgentError, NexusToolError, NexusConfigurationError,
    NexusCommunicationError, NexusTaskError, NexusSecurityError,
    NexusTimeoutError, NexusLLMError, NexusMCPError, NexusFileAccessError
)

# Make specialized agents available
from nexus_framework.agents import (
    UserProxyAgent, AssistantAgent, PlannerAgent, ExecutorAgent
)

# Make communication and orchestration components available
from nexus_framework.communication.bus import CommunicationBus
from nexus_framework.orchestration import NexusGroupChatManager, TaskManager

# Make tool integration components available
from nexus_framework.tools.mcp_connector import MCPConnector

# Make security components available
from nexus_framework.security.security_manager import SecurityManager

# Make observability components available
from nexus_framework.observability import (
    configure_logging, LoggingContext, 
    TracingManager, TracingContext, ChildSpanContext,
    MetricsCollector, MetricsContext, CommonMetrics
)

__all__ = [
    # Core
    'BaseAgent', 'AgentCapability', 'AgentIdentity', 
    'Message', 'Task', 'AgentState',
    'MessageParser', 'MessageHandler',
    
    # Exceptions
    'NexusError', 'NexusAgentError', 'NexusToolError', 'NexusConfigurationError',
    'NexusCommunicationError', 'NexusTaskError', 'NexusSecurityError',
    'NexusTimeoutError', 'NexusLLMError', 'NexusMCPError', 'NexusFileAccessError',
    
    # Specialized Agents
    'UserProxyAgent', 'AssistantAgent', 'PlannerAgent', 'ExecutorAgent',
    
    # Communication and Orchestration
    'CommunicationBus', 'NexusGroupChatManager', 'TaskManager',
    
    # Tool Integration
    'MCPConnector',
    
    # Security
    'SecurityManager',
    
    # Observability
    'configure_logging', 'LoggingContext',
    'TracingManager', 'TracingContext', 'ChildSpanContext',
    'MetricsCollector', 'MetricsContext', 'CommonMetrics'
]
