"""
Task management components for the Nexus framework.

This module provides utilities for managing and delegating tasks
between agents within the Nexus framework.
"""

import logging
from typing import Dict, List, Optional, Any, Union, Callable
import uuid
from datetime import datetime

from nexus_framework.core.agents import BaseAgent
from nexus_framework.core.messaging import Message
from nexus_framework.core.tasks import Task
from nexus_framework.communication.bus import CommunicationBus

# Set up logging
logger = logging.getLogger(__name__)


class TaskManager:
    """
    Manages tasks and their delegation to appropriate agents.
    
    The TaskManager is responsible for:
    - Tracking the status of tasks
    - Assigning tasks to agents based on their capabilities
    - Handling task completion and failure
    """
    
    def __init__(self, communication_bus: CommunicationBus):
        """
        Initialize a new TaskManager.
        
        Args:
            communication_bus: The CommunicationBus instance for messaging between agents.
        """
        self.communication_bus = communication_bus
        
        # Dictionary to track all tasks by their ID
        self._tasks: Dict[str, Task] = {}
        
        # Dictionary mapping task_id to assigned agent_id
        self._task_assignments: Dict[str, str] = {}
    
    def create_task(self, description: str, dependencies: Optional[List[str]] = None) -> Task:
        """
        Create a new task.
        
        Args:
            description: A human-readable description of the task.
            dependencies: Optional list of task_ids that must be completed before
                        this task can start.
            
        Returns:
            The created Task object.
        """
        task = Task(description=description, dependencies=dependencies or [])
        self._tasks[task.task_id] = task
        logger.info(f"Created task: {task.task_id} - {description}")
        return task
    
    def assign_task(self, task_id: str, agent_id: str) -> None:
        """
        Assign a task to a specific agent.
        
        Args:
            task_id: The ID of the task to assign.
            agent_id: The ID of the agent to assign the task to.
            
        Raises:
            ValueError: If the task does not exist or has dependencies that are not completed.
        """
        if task_id not in self._tasks:
            raise ValueError(f"Task {task_id} does not exist")
        
        task = self._tasks[task_id]
        
        # Check if dependencies are satisfied
        for dep_id in task.dependencies:
            if dep_id not in self._tasks:
                raise ValueError(f"Dependency task {dep_id} does not exist")
            
            if self._tasks[dep_id].status != "completed":
                raise ValueError(f"Dependency task {dep_id} is not completed")
        
        # Assign the task to the agent
        task.assigned_to = agent_id
        task.update_status("in_progress")
        self._task_assignments[task_id] = agent_id
        
        logger.info(f"Assigned task {task_id} to agent {agent_id}")
    
    def delegate_task(self, task: Task, agent_id: str, sender_id: str) -> None:
        """
        Delegate a task to an agent by sending a message.
        
        Args:
            task: The Task object to delegate.
            agent_id: The ID of the agent to delegate the task to.
            sender_id: The ID of the agent delegating the task.
            
        Raises:
            ValueError: If the agent is not registered.
        """
        # Store the task
        self._tasks[task.task_id] = task
        
        # Create a message with the task details
        message = Message(
            sender_id=sender_id,
            recipient_id=agent_id,
            content={
                "task_id": task.task_id,
                "description": task.description,
                "action": "execute_task"
            },
            content_type="application/json",
            role="assistant",
            metadata={"task_id": task.task_id}
        )
        
        # Send the message to the agent via the communication bus
        try:
            self.communication_bus.send_message(message)
            
            # Update task status and assignment
            task.assigned_to = agent_id
            task.update_status("in_progress")
            self._task_assignments[task.task_id] = agent_id
            
            logger.info(f"Delegated task {task.task_id} to agent {agent_id}")
        except Exception as e:
            logger.error(f"Error delegating task {task.task_id} to agent {agent_id}: {e}")
            task.update_status("failed")
            raise
    
    def delegate_task_by_capability(self, task: Task, capability_name: str, sender_id: str) -> Optional[str]:
        """
        Delegate a task to an agent that has a specific capability.
        
        Args:
            task: The Task object to delegate.
            capability_name: The name of the capability required to perform the task.
            sender_id: The ID of the agent delegating the task.
            
        Returns:
            The ID of the agent the task was delegated to, or None if no suitable agent was found.
            
        Raises:
            ValueError: If no agent with the specified capability is found.
        """
        # Find agents with the required capability
        capable_agents = []
        
        for agent in self.communication_bus.get_all_agents():
            for capability in agent.get_capabilities():
                if capability.name == capability_name:
                    capable_agents.append(agent)
                    break
        
        if not capable_agents:
            logger.warning(f"No agent found with capability: {capability_name}")
            return None
        
        # For now, just pick the first capable agent
        # In a more sophisticated implementation, this could consider agent workload,
        # performance history, or other factors
        target_agent = capable_agents[0]
        
        # Delegate the task
        self.delegate_task(task, target_agent.agent_id, sender_id)
        
        return target_agent.agent_id
    
    def update_task_status(self, task_id: str, new_status: str) -> None:
        """
        Update the status of a task.
        
        Args:
            task_id: The ID of the task to update.
            new_status: The new status for the task.
            
        Raises:
            ValueError: If the task does not exist.
        """
        if task_id not in self._tasks:
            raise ValueError(f"Task {task_id} does not exist")
        
        task = self._tasks[task_id]
        task.update_status(new_status)
        
        logger.info(f"Updated task {task_id} status to {new_status}")
        
        # If a task is completed or failed, check if it had child tasks
        # and update their status accordingly
        if new_status in ["completed", "failed"]:
            self._handle_task_completion(task, new_status)
    
    def set_task_result(self, task_id: str, result: Any) -> None:
        """
        Set the result of a task.
        
        Args:
            task_id: The ID of the task to update.
            result: The result of the task.
            
        Raises:
            ValueError: If the task does not exist.
        """
        if task_id not in self._tasks:
            raise ValueError(f"Task {task_id} does not exist")
        
        task = self._tasks[task_id]
        task.set_result(result)
        
        logger.info(f"Set result for task {task_id}")
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """
        Get a task by its ID.
        
        Args:
            task_id: The ID of the task to retrieve.
            
        Returns:
            The Task object if found, None otherwise.
        """
        return self._tasks.get(task_id)
    
    def get_agent_tasks(self, agent_id: str) -> List[Task]:
        """
        Get all tasks assigned to a specific agent.
        
        Args:
            agent_id: The ID of the agent.
            
        Returns:
            A list of Task objects assigned to the agent.
        """
        return [
            task for task in self._tasks.values()
            if task.assigned_to == agent_id
        ]
    
    def get_pending_tasks(self) -> List[Task]:
        """
        Get all tasks with 'pending' status.
        
        Returns:
            A list of pending Task objects.
        """
        return [
            task for task in self._tasks.values()
            if task.status == "pending"
        ]
    
    def _handle_task_completion(self, task: Task, status: str) -> None:
        """
        Handle the completion or failure of a task.
        
        This includes checking for dependent tasks and updating their status.
        
        Args:
            task: The Task object that was completed or failed.
            status: The final status of the task ('completed' or 'failed').
        """
        # If the task failed, mark all dependent tasks as failed as well
        if status == "failed":
            # Find all tasks that depend on this one
            dependent_tasks = [
                t for t in self._tasks.values()
                if task.task_id in t.dependencies
            ]
            
            for dep_task in dependent_tasks:
                logger.info(f"Marking dependent task {dep_task.task_id} as failed")
                dep_task.update_status("failed")
                
                # Recursively handle the failure of dependent tasks
                self._handle_task_completion(dep_task, "failed")
        
        # If the task was completed, check if any pending tasks now have
        # all their dependencies satisfied
        elif status == "completed":
            # Check all pending tasks
            for pending_task in self.get_pending_tasks():
                all_deps_completed = True
                
                for dep_id in pending_task.dependencies:
                    if dep_id not in self._tasks or self._tasks[dep_id].status != "completed":
                        all_deps_completed = False
                        break
                
                if all_deps_completed:
                    logger.info(f"Task {pending_task.task_id} is now ready to be started")
