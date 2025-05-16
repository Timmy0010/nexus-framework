import logging
import uuid
import time
import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Callable, Optional, Tuple

# Assuming MessageBroker interface from Phase 1 (Reliable Message Infrastructure)
# from nexus_framework.core.messaging import MessageBroker, RabbitMQBroker # Example import

# Placeholder for MessageBroker if not available in current context
class MessageBroker(ABC):
    @abstractmethod
    def publish(self, topic: str, message: Dict[str, Any], headers: Optional[Dict[str, Any]] = None) -> str: ...
    @abstractmethod
    def subscribe(self, topic: str, callback: Callable[[Dict[str, Any]], None], queue_name: Optional[str] = None) -> str: ...
    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> bool: ...


logger = logging.getLogger(__name__)

# --- Exceptions ---
class SagaError(Exception):
    """Base exception for Saga errors."""
    def __init__(self, message: str, saga_id: Optional[str] = None):
        super().__init__(message)
        self.saga_id = saga_id

class SagaExecutionError(SagaError):
    """Custom exception for errors during Saga execution's action phase."""
    def __init__(self, message: str, saga_id: str, failed_step_name: Optional[str] = None, original_exception: Optional[Exception] = None):
        super().__init__(message, saga_id)
        self.failed_step_name = failed_step_name
        self.original_exception = original_exception

class SagaCompensationError(SagaError):
    """Custom exception for errors during Saga compensation phase."""
    def __init__(self, message: str, saga_id: str, compensation_failures: Optional[List[Tuple[str, Exception]]] = None):
        super().__init__(message, saga_id)
        self.compensation_failures = compensation_failures or []

class SagaPersistenceError(SagaError):
    """Custom exception for errors related to saga state persistence."""
    pass

# --- Data Structures ---
@dataclass
class SagaStep:
    """
    Represents the definition of a single step in a saga.
    """
    name: str
    action_topic: str  # Topic to send command to execute action
    compensate_topic: str # Topic to send command to execute compensation
    # Callable: (current_shared_payload: Dict) -> action_specific_payload: Dict
    action_params_builder: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None
    # Callable: (action_result: Any, current_shared_payload: Dict) -> compensation_specific_payload: Dict
    compensation_params_builder: Optional[Callable[[Any, Dict[str, Any]], Dict[str, Any]]] = None

@dataclass
class SagaActionRecord:
    """
    Records the execution details of a saga action.
    """
    step_name: str
    action_payload: Dict[str, Any] # Payload sent to the action
    action_result: Optional[Any] = None # Result received from the action
    status: str = "PENDING"  # PENDING, COMPLETED, FAILED, COMPENSATING, COMPENSATED, COMPENSATION_FAILED_ATTEMPT
    # status can be: PENDING_ACTION, ACTION_COMPLETED, ACTION_FAILED,
    #                PENDING_COMPENSATION, COMPENSATION_COMPLETED, COMPENSATION_FAILED

@dataclass
class SagaState:
    """
    Holds the complete state of a saga instance.
    This object is what gets persisted.
    """
    saga_id: str
    definition_id: str # Identifier for the saga definition (e.g., "order_processing_saga")
    current_step_index: int # Index for the next action to execute
    current_compensating_step_index: int # Index in 'executed_actions' for current compensation
    status: str  # PREPARED, RUNNING, COMPENSATING, COMPLETED_SUCCESS, FAILED_ACTION, FAILED_COMPENSATION
    executed_actions: List[SagaActionRecord] # Records of executed actions and their results
    shared_payload: Dict[str, Any] # Data accumulated and passed through the saga
    correlation_id: Optional[str] = None # For tracking related messages
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def update_timestamp(self):
        self.updated_at = time.time()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SagaState':
        # Handle deserialization of nested SagaActionRecord
        executed_actions_data = data.get("executed_actions", [])
        data["executed_actions"] = [SagaActionRecord(**rec) for rec in executed_actions_data]
        return cls(**data)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# --- Persistence ---
class SagaRepository(ABC):
    @abstractmethod
    def save_state(self, state: SagaState) -> None: ...
    @abstractmethod
    def load_state(self, saga_id: str) -> Optional[SagaState]: ...
    @abstractmethod
    def delete_state(self, saga_id: str) -> None: ...

