import logging
from typing import List, Dict, Any, Callable, Tuple, Optional
import uuid

logger = logging.getLogger(__name__)

class SagaExecutionError(Exception):
    """Custom exception for errors during Saga execution's action phase."""
    def __init__(self, message: str, saga_id: str, failed_step_name: str, original_exception: Exception):
        super().__init__(message)
        self.saga_id = saga_id
        self.failed_step_name = failed_step_name
        self.original_exception = original_exception

class SagaCompensationError(Exception):
    """Custom exception for errors during Saga compensation phase."""
    def __init__(self, message: str, saga_id: str, compensation_failures: List[Tuple[str, Exception]]):
        super().__init__(message)
        self.saga_id = saga_id
        self.compensation_failures = compensation_failures # List of (step_name, exception)

class SagaStep:
    """
    Represents a single step in a saga, including its action and compensation logic.
    """
    def __init__(self, name: str,
                 action: Callable[..., Any],
                 compensate: Callable[[Any, ...], Any]):
        """
        Initializes a SagaStep.

        Args:
            name: The name of the saga step.
            action: The function to execute for this step.
            compensate: The function to execute to compensate/undo this step.
                        It will receive the result of the action as its first argument.
        """
        self.name = name
        self.action = action
        self.compensate = compensate
        self.action_args: Tuple = ()
        self.action_kwargs: Dict[str, Any] = {}
        self.compensate_args: Tuple = ()  # Additional args for compensate, after action_result
        self.compensate_kwargs: Dict[str, Any] = {}

class SagaManager:
    """
    Manages the execution and compensation of a sequence of saga steps.
    """
    def __init__(self, saga_id: Optional[str] = None):
        self.saga_id = saga_id or f"saga-{uuid.uuid4()}"
        self.steps: List[SagaStep] = []
        # Stores (step_object, action_result) for successfully completed steps
        self._completed_step_info: List[Tuple[SagaStep, Any]] = []

    def add_step(self, name: str,
                 action: Callable[..., Any],
                 compensate: Callable[[Any, ...], Any],
                 action_args: Tuple = (), action_kwargs: Optional[Dict[str, Any]] = None,
                 compensate_args: Tuple = (), compensate_kwargs: Optional[Dict[str, Any]] = None) -> None:
        """Adds a step to the saga."""
        step = SagaStep(name, action, compensate)
        step.action_args = action_args
        step.action_kwargs = action_kwargs or {}
        step.compensate_args = compensate_args
        step.compensate_kwargs = compensate_kwargs or {}
        self.steps.append(step)

    def execute(self) -> Dict[str, Any]:
        """
        Executes all steps in the saga. If any step fails, it attempts to compensate
        for all previously completed steps in reverse order.

        Returns:
            A dictionary of results from each successful action step, keyed by step name.

        Raises:
            SagaExecutionError: If an action step fails. Compensation will be attempted.
            SagaCompensationError: If one or more compensation steps fail after an action failure.
        """
        self._completed_step_info.clear()
        results: Dict[str, Any] = {}

        for i, step in enumerate(self.steps):
            try:
                logger.info(f"Saga {self.saga_id}: Executing step '{step.name}' ({i + 1}/{len(self.steps)}).")
                action_result = step.action(*step.action_args, **step.action_kwargs)
                self._completed_step_info.append((step, action_result))
                results[step.name] = action_result
                logger.info(f"Saga {self.saga_id}: Step '{step.name}' completed successfully.")
            except Exception as e:
                logger.error(f"Saga {self.saga_id}: Step '{step.name}' failed: {e}. Initiating compensation.")
                self._compensate() # This might raise SagaCompensationError
                raise SagaExecutionError(
                    f"Saga {self.saga_id} failed at step '{step.name}'. Compensation attempted.",
                    saga_id=self.saga_id, failed_step_name=step.name, original_exception=e
                ) from e

        logger.info(f"Saga {self.saga_id}: All steps completed successfully.")
        return results

    def _compensate(self) -> None:
        logger.info(f"Saga {self.saga_id}: Starting compensation for {len(self._completed_step_info)} completed step(s).")
        compensation_failures: List[Tuple[str, Exception]] = []

        for step, action_result in reversed(self._completed_step_info):
            try:
                logger.info(f"Saga {self.saga_id}: Compensating step '{step.name}'.")
                step.compensate(action_result, *step.compensate_args, **step.compensate_kwargs)
                logger.info(f"Saga {self.saga_id}: Step '{step.name}' compensated successfully.")
            except Exception as e:
                logger.error(f"Saga {self.saga_id}: Compensation for step '{step.name}' failed: {e}.")
                compensation_failures.append((step.name, e))

        if compensation_failures:
            raise SagaCompensationError(
                f"Saga {self.saga_id}: One or more compensation steps failed.",
                saga_id=self.saga_id, compensation_failures=compensation_failures
            )
        logger.info(f"Saga {self.saga_id}: Compensation process finished successfully.")