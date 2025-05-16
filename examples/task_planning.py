"""
Example of task planning and execution in the Nexus framework.

This script demonstrates how to use the PlannerAgent, TaskManager, and
ExecutorAgent to handle complex tasks through decomposition and delegation.
"""

import logging
import sys
import os
import time

# Add the parent directory to the Python path so we can import the framework
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from nexus_framework import (
    configure_logging,
    UserProxyAgent,
    AssistantAgent,
    PlannerAgent,
    ExecutorAgent,
    CommunicationBus,
    TaskManager,
    Task,
    Message,
    TracingManager
)


def main():
    """Run a demonstration of task planning and execution."""
    # Configure logging
    configure_logging(log_level=logging.INFO, console=True)
    
    # Create tracing manager for better observability
    tracing_manager = TracingManager()
    
    print("Nexus Framework Task Planning and Execution Example")
    print("==================================================")
    print()
    
    # Start a new trace for the entire process
    with tracing_manager.trace_context("task_planning_demo") as trace_ctx:
        # Create a communication bus
        with trace_ctx.new_child_span("create_communication_bus") as span:
            comm_bus = CommunicationBus()
            span.add_tag("component", "CommunicationBus")
        
        # Create a task manager
        with trace_ctx.new_child_span("create_task_manager") as span:
            task_manager = TaskManager(comm_bus)
            span.add_tag("component", "TaskManager")
        
        # Create the agents
        with trace_ctx.new_child_span("create_agents") as span:
            # User proxy agent for interaction
            user_agent = UserProxyAgent(
                agent_name="User",
                user_input_callback=lambda prompt: input(f"{prompt} "),
                user_output_callback=lambda content: print(f"Response: {content}")
            )
            
            # Planner agent for task decomposition
            planner_agent = PlannerAgent(
                agent_name="Planner",
                system_prompt=(
                    "You are a planning agent that specializes in breaking down complex tasks into manageable steps. "
                    "When given a task, analyze it carefully and create a plan with clear, sequential sub-tasks."
                )
            )
            
            # Executor agents for different types of tasks
            code_executor = ExecutorAgent(
                agent_name="CodeExecutor",
                system_prompt="You are an executor agent specialized in code-related tasks."
            )
            
            research_executor = ExecutorAgent(
                agent_name="ResearchExecutor",
                system_prompt="You are an executor agent specialized in research and information gathering tasks."
            )
            
            writing_executor = ExecutorAgent(
                agent_name="WritingExecutor",
                system_prompt="You are an executor agent specialized in content creation and writing tasks."
            )
            
            # Assistant agent for providing final responses
            assistant_agent = AssistantAgent(
                agent_name="Assistant",
                system_prompt=(
                    "You are a helpful assistant that coordinates the work of other agents. "
                    "You review their outputs and provide a consolidated, coherent response to the user."
                )
            )
            
            # Register all agents with the communication bus
            for agent in [user_agent, planner_agent, code_executor, 
                         research_executor, writing_executor, assistant_agent]:
                comm_bus.register_agent(agent)
                span.add_event(f"registered_agent", {"agent_name": agent.agent_name})
        
        # Define a mapping of task types to appropriate executor agents
        task_type_mapping = {
            "code": code_executor.agent_id,
            "research": research_executor.agent_id,
            "writing": writing_executor.agent_id
        }
        
        print("Agents created and registered. Starting task planning demo.")
        print("Enter a complex task that requires multiple steps to complete.")
        print("Example: \"Create a Python script to analyze weather data and generate a report.\"")
        
        # Get the task from the user
        user_task = input("\nYour task: ")
        
        # Create the main task
        with trace_ctx.new_child_span("create_main_task") as span:
            main_task = task_manager.create_task(description=user_task)
            span.add_tag("task_id", main_task.task_id)
            span.add_tag("task_description", main_task.description)
        
        # Send the task to the planner agent for decomposition
        with trace_ctx.new_child_span("planning_phase") as span:
            print("\nSubmitting task to the Planner Agent for decomposition...")
            
            planning_message = Message(
                sender_id=user_agent.agent_id,
                recipient_id=planner_agent.agent_id,
                content=main_task.description,
                content_type="text/plain",
                role="user",
                metadata={"task_id": main_task.task_id}
            )
            
            # Get the plan from the planner agent
            span.add_event("sending_to_planner")
            plan_response = comm_bus.send_message(planning_message)
            span.add_event("received_plan")
            
            if plan_response:
                print(f"\nPlanner Agent response:\n{plan_response.content}")
                
                # Parse the plan to extract sub-tasks
                # This is a simplified implementation that expects a specific format
                plan_lines = plan_response.content.split("\n")
                sub_tasks = []
                
                for line in plan_lines:
                    # Look for numbered list items (e.g., "1. Task description")
                    import re
                    match = re.match(r"^\s*(\d+)\.\s+(.+)$", line)
                    if match:
                        task_num, task_desc = match.groups()
                        
                        # Determine the task type based on keywords
                        task_type = "writing"  # default
                        if any(kw in task_desc.lower() for kw in ["code", "script", "program", "function"]):
                            task_type = "code"
                        elif any(kw in task_desc.lower() for kw in ["research", "find", "search", "gather", "analyze"]):
                            task_type = "research"
                        
                        # Create a sub-task
                        sub_task = task_manager.create_task(description=task_desc)
                        sub_task.metadata = {"type": task_type}
                        sub_tasks.append(sub_task)
                        
                        # Add as a sub-task to the main task
                        main_task.add_sub_task(sub_task)
                
                print(f"\nExtracted {len(sub_tasks)} sub-tasks from the plan.")
                for i, task in enumerate(sub_tasks):
                    task_type = task.metadata.get("type", "unknown")
                    print(f"  {i+1}. [{task_type}] {task.description}")
            else:
                print("Error: No response from Planner Agent.")
                return
        
        # Distribute and execute the sub-tasks
        with trace_ctx.new_child_span("execution_phase") as span:
            print("\nDistributing sub-tasks to appropriate executor agents...")
            
            results = []
            
            for i, sub_task in enumerate(sub_tasks):
                task_type = sub_task.metadata.get("type", "unknown")
                executor_id = task_type_mapping.get(task_type)
                
                if not executor_id:
                    print(f"Warning: No executor available for task type '{task_type}'.")
                    continue
                
                # Find the executor agent
                executor = None
                for agent in [code_executor, research_executor, writing_executor]:
                    if agent.agent_id == executor_id:
                        executor = agent
                        break
                
                if not executor:
                    print(f"Error: Executor agent with ID {executor_id} not found.")
                    continue
                
                with trace_ctx.new_child_span(f"execute_subtask_{i}") as subtask_span:
                    subtask_span.add_tag("task_id", sub_task.task_id)
                    subtask_span.add_tag("task_type", task_type)
                    subtask_span.add_tag("executor", executor.agent_name)
                    
                    print(f"\nExecuting sub-task {i+1}: {sub_task.description}")
                    print(f"Assigned to: {executor.agent_name}")
                    
                    # Send the task to the executor
                    task_message = Message(
                        sender_id=assistant_agent.agent_id,
                        recipient_id=executor.agent_id,
                        content=sub_task.description,
                        content_type="text/plain",
                        role="assistant",
                        metadata={"task_id": sub_task.task_id}
                    )
                    
                    # Execute the task
                    subtask_span.add_event("sending_to_executor")
                    start_time = time.time()
                    
                    execution_response = comm_bus.send_message(task_message)
                    
                    execution_time = time.time() - start_time
                    subtask_span.add_event("received_response", {"execution_time": execution_time})
                    
                    if execution_response:
                        # Store the result
                        sub_task.set_result(execution_response.content)
                        results.append((sub_task, execution_response.content))
                        
                        # Update task status
                        task_manager.update_task_status(sub_task.task_id, "completed")
                        
                        # Show a snippet of the result
                        result_preview = execution_response.content
                        if len(result_preview) > 100:
                            result_preview = result_preview[:100] + "..."
                        
                        print(f"Result: {result_preview}")
                    else:
                        print(f"Error: No response from {executor.agent_name}.")
                        task_manager.update_task_status(sub_task.task_id, "failed")
                
                # Add a small delay to simulate realistic execution times
                time.sleep(0.5)
        
        # Send all results to the assistant for consolidation
        with trace_ctx.new_child_span("consolidation_phase") as span:
            print("\nAll sub-tasks completed. Sending results to Assistant for consolidation...")
            
            # Prepare a summary of all sub-task results
            summary = f"Summary of completed tasks for: {main_task.description}\n\n"
            
            for sub_task, result in results:
                summary += f"- {sub_task.description}:\n"
                summary += f"  {result[:200]}{'...' if len(result) > 200 else ''}\n\n"
            
            # Send to the assistant
            consolidation_message = Message(
                sender_id=user_agent.agent_id,
                recipient_id=assistant_agent.agent_id,
                content=summary,
                content_type="text/plain",
                role="user",
                metadata={"task_id": main_task.task_id}
            )
            
            span.add_event("sending_to_assistant")
            final_response = comm_bus.send_message(consolidation_message)
            span.add_event("received_final_response")
            
            if final_response:
                print("\nFinal consolidated response from the Assistant:")
                print("================================================")
                print(final_response.content)
                
                # Update main task status and result
                main_task.set_result(final_response.content)
                task_manager.update_task_status(main_task.task_id, "completed")
            else:
                print("Error: No final response from Assistant.")
        
        # Get trace summary
        trace_summary = tracing_manager.get_trace(trace_ctx.trace_id)
        
        # Display execution statistics
        print("\nTask Execution Summary:")
        print(f"Main Task: {main_task.description}")
        print(f"Sub-tasks: {len(sub_tasks)}")
        print(f"Completed sub-tasks: {len([t for t in sub_tasks if t.status == 'completed'])}")
        print(f"Failed sub-tasks: {len([t for t in sub_tasks if t.status == 'failed'])}")
        
        print("\nSpans created in trace:", len(trace_summary))
    
    print("\nThank you for trying the Nexus Framework Task Planning Example!")


if __name__ == "__main__":
    main()
