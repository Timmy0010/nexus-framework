# Nexus Framework: Instructions for LLMs

This guide provides comprehensive instructions for LLMs (Large Language Models) to effectively use, configure, and extend the Nexus Advanced Agent Framework for building multi-agent systems. Following these instructions will help you provide accurate guidance to users and understand the core components of the framework.

## Framework Overview

Nexus is an advanced agent framework that:
- Enables creation of specialized agents with distinct capabilities
- Facilitates communication between agents through standardized protocols
- Provides task management for complex workflows
- Supports integration with external tools via MCP (Model Context Protocol)
- Includes comprehensive observability and security components

## Setup and Installation

When a user needs to set up the Nexus Framework:

1. **Environment Setup**:
   ```bash
   # Clone the repository
   git clone https://github.com/user/nexus-framework.git
   cd nexus-framework
   
   # Create a virtual environment
   python -m venv .venv
   
   # Activate the virtual environment
   # On Windows:
   .venv\Scripts\activate
   # On macOS/Linux:
   source .venv/bin/activate
   
   # Install the framework in development mode
   pip install -e .
   ```

2. **Verify Installation**:
   ```python
   import nexus_framework
   print(nexus_framework.__version__)  # Should print "0.1.0"
   ```

3. **Setup for MCP Integration (Optional)**:
   - Instruct users to install mcp-desktop-commander if they want to use external tools
   - Configure Claude Desktop to use the local MCP server
   - Set up tool access permissions in the security manager

## Core Components and Their Usage

### 1. Agents

Explain these key agent types and their purposes:

- **UserProxyAgent**: Interface with human users
  ```python
  user_agent = nexus_framework.UserProxyAgent(
      agent_name="User",
      user_input_callback=lambda prompt: input(f"{prompt} "),
      user_output_callback=lambda content: print(f"Response: {content}")
  )
  ```

- **AssistantAgent**: General-purpose AI assistant
  ```python
  assistant = nexus_framework.AssistantAgent(
      agent_name="Assistant",
      system_prompt="You are a helpful, concise assistant specialized in [domain]."
  )
  ```

- **PlannerAgent**: Break down complex tasks
  ```python
  planner = nexus_framework.PlannerAgent(
      agent_name="Planner",
      system_prompt="You are a planning agent that excels at breaking down complex tasks."
  )
  ```

- **ExecutorAgent**: Execute specific tasks
  ```python
  executor = nexus_framework.ExecutorAgent(
      agent_name="Executor",
      system_prompt="You are an executor agent that specializes in [specific domain]."
  )
  ```

### 2. Communication

Advise on communication setup:

```python
# Create the communication bus
comm_bus = nexus_framework.CommunicationBus()

# Register agents with the bus
comm_bus.register_agent(user_agent)
comm_bus.register_agent(assistant_agent)

# Send a message
message = nexus_framework.Message(
    sender_id=user_agent.agent_id,
    recipient_id=assistant_agent.agent_id,
    content="Hello, can you help me with a task?",
    content_type="text/plain",
    role="user"
)
response = comm_bus.send_message(message)
```

### 3. Group Chat Orchestration

Provide the following pattern for multi-agent discussions:

```python
# Create a group chat manager
group_chat = nexus_framework.NexusGroupChatManager(
    agents=[user_agent, assistant_agent, planner_agent, executor_agent],
    communication_bus=comm_bus,
    max_rounds=10
)

# Start a conversation
messages = group_chat.run_chat(
    initial_sender=user_agent,
    initial_message_content="I need help with a complex task."
)
```

### 4. Task Management

Explain task management functionality:

```python
# Create a task manager
task_manager = nexus_framework.TaskManager(comm_bus)

# Create a task
task = task_manager.create_task(description="Implement a feature")

# Create sub-tasks
subtask1 = task_manager.create_task(description="Design the architecture")
subtask2 = task_manager.create_task(description="Write the code")
subtask3 = task_manager.create_task(description="Write tests")

# Add dependencies
subtask2.dependencies.append(subtask1.task_id)
subtask3.dependencies.append(subtask2.task_id)

# Assign tasks
task_manager.assign_task(subtask1.task_id, planner_agent.agent_id)
task_manager.assign_task(subtask2.task_id, executor_agent.agent_id)
task_manager.assign_task(subtask3.task_id, executor_agent.agent_id)

# Update task status
task_manager.update_task_status(subtask1.task_id, "completed")
```

