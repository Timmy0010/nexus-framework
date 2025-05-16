"""
Exceptions for the Nexus framework.

This module defines the custom exception classes used throughout the
Nexus framework for handling various types of errors.
"""

class NexusError(Exception):
    """Base exception class for all Nexus framework errors."""
    pass


class NexusAgentError(NexusError):
    """Exception for errors originating from an agent."""
    pass


class NexusToolError(NexusAgentError):
    """Exception for errors related to tool invocation."""
    pass


class NexusConfigurationError(NexusError):
    """Exception for errors related to framework setup or agent configuration."""
    pass


class NexusCommunicationError(NexusError):
    """Exception for errors related to agent communication."""
    pass


class NexusTaskError(NexusError):
    """Exception for errors related to task management."""
    pass


class NexusSecurityError(NexusError):
    """Exception for security-related errors."""
    pass


class NexusTimeoutError(NexusError):
    """Exception for timeout errors."""
    pass


class NexusLLMError(NexusError):
    """Exception for errors related to LLM interaction."""
    pass


class NexusMCPError(NexusToolError):
    """Exception for errors related to MCP tool invocation."""
    pass


class NexusFileAccessError(NexusError):
    """Exception for errors related to file access."""
    pass
