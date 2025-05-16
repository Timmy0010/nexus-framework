## Overview

This document outlines the planned enhancements for the Nexus Framework to transform it from a prototype to a production-ready agent orchestration system with enterprise-grade reliability features.

## Architecture Vision

The enhanced architecture focuses on:

1. **Reliability** - Ensuring message delivery even during system failures
2. **Scalability** - Supporting increased load and more complex agent interactions
3. **Observability** - Comprehensive visibility into system behavior
4. **Security** - Robust validation and permission checks throughout
5. **Extensibility** - Well-defined interfaces for future capabilities

## Phase 1: Reliable Message Infrastructure

### 1.1 Message Broker Integration ✅

- [x] Research and select appropriate message broker (RabbitMQ/Kafka)
  - RabbitMQ selected for its simplicity and excellent support for request/reply patterns
  
- [x] Design broker topology
  - **Exchanges/Topics**: `nexus.agents`, `nexus.commands`, `nexus.events`, `nexus.tools`
  - **Queues**: Per-agent queues, shared command queues, tool-specific queues
  - **Routing Keys**: Agent IDs, tool types, command categories

- [x] Implement `MessageBroker` adapter interface
  ```python
  class MessageBroker(ABC):
      @abstractmethod
      def initialize(self, config: Dict[str, Any]) -> bool: ...
      
      @abstractmethod
      def publish(self, topic: str, message: Dict[str, Any], 
                  headers: Optional[Dict[str, Any]] = None) -> str: ...
      
      @abstractmethod
      def subscribe(self, topic: str, callback: Callable, 
                   queue_name: Optional[str] = None) -> str: ...
      
      @abstractmethod
      def acknowledge(self, message_id: str) -> bool: ...
      
      @abstractmethod
      def negative_acknowledge(self, message_id: str, reason: str) -> bool: ...
  ```

- [x] Create RabbitMQ implementation
  - Used `pika` library with reconnection handling
  - Implemented circuit breaker pattern for graceful degradation

- [x] Develop broker health monitoring and reconnection logic
  - Created health check methods
  - Implemented connection monitoring and automatic reconnection
  - Added exponential backoff for reconnection attempts

### 1.2 Persistent Message Queues ✅

- [x] Define durable queue configuration
  - Queue persistence settings: `durable=True`
  - Message persistence: `delivery_mode=2`
  - Message TTL strategies for different message types
  
- [x] Implement message persistence layer
  - JSON serialization with standardized format
  - Proper error handling for serialization/deserialization
  - Support for binary content in future versions

- [x] Create queue management utilities
  - Methods for queue creation, binding, and inspection
  - Support for dead letter queues
  - Proper error handling for queue operations

- [x] Develop recovery procedures for broker restarts
  - Implemented connection monitoring
  - Added automatic reconnection with exponential backoff
  - Created resubscription logic for all active subscriptions

### 1.3 Acknowledgment System ✅

- [x] Design message acknowledgment protocol
  - Client and server-side acknowledgment patterns
  - Timeout handling for long-running operations
  - Support for both ACK and NACK with reason

- [x] Implement producer-side message tagging with UUIDs
  ```python
  def publish(topic: str, message: Dict[str, Any], headers: Optional[Dict] = None) -> str:
      message_id = str(uuid.uuid4())
      headers = headers or {}
      headers['message_id'] = message_id
      # ... publish logic ...
      return message_id
  ```

- [x] Create consumer-side ACK/NACK handlers
  ```python
  def on_message(ch, method, properties, body):
      try:
          # Process message
          broker.acknowledge(properties.message_id)
      except Exception as e:
          broker.negative_acknowledge(properties.message_id, str(e))
  ```

- [x] Develop retry logic for unacknowledged messages
  - RabbitMQ built-in redelivery for unacknowledged messages
  - Client-side tracking of delivery attempts
  - Circuit breaker integration to prevent retry storms

### 1.4 Dead Letter Handling ✅

- [x] Design dead-letter queue (DLQ) structure
  - Created central dead letter exchange: `dead_letter`
  - Added queue-specific routing keys for source tracking
  - Implemented metadata enrichment for error tracking

- [x] Implement routing logic for failed messages
  ```python
  # In RabbitMQ
  channel.queue_declare(
      queue='my_queue',
      arguments={
          'x-dead-letter-exchange': 'dead_letter',
          'x-dead-letter-routing-key': 'my_queue'
      }
  )
  ```