class JsonFileSagaRepository(SagaRepository):
    def __init__(self, storage_path: str = "./saga_states"):
        self.storage_path = storage_path
        os.makedirs(self.storage_path, exist_ok=True)

    def _get_file_path(self, saga_id: str) -> str:
        return os.path.join(self.storage_path, f"{saga_id}.json")

    def save_state(self, state: SagaState) -> None:
        file_path = self._get_file_path(state.saga_id)
        try:
            with open(file_path, 'w') as f:
                json.dump(state.to_dict(), f, indent=2)
            logger.debug(f"Saga state for {state.saga_id} saved to {file_path}")
        except IOError as e:
            logger.error(f"Failed to save saga state for {state.saga_id} to {file_path}: {e}")
            raise SagaPersistenceError(f"Failed to save saga state: {e}", saga_id=state.saga_id) from e

    def load_state(self, saga_id: str) -> Optional[SagaState]:
        file_path = self._get_file_path(saga_id)
        if not os.path.exists(file_path):
            return None
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            state = SagaState.from_dict(data)
            logger.debug(f"Saga state for {saga_id} loaded from {file_path}")
            return state
        except (IOError, json.JSONDecodeError) as e:
            logger.error(f"Failed to load saga state for {saga_id} from {file_path}: {e}")
            raise SagaPersistenceError(f"Failed to load saga state: {e}", saga_id=saga_id) from e
        
    def delete_state(self, saga_id: str) -> None:
        file_path = self._get_file_path(saga_id)
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.debug(f"Saga state for {saga_id} deleted from {file_path}")
        except IOError as e:
            logger.error(f"Failed to delete saga state for {saga_id} from {file_path}: {e}")
            raise SagaPersistenceError(f"Failed to delete saga state: {e}", saga_id=saga_id) from e