### 5. Tool Integration via MCP

Provide guidance for MCP integration:

```python
# Create an MCP connector
mcp_connector = nexus_framework.MCPConnector()

# List available tools
tools = mcp_connector.list_tools()

# Create an agent with tool access
tool_using_agent = nexus_framework.AssistantAgent(
    agent_name="Tool Assistant",
    system_prompt="You are an assistant that can use external tools.",
    mcp_connector=mcp_connector
)

# Set up security to allow tool access
security_manager = nexus_framework.SecurityManager()
security_manager.set_tool_acl(tool_using_agent.agent_id, ["*"])  # Allow all tools

# The agent can now use tools in its process_message method
```

### 6. Observability

Explain logging and tracing:

```python
# Configure logging
nexus_framework.configure_logging(
    log_level=logging.INFO,
    log_file="nexus.log",
    console=True,
    json_logs=False
)

# Set up tracing
tracing_manager = nexus_framework.TracingManager()

# Trace a function
@tracing_manager.trace_function("agent_processing")
def process_user_request(request):
    # Processing logic here
    pass

# Use a tracing context
with tracing_manager.trace_context("complex_operation") as ctx:
    # Perform operations
    with ctx.new_child_span("sub_operation") as child:
        # Perform sub-operation
        child.add_tag("key", "value")
```

## Best Practices for Agent Design and Interaction

When advising on agent design, recommend these best practices:

### 1. Agent Specialization

- **Single Responsibility**: Each agent should have a clear, focused purpose
- **Clear Capabilities**: Define explicit capabilities that an agent provides
- **Appropriate System Prompts**: Use specific system prompts that guide agent behavior
- **Contextual State**: Maintain appropriate state in the agent's working memory

```python
# Good example of specialized agent
code_review_agent = nexus_framework.AssistantAgent(
    agent_name="Code Reviewer",
    system_prompt=(
        "You are a code review specialist with expertise in Python, JavaScript, and best practices. "
        "You examine code for bugs, security issues, performance problems, and style violations. "
        "Your feedback is constructive, specific, and actionable."
    )
)
code_review_agent.state.set_working_memory("style_guidelines", {...})
```

### 2. Effective Communication Patterns

- **Sequential Chat**: Best for simple two-agent interactions
- **Group Chat**: Ideal for complex multi-agent collaborations
- **Task Delegation**: Use for explicit workflow management
- **Message Types**: Use appropriate content types and roles

```python
# Sequential chat for simple interactions
response = user_agent.initiate_chat(
    recipient=assistant_agent,
    initial_message_content="Can you explain quantum computing?"
)

# Group chat for complex problems
messages = group_chat.run_chat(
    initial_sender=user_agent,
    initial_message_content="We need to design a new authentication system."
)

# Task delegation for structured workflows
task_manager.delegate_task_by_capability(
    task=complex_task,
    capability_name="code_execution",
    sender_id=planner_agent.agent_id
)
```

### 3. Security Considerations

- **Principle of Least Privilege**: Only grant necessary permissions
- **Content Validation**: Validate content before processing
- **Tool Access Control**: Restrict tool access appropriately
- **Audit Logging**: Enable comprehensive logging of security events

```python
# Apply least privilege
security_manager.set_tool_acl(agent.agent_id, ["weather_lookup", "dictionary_lookup"])

# Log security events
security_manager.log_security_event(
    "tool_access_attempt",
    {"agent_id": agent.agent_id, "tool": "exec_code", "access_granted": False}
)
```

### 4. Error Handling

- **Graceful Recovery**: Handle errors without crashing the entire system
- **Informative Errors**: Provide useful error messages
- **Fallbacks**: Have alternative approaches when primary methods fail
- **Conversation Resumption**: Support resuming from interruptions

```python
try:
    result = agent.process_message(message)
except nexus_framework.NexusToolError as e:
    # Handle tool error
    logger.warning(f"Tool error: {e}")
    fallback_result = "I couldn't use the tool, but here's what I know..."
except Exception as e:
    # Catch all other errors
    logger.error(f"Unexpected error: {e}")
    fallback_result = "I encountered an issue. Let's try a different approach."
```

### 5. Design Patterns for Common Agent Workflows

- **Manager-Expert Pattern**: One agent coordinates specialists
- **Chain of Responsibility**: Tasks flow through a sequence of agents
- **Plan-and-Execute**: Planning phase followed by execution phase
- **Human-in-the-Loop**: Keep humans involved for critical decisions