- [x] Create alerting system for DLQ entries
  - Added logging for failed message delivery
  - Created tracking for failure reasons

- [x] Implement basic dead letter queue management
  - Added methods for dead letter queue creation
  - Implemented message routing to dead letter queues
  - Created logging for dead letter activity

## Phase 2: Message Integrity & Processing Guarantees

### 2.1 Message Sequencing ✅

- [x] Design message sequence numbering scheme
  - Per-workflow sequence numbers
  - Tracking for processed sequences
  - Detection of missing sequences

- [x] Implement sequence tracking per conversation/workflow
  ```python
  class SequenceTracker:
      def __init__(self, workflow_id: str):
          self.workflow_id = workflow_id
          self.next_sequence = 0
          self.processed_sequences = set()
          
      def get_next_sequence(self) -> int:
          seq = self.next_sequence
          self.next_sequence += 1
          return seq
          
      def mark_processed(self, sequence: int) -> None:
          self.processed_sequences.add(sequence)
          
      def is_processed(self, sequence: int) -> bool:
          return sequence in self.processed_sequences
          
      def get_missing_sequences(self, up_to: int) -> List[int]:
          return [seq for seq in range(up_to) 
                 if seq not in self.processed_sequences]
  ```

- [x] Create detection logic for out-of-order messages
  - Sequence number tracking
  - Logging for missing sequences
  - Basic logging for sequence gaps

- [ ] Develop reordering or rejection strategies
  - Holding buffer for out-of-sequence messages
  - Timeout-based release to prevent deadlocks
  - Selective replay for missed messages

### 2.2 Idempotent Processing ✅

- [x] Design message deduplication system
  - In-memory cache with TTL for recent message IDs
  - Thread-safe implementation with locking
  - Automatic purging of expired entries

- [x] Implement efficient message ID tracking with TTL
  ```python
  class MessageDeduplicator:
      def __init__(self, ttl_seconds: int = 3600):
          self.seen_messages = {}  # message_id -> timestamp
          self.ttl_seconds = ttl_seconds
          
      def is_duplicate(self, message_id: str) -> bool:
          self._purge_expired()
          return message_id in self.seen_messages
          
      def mark_seen(self, message_id: str) -> None:
          self.seen_messages[message_id] = time.time()
          
      def _purge_expired(self) -> None:
          now = time.time()
          expired = [msg_id for msg_id, ts in self.seen_messages.items()
                   if now - ts > self.ttl_seconds]
          for msg_id in expired:
              del self.seen_messages[msg_id]
  ```

- [x] Create idempotent wrapper for agent processing methods
  - Added duplicate message detection in chat managers
  - Implemented unique message IDs for all communications
  - Added metadata for tracking processing state

- [ ] Develop transaction-like patterns for multi-step operations
  - Two-phase commit patterns
  - Saga pattern for distributed transactions
  - Compensating actions for failure recovery

### 2.3 Schema Validation

- [ ] Define JSON Schema for all message types
  - Base message schema with required fields
  - Per-message-type extensions
  - Versioning strategy for schema evolution

- [ ] Implement schema validation middleware
  ```python
  class SchemaValidator:
      def __init__(self, schema_registry: Dict[str, Dict]):
          self.schema_registry = schema_registry
          self.validators = {
              msg_type: jsonschema.validators.Draft7Validator(schema)
              for msg_type, schema in schema_registry.items()
          }
          
      def validate(self, message: Dict, message_type: str) -> List[str]:
          validator = self.validators.get(message_type)
          if not validator:
              return [f\"Unknown message type: {message_type}\"]
              
          errors = list(validator.iter_errors(message))
          return [str(error) for error in errors]
  ```

- [ ] Create error handling for invalid messages
  - Detailed error reporting with validation context
  - Partial validation for backward compatibility
  - Schema negotiation for version mismatches

- [ ] Develop schema version migration strategy
  - Schema registry with version tracking
  - Automatic upgrade path for older schemas
  - Deprecation warnings for sunset fields

## Phase 3: Enhanced Security & Verification

### 3.1 VerificationAgent Implementation

- [ ] Design `VerificationAgent` architecture
  - Pipeline-based processing model
  - Plugin system for verification modules
  - Configuration-driven rules engine

