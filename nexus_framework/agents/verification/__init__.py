# nexus_framework/agents/verification/__init__.py
"""
Verification agents and related components for the Nexus Framework.

This package provides security verification and sanitization for messages 
in the Nexus Framework.
"""

from nexus_framework.agents.verification.verification_agent import (
    VerificationAgent,
    VerificationRule,
    MessageSanitizer
)

__all__ = [
    'VerificationAgent',
    'VerificationRule',
    'MessageSanitizer'
]