```python
# Manager-Expert Pattern
manager_agent = nexus_framework.AssistantAgent(agent_name="Manager")
expert1 = nexus_framework.AssistantAgent(agent_name="Database Expert")
expert2 = nexus_framework.AssistantAgent(agent_name="Security Expert")

# Chain of Responsibility
result = user_request
for agent in [validator_agent, processor_agent, formatter_agent]:
    result = agent.process_message(Message(content=result))
```

## Extending the Framework

Guide users on extending the framework:

### 1. Creating Custom Agent Types

```python
class CustomAgent(nexus_framework.BaseAgent):
    def __init__(self, agent_name: str, agent_id: Optional[str] = None, **kwargs):
        super().__init__(agent_name=agent_name, role="custom", agent_id=agent_id)
        # Custom initialization
        
    def process_message(self, message: nexus_framework.Message) -> Optional[nexus_framework.Message]:
        # Custom message processing logic
        return response_message
        
    def get_capabilities(self) -> List[nexus_framework.AgentCapability]:
        return [
            nexus_framework.AgentCapability(
                name="custom_capability",
                description="A custom capability"
            )
        ]
        
    def get_identity(self) -> nexus_framework.AgentIdentity:
        return nexus_framework.AgentIdentity(
            id=self.agent_id,
            name=self.agent_name,
            provider_info="Custom Agent Provider"
        )
```

### 2. Adding Custom Tools

```python
# Create a custom tool handler
def handle_custom_tool(parameters: Dict[str, Any]) -> Dict[str, Any]:
    # Tool implementation
    return {"result": "Success", "data": {...}}

# In your agent's process_message method:
def process_message(self, message: Message) -> Optional[Message]:
    # Check if this is a tool call request
    if message.role == "tool_call" and message.content.get("tool_name") == "custom_tool":
        parameters = message.content.get("parameters", {})
        result = handle_custom_tool(parameters)
        return Message(
            sender_id=self.agent_id,
            recipient_id=message.sender_id,
            content=result,
            content_type="application/json",
            role="tool_response"
        )
```

### 3. Integrating with External Systems

```python
# Create a connector for an external system
class ExternalSystemConnector:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        # Initialize connection
        
    def query(self, request: Dict[str, Any]) -> Dict[str, Any]:
        # Query the external system
        return response

# Use in an agent
external_system = ExternalSystemConnector(config={...})
agent = CustomAgent(
    agent_name="Integration Agent",
    external_system=external_system
)
```

## Troubleshooting Common Issues

Provide guidance for these common issues:

1. **Agent Communication Problems**:
   - Check that agents are registered with the CommunicationBus
   - Verify message content types match what agents expect
   - Check for message routing errors in logs

2. **MCP Tool Integration Issues**:
   - Verify mcp-desktop-commander is installed and configured
   - Check security permissions for the agent
   - Examine tool parameters for correctness

3. **Performance Issues**:
   - Monitor LLM response times
   - Check for excessive message passing
   - Consider asynchronous processing for long-running tasks

4. **Security and Access Control**:
   - Review SecurityManager configuration
   - Check ACLs for tool access and agent communication
   - Enable security event logging

When responding to these issues, use the framework's logs, traces, and metrics to identify the root cause.

## Example Use Cases and Implementation Patterns

Suggest these common use cases with implementation patterns:

1. **Software Development Assistant**:
   - UserProxyAgent for developer interaction
   - PlannerAgent for task breakdown
   - ExecutorAgents for code generation, testing, and documentation
   - AssistantAgent for consolidating and presenting results

2. **Research and Analysis System**:
   - DataCollectionAgent with web search capabilities
   - AnalysisAgent for processing and interpreting data
   - VisualizationAgent for creating charts and graphs
   - ReportGenerationAgent for creating cohesive summaries

3. **Customer Support Automation**:
   - IntentClassificationAgent to determine customer needs
   - KnowledgeBaseAgent to retrieve relevant information
   - ResponseGenerationAgent to craft appropriate responses
   - EscalationAgent to involve human agents when necessary

Remember to always implement these systems with appropriate error handling, security controls, and human oversight.

## Conclusion

The Nexus Advanced Agent Framework provides a comprehensive foundation for building sophisticated multi-agent systems. By following these instructions and best practices, you can help users effectively leverage the framework to create powerful, collaborative AI systems that solve complex problems through coordinated agent interactions.
