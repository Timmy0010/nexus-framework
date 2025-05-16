import time
import threading
from typing import List, Dict, Any, Callable, Optional, Tuple
import logging

# Configure a logger for this module
logger = logging.getLogger(__name__)

# Assuming nexus_framework.Message or a similar structure for message payloads
# For this example, 'Any' will represent the message payload type.

class MessageTimeoutError(Exception):
    """Custom exception for message sequencing timeouts."""
    pass

class SequenceTracker:
    """
    Manages message sequencing for a given workflow, ensuring ordered processing.
    Includes strategies for handling out-of-order messages, buffering, and timeouts.
    """
    def __init__(self, workflow_id: str,
                 on_message_ready: Callable[[Any], None],
                 max_buffer_size: int = 100,
                 gap_timeout_seconds: float = 30.0):
        self.workflow_id = workflow_id
        self.next_sequence_to_process = 0
        # Buffer for out-of-order messages: seq -> (message_payload, arrival_time)
        self.out_of_order_buffer: Dict[int, Tuple[Any, float]] = {}
        self.on_message_ready = on_message_ready
        self.max_buffer_size = max_buffer_size
        self.gap_timeout_seconds = gap_timeout_seconds
        self.lock = threading.Lock()
        # Tracks when we started waiting for the current 'next_sequence_to_process'
        self.gap_wait_start_time: Optional[float] = None

    def receive_message(self, sequence_number: int, message: Any) -> None:
        """
        Receives a message with its sequence number and processes or buffers it.
        """
        with self.lock:
            if sequence_number < self.next_sequence_to_process or \
               sequence_number in self.out_of_order_buffer:
                logger.warning(f"Workflow {self.workflow_id}: Duplicate or old message seq {sequence_number} received. Ignoring.")
                return

            if sequence_number == self.next_sequence_to_process:
                logger.debug(f"Workflow {self.workflow_id}: Message seq {sequence_number} received in order.")
                self._process_message_and_buffered(sequence_number, message)
            elif sequence_number > self.next_sequence_to_process:
                if len(self.out_of_order_buffer) >= self.max_buffer_size:
                    logger.error(f"Workflow {self.workflow_id}: Buffer full (size {self.max_buffer_size}). "
                                 f"Rejecting message seq {sequence_number}.")
                    # Consider a more sophisticated rejection strategy if needed (e.g., drop oldest)
                    return 
                logger.debug(f"Workflow {self.workflow_id}: Message seq {sequence_number} received out of order. Buffering.")
                self.out_of_order_buffer[sequence_number] = (message, time.time())
                if self.gap_wait_start_time is None: # Start timer if a new gap is created
                    self.gap_wait_start_time = time.time()
            
            # It's good practice to check timeouts after any state change
            self._check_gap_timeout()

    def _process_message_and_buffered(self, current_sequence_number: int, current_message: Any) -> None:
        """
        Processes the current in-order message and any subsequent messages
        from the buffer that are now ready.
        Assumes lock is held.
        """
        self.on_message_ready(current_message)
        self.next_sequence_to_process = current_sequence_number + 1
        self.gap_wait_start_time = None # Reset gap timer as we've processed the expected one

        while self.next_sequence_to_process in self.out_of_order_buffer:
            next_message, _ = self.out_of_order_buffer.pop(self.next_sequence_to_process)
            logger.debug(f"Workflow {self.workflow_id}: Processing buffered message seq {self.next_sequence_to_process}.")
            self.on_message_ready(next_message)
            self.next_sequence_to_process += 1
        
        if self.out_of_order_buffer and self.gap_wait_start_time is None: # New gap might have formed
            self.gap_wait_start_time = time.time()

    def _check_gap_timeout(self) -> None:
        """
        Checks if the current gap (waiting for 'next_sequence_to_process') has timed out.
        Assumes lock is held.
        """
        if self.out_of_order_buffer and \
           self.gap_wait_start_time and \
           (time.time() - self.gap_wait_start_time > self.gap_timeout_seconds):
            
            missing_sequence = self.next_sequence_to_process
            logger.warning(f"Workflow {self.workflow_id}: Gap timeout waiting for seq {missing_sequence}. "
                         f"Buffered messages: {sorted(self.out_of_order_buffer.keys())}.")

            # Rejection Strategy: Log missing, skip gap, and process next available if any.
            # More advanced strategies could involve requesting retransmission.
            if self.out_of_order_buffer:
                min_buffered_seq = min(self.out_of_order_buffer.keys())
                logger.warning(f"Workflow {self.workflow_id}: Skipping missing sequence(s) up to {min_buffered_seq} due to timeout.")
                # Report/log actually missing sequences
                for seq_num in range(self.next_sequence_to_process, min_buffered_seq):
                     logger.error(f"Workflow {self.workflow_id}: Sequence {seq_num} declared missing due to timeout.")
                
                self.next_sequence_to_process = min_buffered_seq
                message_to_process, _ = self.out_of_order_buffer.pop(self.next_sequence_to_process)
                self._process_message_and_buffered(self.next_sequence_to_process, message_to_process) # Will also reset timer
            else:
                # No buffered messages, just reset timer as the gap is "resolved" by timeout
                self.gap_wait_start_time = None

    def get_next_expected_sequence(self) -> int:
        with self.lock:
            return self.next_sequence_to_process

    def force_check_timeouts(self) -> None:
        """Externally callable method to trigger timeout checks, e.g., by a periodic timer."""
        with self.lock:
            self._check_gap_timeout()