- [ ] Implement message inspection pipeline
  ```python
  class VerificationAgent(BaseAgent):
      def __init__(self, config: Dict[str, Any]):
          super().__init__(agent_name=\"VerificationAgent\", role=\"security\")
          self.validators = self._load_validators(config)
          self.sanitizers = self._load_sanitizers(config)
          
      def process_message(self, message: Message) -> Optional[Message]:
          # Validate message
          validation_results = self._validate(message)
          if not validation_results.is_valid:
              return self._create_rejection_message(
                  message, validation_results.errors)
                  
          # Sanitize message if valid
          sanitized_message = self._sanitize(message)
          
          # Forward to intended recipient
          return sanitized_message
  ```

- [ ] Create plugin system for verification rules
  - Rule definition interface
  - Rule loading and registration
  - Rule execution priority handling

- [ ] Develop rule configuration and management
  - YAML-based rule configuration
  - Dynamic rule reloading
  - Rule validation and testing framework

- [ ] Test verification with simulated attacks/invalid inputs
  - Malformed message structures
  - Oversized payloads
  - Malicious content patterns

### 3.2 Message Authentication

- [ ] Design message signing protocol
  - HMAC-based message signature generation
  - JWT for complex authorization scenarios
  - Key rotation strategy for security maintenance

- [ ] Implement HMAC or JWT generation and validation
  ```python
  def sign_message(message: Dict, secret_key: str) -> str:
      message_str = json.dumps(message, sort_keys=True)
      signature = hmac.new(
          secret_key.encode(),
          message_str.encode(),
          hashlib.sha256
      ).hexdigest()
      return signature
      
  def verify_signature(message: Dict, signature: str, secret_key: str) -> bool:
      expected = sign_message(message, secret_key)
      return hmac.compare_digest(signature, expected)
  ```

- [ ] Create key management for signature verification
  - Key storage with proper security practices
  - Access control for key usage
  - Key versioning for rotating credentials

- [ ] Develop signature rotation strategy
  - Periodic key rotation schedule
  - Overlapping validity periods for smooth transition
  - Emergency rotation procedures

- [ ] Test signature validation
  - Valid and invalid signatures
  - Expired credentials
  - Tampered message detection

### 3.3 Access Control System

- [ ] Design agent-to-agent authorization model
  - Role-based access control (RBAC)
  - Attribute-based access control (ABAC) for fine-grained permissions
  - Permission inheritance for agent hierarchies

- [ ] Implement ACL database and lookup
  ```python
  class AccessControl:
      def __init__(self, acl_config: Dict[str, Any]):
          self.acl_db = self._load_acl_rules(acl_config)
          
      def check_permission(self, 
                         source_agent_id: str, 
                         target_agent_id: str,
                         action: str) -> bool:
          # Check direct permission
          if self._has_direct_permission(source_agent_id, target_agent_id, action):
              return True
              
          # Check role-based permission
          agent_roles = self._get_agent_roles(source_agent_id)
          return any(self._has_role_permission(role, target_agent_id, action)
                   for role in agent_roles)
  ```

- [ ] Create permission hierarchy and inheritance
  - Group-based permission assignment
  - Role templates for common patterns
  - Wildcard permissions for administrative access

- [ ] Develop ACL administration utilities
  - Permission management UI
  - Audit logging for permission changes
  - Permission testing and validation tools

- [ ] Test permission enforcement
  - Authorized and unauthorized requests
  - Permission inheritance scenarios
  - Privilege escalation attempts

### 3.4 Message Sanitization

- [ ] Design content filtering rules
  - Whitelisted content patterns
  - Size limits for different message fields
  - Deep inspection for nested structures

- [ ] Implement sanitization for various content types
  ```python
  class MessageSanitizer:
      def __init__(self, config: Dict[str, Any]):
          self.max_sizes = config.get('max_sizes', {})
          self.allowed_patterns = config.get('allowed_patterns', {})
          
      def sanitize(self, message: Dict) -> Dict:
          result = {}
          for key, value in message.items():
              # Apply size limits
              if key in self.max_sizes and isinstance(value, str):
                  value = value[:self.max_sizes[key]]
                  
              # Apply pattern filtering
              if key in self.allowed_patterns and isinstance(value, str):
                  value = self._filter_by_pattern(value, self.allowed_patterns[key])
                  
              # Recurse for nested dictionaries
              if isinstance(value, dict):
                  value = self.sanitize(value)
                  
              result[key] = value
          return result
  ```

- [ ] Create size limit enforcement
  - Per-field size limits
  - Total message size constraints
  - Recursive depth limitations

