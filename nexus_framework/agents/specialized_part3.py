"""
Specialized agent implementations for the Nexus framework - Part 3.

This module defines remaining concrete agent classes that extend the BaseAgent
abstraction with specific roles and capabilities.
"""

import logging
from typing import Dict, List, Optional, Any, Union, Callable
import json
from datetime import datetime

from nexus_framework.core.agents import BaseAgent, AgentCapability, AgentIdentity
from nexus_framework.core.messaging import Message
from nexus_framework.core.tasks import Task
from nexus_framework.core.state import AgentState
from nexus_framework.core.message_parser import MessageParser, MessageHandler
from nexus_framework.tools.mcp_connector import MCPConnector

# Set up logging
logger = logging.getLogger(__name__)


class PlannerAgent(BaseAgent):
    """
    An agent specialized in task decomposition and planning.
    
    Given a complex or high-level goal, this agent breaks it down into
    a sequence of smaller, more manageable sub-tasks and potentially
    determines which agents should handle each sub-task.
    """
    
    def __init__(
        self,
        agent_name: str = "Planner",
        agent_id: Optional[str] = None,
        system_prompt: str = "You are a planning agent that excels at breaking down complex tasks into manageable steps.",
        llm_config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize a new PlannerAgent.
        
        Args:
            agent_name: A human-readable name for this agent.
            agent_id: Optional unique identifier for this agent.
            system_prompt: The system prompt that defines this agent's behavior.
            llm_config: Optional configuration for the LLM integration.
        """
        super().__init__(agent_name=agent_name, role="planner", agent_id=agent_id)
        self.system_prompt = system_prompt
        self.llm_config = llm_config or {}
        
        # Replace the default state with AgentState
        self.state = AgentState()
        
        # Store the system prompt in working memory
        self.state.set_working_memory("system_prompt", system_prompt)
        
        # Define capabilities
        self.capabilities = [
            AgentCapability(
                name="task_planning",
                description="Ability to break down complex tasks into smaller sub-tasks."
            ),
            AgentCapability(
                name="llm_reasoning",
                description="Ability to leverage an LLM for planning and reasoning."
            )
        ]
    
    def process_message(self, message: Message) -> Optional[Message]:
        """
        Process an incoming message by generating a plan.
        
        Args:
            message: The incoming Message object to process.
            
        Returns:
            A Message object containing the plan.
        """
        # Add the message to conversation history
        self.state.add_message(message)
        
        # Parse the message based on content_type and role
        try:
            parsed_message = MessageHandler.handle_by_role(message)
            logger.debug(f"Parsed message: {parsed_message}")
        except ValueError as e:
            logger.error(f"Error parsing message: {e}")
            return Message(
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                content=f"Error processing your message: {str(e)}",
                content_type="text/plain",
                role="assistant"
            )
        
        # Extract the task description from the message
        task_description = parsed_message["content"]
        
        # Create a Task object for the main task
        main_task = Task(description=task_description)
        
        # Generate a plan (sub-tasks) for the main task
        sub_tasks = self._generate_plan(main_task)
        
        # Add all sub-tasks to the main task
        for sub_task in sub_tasks:
            main_task.add_sub_task(sub_task)
        
        # Store the main task in working memory
        self.state.set_working_memory("current_plan", main_task.to_dict())
        
        # Create a human-readable representation of the plan
        plan_text = self._format_plan_as_text(main_task)
        
        # Return the plan as a response
        return Message(
            sender_id=self.agent_id,
            recipient_id=message.sender_id,
            content=plan_text,
            content_type="text/plain",
            role="assistant"
        )
    
    def get_capabilities(self) -> List[AgentCapability]:
        """
        Get the list of capabilities this agent provides.
        
        Returns:
            A list of AgentCapability objects.
        """
        return self.capabilities
    
    def get_identity(self) -> AgentIdentity:
        """
        Get the identity of this agent.
        
        Returns:
            An AgentIdentity object.
        """
        return AgentIdentity(
            id=self.agent_id,
            name=self.agent_name,
            provider_info="Nexus Framework",
            version="1.0.0"
        )
    
    def _generate_plan(self, task: Task) -> List[Task]:
        """
        Generate a plan (list of sub-tasks) for a given task.
        
        Args:
            task: The Task object to plan for.
            
        Returns:
            A list of Task objects representing the sub-tasks in the plan.
        """
        # TODO: Replace this placeholder with actual LLM-based plan generation
        # This is where we would call the LLM API to generate a plan
        
        logger.info(f"Generating plan for task: {task.description}")
        
        # This is a placeholder that returns a simple predefined plan
        # In a real implementation, this would use the LLM to generate a
        # task-specific plan based on the task description
        
        # Simple examples for different task types
        if "code" in task.description.lower():
            return [
                Task(description="Understand the requirements"),
                Task(description="Design the solution architecture"),
                Task(description="Implement core functionality"),
                Task(description="Write tests"),
                Task(description="Refactor and optimize"),
                Task(description="Document the code")
            ]
        elif "research" in task.description.lower():
            return [
                Task(description="Define research questions"),
                Task(description="Collect relevant information"),
                Task(description="Analyze the information"),
                Task(description="Draw conclusions"),
                Task(description="Prepare a report")
            ]
        else:
            # Generic plan for other types of tasks
            return [
                Task(description="Analyze the problem"),
                Task(description="Gather necessary resources"),
                Task(description="Execute core steps"),
                Task(description="Verify results"),
                Task(description="Document the process and outcome")
            ]
    
    def _format_plan_as_text(self, task: Task) -> str:
        """
        Format a task and its sub-tasks as a human-readable text.
        
        Args:
            task: The Task object with sub-tasks to format.
            
        Returns:
            A formatted string representation of the plan.
        """
        lines = [f"# Plan for: {task.description}\n"]
        
        for i, sub_task in enumerate(task.sub_tasks, start=1):
            lines.append(f"{i}. {sub_task.description}")
            
            # Handle nested sub-tasks (if any)
            if sub_task.sub_tasks:
                for j, nested_task in enumerate(sub_task.sub_tasks, start=1):
                    lines.append(f"   {i}.{j}. {nested_task.description}")
        
        return "\n".join(lines)


class ExecutorAgent(BaseAgent):
    """
    An agent responsible for executing specific, well-defined tasks.
    
    This agent focuses on carrying out instructions rather than high-level
    reasoning or planning. It often involves actions like running code,
    performing calculations, or making precise tool calls.
    """
    
    def __init__(
        self,
        agent_name: str = "Executor",
        agent_id: Optional[str] = None,
        system_prompt: str = "You are an executor agent that specializes in carrying out well-defined tasks.",
        mcp_connector: Optional[MCPConnector] = None,
        llm_config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize a new ExecutorAgent.
        
        Args:
            agent_name: A human-readable name for this agent.
            agent_id: Optional unique identifier for this agent.
            system_prompt: The system prompt that defines this agent's behavior.
            mcp_connector: Optional MCPConnector for accessing external tools.
            llm_config: Optional configuration for the LLM integration.
        """
        super().__init__(agent_name=agent_name, role="executor", agent_id=agent_id)
        self.system_prompt = system_prompt
        self.mcp_connector = mcp_connector
        self.llm_config = llm_config or {}
        
        # Replace the default state with AgentState
        self.state = AgentState()
        
        # Store the system prompt in working memory
        self.state.set_working_memory("system_prompt", system_prompt)
        
        # Define capabilities
        self.capabilities = [
            AgentCapability(
                name="task_execution",
                description="Ability to execute well-defined tasks."
            ),
            AgentCapability(
                name="llm_reasoning",
                description="Ability to leverage an LLM for execution decisions."
            )
        ]
        
        # Add additional capabilities if MCP connector is provided
        if mcp_connector:
            self.capabilities.append(
                AgentCapability(
                    name="mcp_tool_invoke",
                    description="Ability to use external tools via MCP."
                )
            )
            
            # Placeholder for code execution capability
            # In a real system, this would require careful security considerations
            self.capabilities.append(
                AgentCapability(
                    name="code_execution",
                    description="Ability to execute code (PLACEHOLDER - not actually implemented).",
                    parameters_schema={
                        "code": {
                            "type": "string",
                            "description": "The code to execute."
                        },
                        "language": {
                            "type": "string",
                            "description": "The programming language of the code.",
                            "enum": ["python", "javascript"]
                        }
                    }
                )
            )
    
    def process_message(self, message: Message) -> Optional[Message]:
        """
        Process an incoming message by executing the specified task.
        
        Args:
            message: The incoming Message object to process.
            
        Returns:
            A Message object containing the execution result.
        """
        # Add the message to conversation history
        self.state.add_message(message)
        
        # Parse the message based on content_type and role
        try:
            parsed_message = MessageHandler.handle_by_role(message)
            logger.debug(f"Parsed message: {parsed_message}")
        except ValueError as e:
            logger.error(f"Error parsing message: {e}")
            return Message(
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                content=f"Error processing your message: {str(e)}",
                content_type="text/plain",
                role="assistant"
            )
        
        # Extract task information from the message
        task_content = parsed_message["content"]
        
        # Determine the type of execution needed based on the message
        if (message.content_type == "application/json" and 
            isinstance(message.content, dict) and 
            "tool_name" in message.content):
            # This appears to be a tool call request
            result = self._execute_tool_call(message.content)
        elif "code" in task_content.lower() and "execute" in task_content.lower():
            # This appears to be a code execution request
            result = self._execute_code_placeholder(task_content)
        else:
            # For other types of tasks, use LLM to determine best approach
            # and generate a response about the execution
            result = self._execute_general_task(task_content)
        
        # Return the execution result
        return Message(
            sender_id=self.agent_id,
            recipient_id=message.sender_id,
            content=result,
            content_type="text/plain",
            role="assistant"
        )
    
    def get_capabilities(self) -> List[AgentCapability]:
        """
        Get the list of capabilities this agent provides.
        
        Returns:
            A list of AgentCapability objects.
        """
        return self.capabilities
    
    def get_identity(self) -> AgentIdentity:
        """
        Get the identity of this agent.
        
        Returns:
            An AgentIdentity object.
        """
        return AgentIdentity(
            id=self.agent_id,
            name=self.agent_name,
            provider_info="Nexus Framework",
            version="1.0.0"
        )
    
    def _execute_tool_call(self, tool_request: Dict[str, Any]) -> str:
        """
        Execute a tool using the MCP connector.
        
        Args:
            tool_request: Dictionary containing tool_name and parameters.
            
        Returns:
            String representation of the tool execution result.
        """
        if not self.mcp_connector:
            return "Cannot execute tool call: No MCP connector available."
        
        tool_name = tool_request.get("tool_name")
        parameters = tool_request.get("parameters", {})
        
        try:
            logger.info(f"Executing tool: {tool_name} with parameters: {parameters}")
            result = self.mcp_connector.invoke_tool(tool_name, parameters)
            
            # Format the result as a string
            if isinstance(result, (dict, list)):
                return json.dumps(result, indent=2)
            else:
                return str(result)
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            return f"Error executing tool {tool_name}: {str(e)}"
    
    def _execute_code_placeholder(self, task_description: str) -> str:
        """
        Placeholder for code execution capability.
        
        Args:
            task_description: Description of the code execution task.
            
        Returns:
            A message explaining that code execution is not actually implemented.
        """
        logger.info(f"Received code execution request: {task_description}")
        
        return (
            "Code execution placeholder: In a production system, this would safely "
            "execute code in a sandboxed environment. For security reasons, this capability "
            "is not actually implemented in this demonstration version of the framework.\n\n"
            "Task description: " + task_description
        )
    
    def _execute_general_task(self, task_description: str) -> str:
        """
        Execute a general task using LLM reasoning.
        
        Args:
            task_description: Description of the task to execute.
            
        Returns:
            The result of the task execution.
        """
        # TODO: Replace this placeholder with actual LLM-based task execution
        # This is where we would call the LLM API to determine how to execute the task
        
        logger.info(f"Executing general task: {task_description}")
        
        # This is a placeholder that simply acknowledges the task
        # In a real implementation, this would use the LLM to determine
        # the best approach to execute the task and then do so
        
        return (
            f"I have executed the task: \"{task_description}\"\n\n"
            "Execution complete. In a full implementation, this would include "
            "detailed information about the execution steps and results."
        )
