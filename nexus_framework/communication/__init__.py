"""
Communication components for the Nexus framework.

This package contains the components responsible for managing
communication between agents within the Nexus framework.
"""

from nexus_framework.communication.bus import CommunicationBus
from nexus_framework.communication.reliable_bus import ReliableCommunicationBus

__all__ = ['CommunicationBus', 'ReliableCommunicationBus']
