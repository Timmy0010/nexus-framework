"""
Agents package for the Nexus framework.

This package contains specialized agent implementations built upon
the BaseAgent abstraction.
"""

from nexus_framework.agents.specialized import UserProxyAgent
from nexus_framework.agents.specialized_part2 import AssistantAgent
from nexus_framework.agents.specialized_part3 import PlannerAgent, ExecutorAgent

__all__ = ['UserProxyAgent', 'AssistantAgent', 'PlannerAgent', 'ExecutorAgent']