- [ ] Develop logging for sanitization operations
  - Detailed logs of modifications made
  - Statistics gathering for common issues
  - Alerting for excessive sanitization needs

- [ ] Test with malicious payloads
  - XSS attack patterns
  - Command injection attempts
  - Oversized field attacks

## Phase 4: Resilient Operations

### 4.1 Circuit Breaker Implementation ✅

- [x] Design circuit breaker for external service calls
  - Three states: Closed, Open, Half-Open
  - Failure threshold configuration
  - Automatic recovery timing

- [x] Implement state tracking (closed/open/half-open)
  ```python
  class CircuitBreaker:
      def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 30):
          self.failure_threshold = failure_threshold
          self.recovery_timeout = recovery_timeout
          self.failure_count = 0
          self.state = 'CLOSED'
          self.last_failure_time = 0
          
      def execute(self, func, *args, **kwargs):
          if self.state == 'OPEN':
              if time.time() - self.last_failure_time > self.recovery_timeout:
                  self.state = 'HALF-OPEN'
              else:
                  raise CircuitOpenError(\"Circuit is open\")
                  
          try:
              result = func(*args, **kwargs)
              if self.state == 'HALF-OPEN':
                  self.reset()
              return result
          except Exception as e:
              self.record_failure()
              raise
              
      def record_failure(self):
          self.failure_count += 1
          self.last_failure_time = time.time()
          if self.failure_count >= self.failure_threshold:
              self.state = 'OPEN'
              
      def reset(self):
          self.failure_count = 0
          self.state = 'CLOSED'
  ```

- [x] Create circuit configuration system
  - Implemented within RabbitMQ broker
  - Automatic circuit triggering on connection failures
  - Controlled reconnection logic

- [x] Develop circuit reset and testing logic
  - Timeout-based circuit reopening
  - Exponential backoff for reconnection attempts
  - Health check integration

### 4.2 Advanced Retry Strategies ✅

- [x] Design configurable retry policies
  - Maximum retry attempts
  - Backoff strategy selection
  - Failure categorization (retriable vs. permanent)

- [x] Implement exponential backoff with jitter
  ```python
  def retry_with_backoff(func, max_retries=3, base_delay=1, max_delay=60):
      retries = 0
      while True:
          try:
              return func()
          except RetriableError as e:
              retries += 1
              if retries > max_retries:
                  raise
                  
              # Calculate delay with exponential backoff and jitter
              delay = min(max_delay, base_delay * (2 ** (retries - 1)))
              jitter = random.uniform(0, 0.1 * delay)
              time.sleep(delay + jitter)
  ```

- [x] Create retry limit and timeout management
  - Configurable connection attempts in broker initialization
  - Timeout handling for operations
  - Deadlock prevention through configurable timeouts

- [x] Develop reconnection strategies
  - Automatic reconnection for broker failures
  - Stateful reconnection with exponential backoff
  - Resubscription for all active subscriptions

### 4.3 Rate Limiting

- [ ] Design rate limiting system for external calls
  - Request quota allocation per service
  - Time window configuration (second/minute/hour)
  - Prioritization for critical operations

- [ ] Implement token bucket or leaky bucket algorithm
  ```python
  class TokenBucket:
      def __init__(self, capacity: int, refill_rate: float):
          self.capacity = capacity
          self.tokens = capacity
          self.refill_rate = refill_rate  # tokens per second
          self.last_refill = time.time()
          self.lock = threading.Lock()
          
      def consume(self, tokens: int = 1) -> bool:
          with self.lock:
              self._refill()
              if tokens <= self.tokens:
                  self.tokens -= tokens
                  return True
              return False
              
      def _refill(self):
          now = time.time()
          elapsed = now - self.last_refill
          new_tokens = elapsed * self.refill_rate
          
          if new_tokens > 0:
              self.tokens = min(self.capacity, self.tokens + new_tokens)
              self.last_refill = now
  ```

- [ ] Create dynamic rate adjustment based on responses
  - Response time monitoring
  - Error rate feedback
  - Adaptive rate limiting based on service health

- [ ] Develop rate limit monitoring
  - Usage metrics tracking
  - Threshold alerting
  - Trend analysis for capacity planning

- [ ] Test behavior under limit conditions
  - Burst request handling
  - Gradual limit approach
  - Priority override scenarios

## Phase 5: Observability & Monitoring

### 5.1 Distributed Tracing

