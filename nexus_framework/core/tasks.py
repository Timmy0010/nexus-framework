"""
Task management structures for the Nexus framework.

This module defines the structures used to represent and track tasks
within the Nexus agent framework.
"""

from dataclasses import dataclass, field
from datetime import datetime
import uuid
from typing import Dict, List, Any, Optional, Union

@dataclass
class Task:
    """
    Represents a unit of work to be performed within the framework.
    
    Tasks can represent high-level objectives that may be broken down
    into smaller sub-tasks, forming a hierarchical structure of work.
    """
    description: str
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: str = "pending"  # pending, in_progress, completed, failed, deferred
    assigned_to: Optional[str] = None
    sub_tasks: List['Task'] = field(default_factory=list)
    result: Optional[Any] = None
    dependencies: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """Validate the task after initialization."""
        if not self.description:
            raise ValueError("Task description cannot be empty")
        
        # Validate status
        valid_statuses = ["pending", "in_progress", "completed", "failed", "deferred"]
        if self.status not in valid_statuses:
            raise ValueError(f"Invalid status: {self.status}. Must be one of {valid_statuses}")
    
    def update_status(self, new_status: str) -> None:
        """
        Update the status of this task.
        
        Args:
            new_status: The new status for the task.
        """
        valid_statuses = ["pending", "in_progress", "completed", "failed", "deferred"]
        if new_status not in valid_statuses:
            raise ValueError(f"Invalid status: {new_status}. Must be one of {valid_statuses}")
        
        self.status = new_status
        self.last_updated = datetime.now()
    
    def add_sub_task(self, sub_task: 'Task') -> None:
        """
        Add a sub-task to this task.
        
        Args:
            sub_task: The Task object to add as a sub-task.
        """
        self.sub_tasks.append(sub_task)
        self.last_updated = datetime.now()
    
    def set_result(self, result: Any) -> None:
        """
        Set the result of this task.
        
        Args:
            result: The result of the task.
        """
        self.result = result
        self.last_updated = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the task to a dictionary representation."""
        return {
            "task_id": self.task_id,
            "description": self.description,
            "status": self.status,
            "assigned_to": self.assigned_to,
            "sub_tasks": [st.to_dict() for st in self.sub_tasks],
            "result": self.result,
            "dependencies": self.dependencies,
            "created_at": self.created_at.isoformat(),
            "last_updated": self.last_updated.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        """Create a Task instance from a dictionary."""
        # Handle nested sub-tasks
        sub_tasks_data = data.pop('sub_tasks', [])
        sub_tasks = [cls.from_dict(st) for st in sub_tasks_data]
        
        # Convert ISO timestamp strings back to datetime
        for dt_field in ['created_at', 'last_updated']:
            if isinstance(data.get(dt_field), str):
                data[dt_field] = datetime.fromisoformat(data[dt_field])
        
        # Create the task
        task = cls(**data)
        task.sub_tasks = sub_tasks
        
        return task
