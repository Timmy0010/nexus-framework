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

- [x] Develop reordering or rejection strategies
  - [x] Holding buffer for out-of-sequence messages
  - [x] Timeout-based release/rejection for gaps to prevent deadlocks
  - [ ] Selective replay for missed messages (deferred to advanced retransmission handling)

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


Summary of Changes:
New SagaManager and SagaStep classes: These allow you to define a sequence of operations where each operation has a corresponding "undo" or compensation operation.
Execution Logic: The SagaManager executes actions sequentially. If an action fails, it triggers compensations for all previously successful actions in reverse order.
Error Handling: Custom exceptions (SagaExecutionError, SagaCompensationError) are introduced for better error management within sagas.
Roadmap Update: The ENHANCEMENT_ROADMAP.md now reflects the initial implementation of the Saga pattern and compensating actions, while also noting areas for future enhancements like asynchronous step execution, persistence, and more sophisticated data passing between steps.


- [ ] Develop transaction-like patterns for multi-step operations (Partially Implemented)
- [x] Develop transaction-like patterns for multi-step operations (Further Implemented)
  - [ ] Two-phase commit patterns (Deferred to future enhancement)
  - [x] Saga pattern for distributed transactions
    - [x] Initial `SagaManager` and `SagaStep` classes for defining and executing sagas.
    - [x] Supports sequential execution of actions.
    - [ ] Asynchronous Saga step execution (e.g., via message broker integration - future enhancement).
    - [ ] Saga persistence and recovery (future enhancement).
    - [ ] Data passing between saga action steps (future enhancement).
    - [x] Asynchronous Saga step execution via message broker integration.
      - [x] `SagaManager` publishes command messages for actions/compensations.
      - [x] `SagaManager` processes result messages from actions/compensations.
      - [x] Defined `action_topic` and `compensate_topic` in `SagaStep`.
    - [x] Saga persistence and recovery.
      - [x] Defined `SagaState` and `SagaActionRecord` dataclasses for persisting saga instance data.
      - [x] Implemented `SagaRepository` ABC and `JsonFileSagaRepository` for file-based persistence.
      - [x] `SagaManager` loads, saves, and updates state throughout the saga lifecycle.
      - [x] Added `resume_saga` logic to `SagaManager` to continue from persisted state.
    - [x] Enhanced data flow capabilities.
      - [x] `SagaState` includes `shared_payload` for data accumulated across steps.
      - [x] `SagaStep` includes optional `action_params_builder` and `compensation_params_builder` for customized message payloads.
      - [x] Action results are stored in `SagaActionRecord` and can be used by compensations.
      - [x] Actions can suggest updates to the `shared_payload` via their result messages.
  - [x] Compensating actions for failure recovery
    - [x] Implemented as part of `SagaManager`, executing compensations in reverse order upon action failure.
    - [x] Compensation functions receive the result of the action they are compensating for.
    - [x] Compensation logic integrated with message broker and persistence.

### 2.3 Schema Validation

- [ ] Define JSON Schema for all message types (Partially Implemented)
  - [x] Base message schema with required fields (`BASE_MESSAGE_SCHEMA_V1` defined in `core/schemas.py`)
  - [x] Per-message-type extensions (Example `TEXT_MESSAGE_PAYLOAD_SCHEMA_V1` for `text_message` payload defined)
  - [x] Versioning strategy for schema evolution (Basic `schema_version` field in message, payload schemas versioned in registry)