- [ ] Integrate OpenTelemetry framework
  - Tracer initialization
  - Context propagation setup
  - Exporter configuration for tracing backend

- [ ] Implement trace context propagation in messages
  ```python
  def publish_with_tracing(broker, topic, message, headers=None):
      headers = headers or {}
      
      # Extract current span context
      span_context = trace.get_current_span().get_span_context()
      
      # Add trace context to headers
      headers['trace_id'] = format(span_context.trace_id, '032x')
      headers['span_id'] = format(span_context.span_id, '016x')
      headers['trace_flags'] = format(span_context.trace_flags, '02x')
      
      return broker.publish(topic, message, headers)
      
  def process_with_tracing(message, headers):
      # Extract trace context
      trace_id = int(headers.get('trace_id', '0'), 16)
      span_id = int(headers.get('span_id', '0'), 16)
      trace_flags = int(headers.get('trace_flags', '0'), 16)
      
      # Create span context
      span_context = trace.SpanContext(
          trace_id=trace_id,
          span_id=span_id,
          is_remote=True,
          trace_flags=trace.TraceFlags(trace_flags)
      )
      
      # Create new span using extracted context as parent
      with tracer.start_as_current_span(
          \"process_message\", context=trace.set_span_in_context(span_context)
      ):
          # Process message
          result = process_message(message)
          return result
  ```

- [ ] Create custom span attributes for agent operations
  - Agent type and ID attributes
  - Operation category and name
  - Business-relevant metadata

- [ ] Develop sampling strategy
  - Base sampling rate configuration
  - Priority-based sampling rules
  - Trace completion guarantees

- [ ] Test trace correlation through complex workflows
  - Multi-agent interaction traces
  - External service integration
  - Error path tracing

### 5.2 Structured Logging

- [ ] Design standardized log format
  - JSON-structured logging
  - Consistent field naming
  - Log level standardization

- [ ] Implement contextual logging with trace IDs
  ```python
  def get_contextual_logger():
      logger = logging.getLogger(__name__)
      
      # Add trace context
      span = trace.get_current_span()
      span_context = span.get_span_context()
      
      # Create a logger adapter with trace context
      context = {
          'trace_id': format(span_context.trace_id, '032x'),
          'span_id': format(span_context.span_id, '016x')
      }
      
      return logging.LoggerAdapter(logger, context)
      
  # Usage
  logger = get_contextual_logger()
  logger.info(\"Processing message\", extra={'message_id': msg.id})
  ```

- [ ] Create log level management
  - Dynamic log level configuration
  - Component-specific log levels
  - Temporary debug level boosting

- [ ] Develop log aggregation strategy
  - Centralized logging infrastructure
  - Log shipping configuration
  - Retention and rotation policies

- [ ] Test log correlation through complex workflows
  - End-to-end traceability validation
  - Error path logging verification
  - Log volume stress testing

### 5.3 Metrics Collection

- [ ] Design metrics for system health and performance
  - Throughput metrics (messages/second)
  - Latency metrics (processing time histograms)
  - Error rate metrics (failures/total)

- [ ] Implement counters, gauges, and histograms
  ```python
  # Initialize metrics
  message_counter = Counter('messages_processed_total', 
                           'Total messages processed', 
                           ['agent_type', 'status'])
                           
  queue_depth_gauge = Gauge('queue_depth',
                           'Current queue depth',
                           ['queue_name'])
                           
  processing_time = Histogram('message_processing_seconds',
                             'Time spent processing messages',
                             ['agent_type', 'message_type'])
                             
  # Usage
  def process_message(message):
      start_time = time.time()
      
      try:
          result = actual_processing(message)
          message_counter.labels(agent_type='assistant', status='success').inc()
          return result
      except Exception:
          message_counter.labels(agent_type='assistant', status='error').inc()
          raise
      finally:
          processing_time.labels(
              agent_type='assistant',
              message_type=message.get('type', 'unknown')
          ).observe(time.time() - start_time)
  ```

- [ ] Create dashboards for key metrics
  - System health overview
  - Performance analysis views
  - Error and alerting dashboards

- [ ] Develop alerting thresholds
  - Response time degradation alerts
  - Error rate spike detection
  - Resource utilization warnings

- [ ] Test metrics accuracy
  - Controlled load testing
  - Metric aggregation validation
  - Alert trigger verification

### 5.4 Health Checks ✅

- [x] Design health check endpoints
  - Method to check broker health
  - Status reporting for all components
  - Standardized health response format