# --- Saga Manager ---
class SagaManager:
    """
    Manages the execution and compensation of a distributed saga.
    Interacts with a message broker for asynchronous step execution
    and a repository for state persistence.
    """
    def __init__(self,
                 saga_definition_id: str,
                 steps: List[SagaStep], # The static definition of saga steps
                 broker: MessageBroker,
                 repository: SagaRepository,
                 saga_id: Optional[str] = None): # If saga_id is provided, it's for a specific instance

        self.saga_definition_id = saga_definition_id
        self.steps_definition = steps # Store the definition
        self.broker = broker
        self.repository = repository
        
        # If saga_id is passed, this manager instance is for that specific saga.
        # If not, a new one will be generated when 'start' is called.
        self._instance_saga_id = saga_id 

        # Reply topics should be specific to this manager instance if it handles one saga,
        # or more generic if a single manager handles many sagas of this type.
        # For this iteration, let's assume one manager instance per saga execution if saga_id is fixed at init.
        # If saga_id is dynamic (generated at start), then reply topics need to include it.
        # Let's make reply topics include the saga_id.
        # The manager needs to subscribe to these. This implies the manager is long-lived
        # or the subscription is handled by the hosting agent/service.

        # For simplicity, we'll assume the hosting environment sets up subscriptions
        # to route relevant messages to this manager's handler methods.
        # The handler methods will use the saga_id from the message to load state.

    def _get_reply_topics(self, saga_id: str) -> Tuple[str, str]:
        action_result_topic = f"saga.{saga_id}.action_result"
        compensation_result_topic = f"saga.{saga_id}.compensation_result"
        return action_result_topic, compensation_result_topic

    def start_new_saga(self, initial_payload: Dict[str, Any], correlation_id: Optional[str] = None) -> str:
        """Creates and starts a new saga instance."""
        saga_id = self._instance_saga_id or f"saga-{self.saga_definition_id}-{uuid.uuid4()}"
        
        if self.repository.load_state(saga_id):
            logger.error(f"Saga {saga_id} already exists. Cannot start new with the same ID.")
            raise SagaExecutionError(f"Saga {saga_id} already exists.", saga_id)

        state = SagaState(
            saga_id=saga_id,
            definition_id=self.saga_definition_id,
            current_step_index=0,
            current_compensating_step_index=-1, # Not compensating initially
            status="PREPARED",
            executed_actions=[],
            shared_payload=initial_payload.copy(),
            correlation_id=correlation_id
        )
        state.status = "RUNNING"
        state.update_timestamp()
        self.repository.save_state(state)
        logger.info(f"Saga {state.saga_id} created and persisted. Starting first action.")
        self._trigger_action_for_state(state)
        return saga_id

    def resume_saga(self, saga_id: str) -> None:
        """Resumes a saga from its persisted state."""
        state = self.repository.load_state(saga_id)
        if not state:
            logger.warning(f"Saga {saga_id} not found for resumption.")
            raise SagaError(f"Saga {saga_id} not found for resumption.", saga_id)

        if state.definition_id != self.saga_definition_id:
            err_msg = (f"Saga {saga_id} definition mismatch. "
                       f"Loaded: {state.definition_id}, Manager expected: {self.saga_definition_id}")
            logger.error(err_msg)
            raise SagaError(err_msg, saga_id)

        logger.info(f"Saga {saga_id}: Resuming with status '{state.status}'")

        if state.status == "RUNNING":
            # Check if the last recorded action was PENDING, implies it might not have completed or reply lost
            if state.executed_actions and state.executed_actions[-1].status == "PENDING":
                 logger.info(f"Saga {saga_id}: Last action '{state.executed_actions[-1].step_name}' was PENDING. Re-triggering.")
                 self._retrigger_pending_action(state)
            else: # Trigger next logical action
                 logger.info(f"Saga {saga_id}: Triggering next logical action.")
                 self._trigger_action_for_state(state)
        elif state.status == "COMPENSATING":
            if state.executed_actions and state.current_compensating_step_index >=0 and \
               state.executed_actions[state.current_compensating_step_index].status == "PENDING_COMPENSATION":
                logger.info(f"Saga {saga_id}: Last compensation '{state.executed_actions[state.current_compensating_step_index].step_name}' was PENDING. Re-triggering.")
                self._retrigger_pending_compensation(state)
            else:
                logger.info(f"Saga {saga_id}: Triggering next logical compensation.")
                self._trigger_compensation_for_state(state, state.current_compensating_step_index)

        elif state.status in ["COMPLETED_SUCCESS", "FAILED_ACTION", "FAILED_COMPENSATION"]:
            logger.info(f"Saga {state.saga_id} is already in a terminal state: {state.status}. No action taken.")
        else:
            logger.warning(f"Saga {state.saga_id}: Unhandled status '{state.status}' for resumption.")


    def _get_step_definition(self, step_name: str) -> Optional[SagaStep]:
        return next((s for s in self.steps_definition if s.name == step_name), None)

    def _retrigger_pending_action(self, state: SagaState):
        step_def = self.steps_definition[state.current_step_index]
        action_record = state.executed_actions[-1] # The PENDING one
        action_payload = action_record.action_payload # Use originally prepared payload
        
        action_reply_topic, _ = self._get_reply_topics(state.saga_id)
        message_content = {
            "saga_id": state.saga_id,
            "step_index": state.current_step_index,
            "step_name": step_def.name,
            "action_payload": action_payload,
            "reply_topic": action_reply_topic,
            "correlation_id": state.correlation_id
        }
        logger.info(f"Saga {state.saga_id}: Re-triggering action for step '{step_def.name}' to topic {step_def.action_topic}.")
        self.broker.publish(step_def.action_topic, message_content)

    def _trigger_action_for_state(self, state: SagaState):
        if state.current_step_index >= len(self.steps_definition):
            state.status = "COMPLETED_SUCCESS"
            state.update_timestamp()
            self.repository.save_state(state)
            logger.info(f"Saga {state.saga_id} completed successfully. Final payload: {state.shared_payload}")
            self.broker.publish(f"saga_events.{state.saga_id}.completed", {"saga_id": state.saga_id, "final_payload": state.shared_payload})
            return

        step_def = self.steps_definition[state.current_step_index]
        action_payload = {}
        if step_def.action_params_builder:
            action_payload = step_def.action_params_builder(state.shared_payload)
        else: # Default: pass shared_payload as action_payload
            action_payload = state.shared_payload.copy()


        action_record = SagaActionRecord(step_name=step_def.name, action_payload=action_payload, status="PENDING")
        state.executed_actions.append(action_record)
        state.update_timestamp()
        self.repository.save_state(state)

        action_reply_topic, _ = self._get_reply_topics(state.saga_id)
        message_content = {
            "saga_id": state.saga_id,
            "step_index": state.current_step_index,
            "step_name": step_def.name,
            "action_payload": action_payload,
            "reply_topic": action_reply_topic,
            "correlation_id": state.correlation_id
        }
        logger.info(f"Saga {state.saga_id}: Triggering action for step '{step_def.name}' ({state.current_step_index}) to topic {step_def.action_topic}.")
        self.broker.publish(step_def.action_topic, message_content)

    def handle_action_result(self, message_payload: Dict[str, Any]):
        saga_id = message_payload.get("saga_id")
        step_idx_completed = message_payload.get("step_index")
        success = message_payload.get("success")
        action_output = message_payload.get("action_output") # This is the direct result of the action
        error_details = message_payload.get("error_details")
        # Optional: action can suggest updates to the shared payload
        updated_shared_data = message_payload.get("updated_shared_payload", {})

        state = self.repository.load_state(saga_id)
        if not state:
            logger.error(f"Saga {saga_id}: Received action result for non-existent or already deleted saga.")
            return # Or NACK

        if state.status != "RUNNING" or step_idx_completed != state.current_step_index:
            logger.warning(f"Saga {saga_id}: Received action result for step {step_idx_completed} "
                           f"but current step is {state.current_step_index} or status is {state.status}. Ignoring.")
            return # Or NACK / dead-letter

        action_record = state.executed_actions[step_idx_completed] # Should be the last one, and PENDING

        if success:
            action_record.status = "ACTION_COMPLETED"
            action_record.action_result = action_output # Store the specific result
            state.shared_payload.update(updated_shared_data) # Merge updates to shared payload
            logger.info(f"Saga {saga_id}: Step '{action_record.step_name}' completed. Result: {action_output}, Shared payload updated.")
            
            state.current_step_index += 1
            state.update_timestamp()
            self.repository.save_state(state)
            self._trigger_action_for_state(state)
        else:
            action_record.status = "ACTION_FAILED"
            action_record.action_result = error_details # Store error as "result"
            state.status = "FAILED_ACTION" # Saga is now in a failed state
            logger.error(f"Saga {saga_id}: Step '{action_record.step_name}' failed: {error_details}. Initiating compensation.")
            
            state.update_timestamp()
            self.repository.save_state(state)
            # Start compensating from the step that just failed (which is current_step_index)
            self._trigger_compensation_for_state(state, state.current_step_index)


    def _retrigger_pending_compensation(self, state: SagaState):
        action_to_compensate_record = state.executed_actions[state.current_compensating_step_index]
        step_def = self._get_step_definition(action_to_compensate_record.step_name)
        if not step_def:
            # This should not happen if definitions are consistent
            logger.error(f"Saga {state.saga_id}: Cannot find step definition for '{action_to_compensate_record.step_name}' during re-trigger compensation.")
            state.status = "FAILED_COMPENSATION" # Critical error
            self.repository.save_state(state)
            return

        # Use the original action_result and shared_payload for compensation_params_builder
        compensation_payload = {}
        if step_def.compensation_params_builder:
            compensation_payload = step_def.compensation_params_builder(
                action_to_compensate_record.action_result, # Result of the original forward action
                state.shared_payload # Current shared payload
            )
        else: # Default: pass action_result and shared_payload
            compensation_payload = {
                "action_result": action_to_compensate_record.action_result,
                "shared_payload": state.shared_payload.copy()
            }
        
        _, compensation_reply_topic = self._get_reply_topics(state.saga_id)
        message_content = {
            "saga_id": state.saga_id,
            "step_index_to_compensate": state.current_compensating_step_index,
            "step_name": step_def.name,
            "compensation_payload": compensation_payload,
            "reply_topic": compensation_reply_topic,
            "correlation_id": state.correlation_id
        }
        logger.info(f"Saga {state.saga_id}: Re-triggering compensation for step '{step_def.name}' to topic {step_def.compensate_topic}.")
        self.broker.publish(step_def.compensate_topic, message_content)


    def _trigger_compensation_for_state(self, state: SagaState, last_executed_action_idx: int):
        state.status = "COMPENSATING"
        # current_compensating_step_index points to the action in executed_actions to be compensated.
        # Initialize if not already set (e.g., first time entering compensation)
        if state.current_compensating_step_index == -1:
            state.current_compensating_step_index = last_executed_action_idx
        
        # Iterate backwards through executed actions that need compensation
        while state.current_compensating_step_index >= 0:
            action_record = state.executed_actions[state.current_compensating_step_index]
            # Compensate actions that were COMPLETED or FAILED (if they need cleanup)
            # Skip already compensated or if compensation attempt failed
            if action_record.status in ["ACTION_COMPLETED", "ACTION_FAILED"]:
                break 
            state.current_compensating_step_index -= 1
        else: # No more steps to compensate
            final_status = "FAILED_ACTION" # Default if all compensations succeeded after an action failure
            # Check if any compensation itself failed
            if any(rec.status == "COMPENSATION_FAILED" for rec in state.executed_actions):
                final_status = "FAILED_COMPENSATION"

            state.status = final_status 
            state.update_timestamp()
            self.repository.save_state(state)
            logger.info(f"Saga {state.saga_id}: Compensation process finished. Final status: {state.status}")
            self.broker.publish(f"saga_events.{state.saga_id}.failed", {"saga_id": state.saga_id, "reason": f"Saga failed, compensation ended with status: {state.status}"})
            return

        action_to_compensate_record = state.executed_actions[state.current_compensating_step_index]
        step_def = self._get_step_definition(action_to_compensate_record.step_name)
        if not step_def:
            logger.critical(f"Saga {state.saga_id}: Missing step definition for '{action_to_compensate_record.step_name}' during compensation. Halting.")
            state.status = "FAILED_COMPENSATION" # System/config error
            self.repository.save_state(state)
            return

        compensation_payload = {}
        if step_def.compensation_params_builder:
            compensation_payload = step_def.compensation_params_builder(
                action_to_compensate_record.action_result, # Original action's result
                state.shared_payload # Current shared payload
            )
        else:
             compensation_payload = {
                "action_result": action_to_compensate_record.action_result,
                "shared_payload": state.shared_payload.copy()
            }

        action_to_compensate_record.status = "PENDING_COMPENSATION"
        state.update_timestamp()
        self.repository.save_state(state)

        _, compensation_reply_topic = self._get_reply_topics(state.saga_id)
        message_content = {
            "saga_id": state.saga_id,
            "step_index_to_compensate": state.current_compensating_step_index, # Index in executed_actions
            "step_name": step_def.name,
            "compensation_payload": compensation_payload,
            "reply_topic": compensation_reply_topic,
            "correlation_id": state.correlation_id
        }
        logger.info(f"Saga {state.saga_id}: Triggering compensation for step '{step_def.name}' to topic {step_def.compensate_topic}.")
        self.broker.publish(step_def.compensate_topic, message_content)


    def handle_compensation_result(self, message_payload: Dict[str, Any]):
        saga_id = message_payload.get("saga_id")
        step_idx_compensated = message_payload.get("step_index_to_compensate")
        success = message_payload.get("success")
        error_details = message_payload.get("error_details")
        # updated_shared_data = message_payload.get("updated_shared_payload", {}) # Compensation can also update

        state = self.repository.load_state(saga_id)
        if not state:
            logger.error(f"Saga {saga_id}: Received compensation result for non-existent saga.")
            return

        if state.status != "COMPENSATING" or step_idx_compensated != state.current_compensating_step_index:
            logger.warning(f"Saga {saga_id}: Received compensation result for step index {step_idx_compensated} "
                           f"but current compensating index is {state.current_compensating_step_index} or status is {state.status}. Ignoring.")
            return

        action_record = state.executed_actions[step_idx_compensated]

        if success:
            action_record.status = "COMPENSATION_COMPLETED"
            # if updated_shared_data: state.shared_payload.update(updated_shared_data)
            logger.info(f"Saga {saga_id}: Compensation for step '{action_record.step_name}' succeeded.")
            state.current_compensating_step_index -= 1 # Move to the previous action for compensation
        else:
            action_record.status = "COMPENSATION_FAILED"
            state.status = "FAILED_COMPENSATION" # Saga is now in a compensation-failed state
            logger.error(f"Saga {saga_id}: Compensation for step '{action_record.step_name}' failed: {error_details}. Halting further compensation.")
        
        state.update_timestamp()
        self.repository.save_state(state)

        if success: # If this one succeeded, try to compensate the next (previous) one
            self._trigger_compensation_for_state(state, state.current_compensating_step_index)
        else: # Compensation failed, publish final failure event
            self.broker.publish(f"saga_events.{state.saga_id}.failed", {"saga_id": state.saga_id, "reason": f"Compensation failed for step {action_record.step_name}"})