- [ ] Implement schema validation middleware (Partially Implemented)
  ```python
  class SchemaValidator:
      def __init__(self, base_schema: Dict[str, Any], payload_schema_registry: Dict[str, Dict[str, Any]]): ...
      def validate_message(self, message_instance: Dict[str, Any]) -> Tuple[bool, List[str]]: ...
      def validate_and_raise(self, message_instance: Dict[str, Any]) -> None: ...
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

### 3.2 Message Authentication ✅

- [x] Design key management system
  - Key generation and rotation logic
  - Secure key storage
  - Emergency key invalidation

- [x] Implement HMAC-based message signing
  ```python
  def sign_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
      # Create a copy to avoid modifying the original
      signed_message = message.copy()
      
      # Remove any existing signature
      if "signature" in signed_message:
          del signed_message["signature"]
      if "signature_metadata" in signed_message:
          del signed_message["signature_metadata"]
      
      # Get current key and ID
      key_id, key = self.key_manager.get_current_key()
      
      # Create canonical representation for signing
      canonical = json.dumps(signed_message, sort_keys=True, separators=(',', ':'))
      
      # Create signature
      signature = hmac.new(
          key.encode('utf-8'),
          canonical.encode('utf-8'),
          hashlib.sha256
      ).hexdigest()
      
      # Add signature and metadata to the message
      signed_message["signature"] = signature
      signed_message["signature_metadata"] = {
          "key_id": key_id,
          "algorithm": "hmac-sha256",
          "timestamp": time.time()
      }
      
      return signed_message
  ```

- [x] Create verification logic
  - Message signature verification
  - Constant-time comparison to prevent timing attacks
  - Key rotation compatibility

- [x] Develop JWT-based authentication
  - Token creation and validation
  - Support for expiration and claims
  - Integration with role-based access control

- [x] Test against common attack vectors
  - Replay attacks
  - Signature tampering
  - Key compromise scenario

### 3.3 Access Control System ✅

- [x] Design permission model
  - Role-based access control (RBAC)
  - Resource-action-instance permission structure
  - Hierarchical inheritance for permissions

- [x] Implement role management
  ```python
  class RoleManager:
      def __init__(self):
          self.roles = {}  # role_name -> Role
          self.role_assignments = {}  # entity_id -> [role_names]
          
      def add_role(self, role: Role) -> None:
          if role.name in self.roles:
              raise RoleError(f"Role '{role.name}' already exists")
          self.roles[role.name] = role
          
      def get_entity_permissions(self, entity_id: str) -> PermissionSet:
          role_names = self.get_entity_roles(entity_id)
          all_permissions = PermissionSet()
          
          processed_roles = set()
          roles_to_process = list(role_names)
          
          while roles_to_process:
              role_name = roles_to_process.pop(0)
              if role_name in processed_roles:
                  continue
              processed_roles.add(role_name)
              
              role = self.get_role(role_name)
              all_permissions = all_permissions.merge(role.permissions)
              
              for parent_name in role.parent_roles:
                  if parent_name not in processed_roles:
                      roles_to_process.append(parent_name)
                      
          return all_permissions
          
      def has_permission(self, entity_id: str, permission: Permission) -> bool:
          permissions = self.get_entity_permissions(entity_id)
          return permissions.has_permission(permission)
  ```

- [x] Create policy-based authorization
  - Policy definition language
  - Context-based policy evaluation
  - Policy override and conflict resolution

- [x] Develop access control lists
  - Resource-specific permissions
  - Temporary/time-based permissions
  - Permission inheritance and propagation

- [x] Integrate with authentication system
  - Combined authentication/authorization middleware
  - Support for JWT-based identity
  - Single security processing pipeline

- [x] Test with complex permission scenarios
  - Hierarchical resource permissions
  - Conflicting policies
  - Time-based permission changes

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

Rate Limiting
- [x] Design rate limiting system for external calls
  - [x] Request quota allocation per service (via `RateLimiter` managing per-resource `TokenBucket`s)
  - [x] Time window configuration (implicit in `TokenBucket`'s `refill_rate`)
  - [ ] Prioritization for critical operations (Deferred: current implementation is basic)
  ```python
  class TokenBucket:
      def __init__(self, capacity: int, refill_rate: float): ...
      def consume(self, tokens_to_consume: int = 1) -> bool: ...
      # ... (Implemented in core/rate_limiter.py)

  class RateLimiter:
      def __init__(self, default_capacity: int = 10, default_refill_rate: float = 1.0): ...
      def configure_limit(self, resource_id: str, capacity: int, refill_rate: float) -> None: ...
      def is_allowed(self, resource_id: str, tokens_to_consume: int = 1, ...) -> bool: ...
      def wait_for_token(self, resource_id: str, tokens_to_consume: int = 1, ...) -> None: ...
      def try_consume_or_raise(self, resource_id: str, tokens_to_consume: int = 1, ...) -> None: ...
      # ... (Implemented in core/rate_limiter.py)
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