- [x] Implement multi-level health reporting (surface/deep)
  ```python
  def health_check(self) -> Dict[str, Any]:
      """
      Check the health of the broker connection.
      
      Returns:
          Dictionary with health check results
      """
      result = {
          'status': 'healthy',
          'details': {
              'connection': 'connected' if self.connection and self.connection.is_open else 'disconnected',
              'channels': {},
              'subscriptions': len(self.subscriptions)
          }
      }
      
      # Check each channel
      for name, channel in self.channels.items():
          result['details']['channels'][name] = 'open' if channel.is_open else 'closed'
      
      # Set overall status
      if not self.connection or not self.connection.is_open:
          result['status'] = 'unhealthy'
          
      return result
  ```

- [x] Create cascading health status
  - Component-level health rollup
  - Status aggregation for overall system
  - Detailed reporting of unhealthy components

- [ ] Develop health status dashboard
  - Component health visualization
  - Historical uptime tracking
  - Incident correlation

- [x] Test health reporting under various conditions
  - Implemented component failure detection
  - Detailed status reporting
  - Added logging for health status changes

## Implementation Guidelines

### Coding Standards

- Follow PEP 8 and established project code style
- Document all new interfaces and changes to existing ones
- Write tests for all new functionality
- Use type annotations throughout

### Testing Strategy

- Unit tests for all components
- Integration tests for component interactions
- System tests for end-to-end workflows
- Performance tests for throughput and latency
- Chaos tests for resilience verification

### Dependency Management

- Minimize new external dependencies
- Evaluate license compatibility for all new packages
- Document version requirements
- Provide alternative implementations where possible

### Backward Compatibility

- Maintain API compatibility where possible
- Provide migration paths for breaking changes
- Version all APIs and schemas
- Support gradual adoption of new features

## Integration with Existing Components

### 1. Adapting Current Communication Bus ✅

The existing `CommunicationBus` class has been enhanced with a new reliable version that uses the message broker underneath. This approach ensures backward compatibility:

```python
class ReliableCommunicationBus:
    """
    Reliable message router for the Nexus framework.
    
    This implementation uses a message broker (RabbitMQ by default) to provide
    reliable message delivery with acknowledgments and dead letter handling.
    It maintains the same API as the base CommunicationBus for backward compatibility.
    """
    
    def __init__(self, broker: Optional[MessageBroker] = None, legacy_mode: bool = False):
        # Use provided broker or create default implementation
        self._broker = broker or self._create_default_broker()
        self._legacy_mode = legacy_mode
        
        # ...other initialization code...
```

### 2. Adapting the `NexusGroupChatManager` ✅

The existing `NexusGroupChatManager` has been enhanced with a reliable version that leverages the reliable messaging infrastructure:

```python
class ReliableNexusGroupChatManager(NexusGroupChatManager):
    """
    Enhanced group chat manager with reliable messaging support.
    
    This class extends the NexusGroupChatManager to add reliability features
    such as message sequencing, deduplication, and guaranteed delivery.
    """
    
    def __init__(
        self,
        agents: List[BaseAgent],
        communication_bus: ReliableCommunicationBus,
        messages: Optional[List[Message]] = None,
        max_rounds: int = 10,
        workflow_id: Optional[str] = None
    ):
        # Initialize parent class
        super().__init__(
            agents=agents,
            communication_bus=communication_bus,
            messages=messages,
            max_rounds=max_rounds
        )
        
        # Set workflow ID
        self.workflow_id = workflow_id or f"workflow_{str(uuid.uuid4())[:8]}"
        
        # Initialize sequence tracker
        self.sequence_tracker = SequenceTracker(self.workflow_id)
        
        # Initialize message deduplicator
        self.message_deduplicator = MessageDeduplicator(ttl_seconds=3600)
```

### 3. Verification Agent Integration

The `VerificationAgent` will be integrated into the message flow as follows:

```python
# In system initialization code:
def initialize_messaging_system(config):
    # Create broker
    broker = RabbitMQBroker()
    broker.initialize(config['broker'])
    
    # Create verification agent
    verification_agent = VerificationAgent(config['verification'])
    
    # Create communication bus with broker
    bus = ReliableCommunicationBus(broker=broker)
    
    # Register verification agent
    bus.register_agent(verification_agent)
    
    # Configure routing to ensure all messages pass through verification
    verification_topic = "nexus.verification"
    agent`
