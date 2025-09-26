"""Tool call streaming handler.

Implements the complex tool call streaming pattern documented in 0_stream_parsing.md:
1. First message has complete metadata (id, name)
2. Subsequent chunks only have args and index
3. Link chunks using (message_id, index) tuple
4. Reconstruct JSON arguments from streaming chunks

Integrates and improves functionality from utils/streaming_parser.py.
"""

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    BaseMessage,
    ToolCall,
    ToolCallChunk,
    ToolMessage,
    ToolMessageChunk,
)
from pydantic.v1.typing import AnyCallable

from .events import ToolCallEvent

logger = logging.getLogger(__name__)


class ToolCallStatus(Enum):
    """Status of a streaming tool call.

    NOTE: COMPLETED refers to argument streaming completion (JSON parsed),
    not the final tool execution result. Tool execution results are tracked
    via separate ToolCallEvent statuses (result_received/result_error).
    """

    INITIALIZING = "initializing"  # First message received
    STREAMING = "streaming"  # Accumulating argument chunks
    COMPLETED = "completed"  # Successfully parsed final JSON (args complete)
    ERROR = "error"  # Failed to parse or other error while streaming args


@dataclass
class ToolCallState:
    """State of a streaming tool call using (message_id, index) linking."""

    # Metadata from first message
    tool_call_id: str  # From first message tool_calls[index].id
    tool_name: str  # From first message tool_calls[index].name
    message_id: str  # Message ID for linking chunks
    index: int  # Tool call index within the message

    # Streaming state
    accumulated_args: str = ""  # Building JSON string
    parsed_args: Optional[Dict[str, Any]] = None  # Final parsed arguments
    status: ToolCallStatus = ToolCallStatus.INITIALIZING
    error_message: Optional[str] = None

    # Result state (from ToolMessage[Chunk])
    result: Optional[Dict[str, Any]] = None
    result_status: Optional[str] = None  # "success" | "error"

    def add_args_chunk(self, args_chunk: str) -> bool:
        """Add an argument chunk and try to parse.

        Args:
            args_chunk: New chunk of arguments

        Returns:
            True if parsing succeeded (call is complete)
        """
        if self.status == ToolCallStatus.ERROR:
            return False

        self.accumulated_args += args_chunk
        self.status = ToolCallStatus.STREAMING

        # Try to parse the accumulated JSON
        return self.try_parse_args()

    def try_parse_args(self) -> bool:
        """Attempt to parse accumulated arguments as JSON.

        Returns:
            True if parsing succeeded and call is complete
        """
        if not self.accumulated_args.strip():
            return False

        try:
            # Try to parse the accumulated JSON
            self.parsed_args = json.loads(self.accumulated_args)
            self.status = ToolCallStatus.COMPLETED
            logger.debug(f"Tool call {self.tool_call_id} completed: {self.parsed_args}")
            return True
        except json.JSONDecodeError as e:
            # Check if it looks like it should be complete but failed
            if self._looks_complete_but_invalid():
                self.status = ToolCallStatus.ERROR
                self.error_message = f"JSON parse error: {str(e)}"
                logger.warning(f"Tool call {self.tool_call_id} failed to parse: {self.accumulated_args}")
                return False
            # Otherwise, just not ready yet
            return False

    def _looks_complete_but_invalid(self) -> bool:
        """Check if JSON looks complete but invalid."""
        args = self.accumulated_args.strip()
        if not args:
            return False
        # Simple heuristic: has opening and closing braces
        return args.count("{") > 0 and args.count("}") > 0


class ToolCallTracker:
    """Track tool call streaming state using (message_id, index) pattern.

    Implements the linking strategy documented in 0_stream_parsing.md:
    - First message: Store metadata keyed by (message_id, index)
    - Subsequent chunks: Link using same (message_id, index) key
    """

    def __init__(self):
        # Active tool calls: (message_id, index) -> ToolCallState
        self._active_calls: Dict[Tuple[str, int], ToolCallState] = {}

        # Completed calls for current iteration
        self._completed_calls: List[ToolCallState] = []

        # History of all completed calls
        self._call_history: List[Dict[str, Any]] = []

        # Track seen message IDs to avoid duplicates
        self._seen_message_ids: Set[str] = set()

        # Current iteration counter
        self._current_iteration: int = 0

        # Map tool_call_id -> ToolCallState for quick lookup on results
        self._id_to_state: Dict[str, ToolCallState] = {}

    def process_stream_tool_calls(
        self, message: AIMessageChunk, namespace: str, task_id: Optional[str] = None
    ) -> List[Any]:
        """Process a message and return generated events.

        Args:
            message: The AI message to process
            namespace: Current namespace
            task_id: Optional task ID

        Returns:
            List of generated events (ToolCallStartedEvent, ToolCallProgressEvent, etc.)
        """
        events = []

        if not message.id:
            logger.warning("Missing Message ID for tool call processing")
            logger.debug(f"Message: {message.pretty_repr()}")
            return events

        if not message.tool_calls and not message.tool_call_chunks:
            return events

        # Check for tool call initialization (first message with complete metadata)
        for i, tool_call in enumerate(message.tool_calls):
            if tool_call.get("id") and tool_call.get("name"):
                # This is a first message with complete metadata
                events.append(self._initialize_tool_call(message.id, i, tool_call, namespace, task_id))

        for chunk in message.tool_call_chunks:
            if chunk["args"]:  # Only process chunks with argument content
                events.extend(self._process_tool_call_chunk(message.id, chunk, namespace, task_id))

        return events

    def process_tool_call_result(
        self, message: ToolMessageChunk | ToolMessage, namespace: str, task_id: Optional[str] = None
    ) -> List[ToolCallEvent]:
        """Process a tool call result message and return generated events."""
        events: List[ToolCallEvent] = []

        tool_call_id = message.tool_call_id
        if not tool_call_id:
            return events

        state = self._id_to_state.get(tool_call_id)
        if not state:
            logger.warning(f"Received tool result for unknown tool_call_id={tool_call_id}")
            return events

        # Build result payload
        result_payload: Dict[str, Any] = {
            "content": getattr(message, "content", None),
            "artifact": getattr(message, "artifact", None),
            "status": getattr(message, "status", None),
            "response_metadata": getattr(message, "response_metadata", {}),
        }

        state.result = result_payload
        state.result_status = getattr(message, "status", None)

        status: str = "result_received" if getattr(message, "status", "success") == "success" else "result_error"

        events.append(
            ToolCallEvent(
                tool_name=state.tool_name,
                namespace=namespace,
                task_id=task_id or "",
                tool_call_id=state.tool_call_id,
                message_id=getattr(message, "id", None) or state.message_id,
                index=state.index,
                status=status,  # "result_received" | "result_error"
                args=state.parsed_args,
                result=result_payload,
                error=str(getattr(message, "content", "")) if status == "result_error" else None,
            )
        )

        return events

    def _initialize_tool_call(
        self, message_id: str, index: int, tool_call: ToolCall, namespace: str, task_id: Optional[str]
    ) -> ToolCallEvent:
        """Initialize a tool call from first message with complete metadata."""

        key = (message_id, index)

        # Create tool call state
        state = ToolCallState(
            tool_call_id=tool_call["id"],  # type: ignore -> we do the check before
            tool_name=tool_call["name"],
            message_id=message_id,
            index=index,
            status=ToolCallStatus.INITIALIZING,
        )

        self._active_calls[key] = state
        self._id_to_state[state.tool_call_id] = state

        logger.debug(f"Initialized tool call {tool_call['id']} at ({message_id}, {index})")

        return ToolCallEvent(
            tool_name=tool_call["name"],
            namespace=namespace,
            task_id=task_id or "",
            tool_call_id=state.tool_call_id,  # type: ignore : we do the check before
            message_id=state.message_id,
            index=state.index,
            status="started_streaming",
        )

    def _process_tool_call_chunk(
        self, message_id: str, chunk: ToolCallChunk, namespace: str, task_id: Optional[str]
    ) -> list[ToolCallEvent]:
        """Process a tool call argument chunk."""

        index = chunk["index"] or 0
        key = (message_id, index)

        # Find the corresponding active call
        if key not in self._active_calls:
            if chunk["id"] not in self._completed_calls:
                logger.warning(f"No active tool call for {chunk['id']} found in ({message_id}, {index})")
            else:
                logger.warning(f"Tool call {chunk['id']} already completed in ({message_id}, {index})")
            return []

        state = self._active_calls[key]

        args_chunk = chunk["args"] or ""

        # Add the chunk and check if complete
        is_complete = state.add_args_chunk(args_chunk)

        # If complete, generate completion event and move to completed
        if is_complete:
            if state.status == ToolCallStatus.COMPLETED:
                self._completed_calls.append(state)
            # Remove from active calls (keep id->state mapping for result linking)
            del self._active_calls[key]

        # Generate progress event
        return [
            ToolCallEvent(
                namespace=namespace,
                task_id=task_id,
                message_id=message_id,
                index=index,
                tool_call_id=state.tool_call_id,
                tool_name=state.tool_name,
                args_delta=args_chunk,
                args_accumulated=state.accumulated_args,
                status="args_streaming" if not is_complete else "completed_streaming",
                args=state.parsed_args,
            )
        ]

    def get_active_calls(self) -> Dict[Tuple[str, int], ToolCallState]:
        """Get currently active (streaming) tool calls."""
        return self._active_calls.copy()

    def get_completed_calls(self) -> List[ToolCallState]:
        """Get completed calls from current iteration."""
        return self._completed_calls.copy()

    def get_all_completed_calls(self) -> List[Dict[str, Any]]:
        """Get all completed tool calls with history."""
        current_completed = []
        for state in self._completed_calls:
            if state.status == ToolCallStatus.COMPLETED and state.parsed_args is not None:
                current_completed.append(
                    {
                        "id": state.tool_call_id,
                        "name": state.tool_name,
                        "args": state.parsed_args,
                        "type": "tool_call",
                        "iteration": self._current_iteration,
                    }
                )

        return self._call_history + current_completed

    def start_new_iteration(self):
        """Start a new iteration, moving completed calls to history."""
        # Move completed calls to history
        for state in self._completed_calls:
            if state.status == ToolCallStatus.COMPLETED and state.parsed_args is not None:
                self._call_history.append(
                    {
                        "id": state.tool_call_id,
                        "name": state.tool_name,
                        "args": state.parsed_args,
                        "type": "tool_call",
                        "iteration": self._current_iteration,
                    }
                )

        # Clear current iteration state
        self._completed_calls.clear()
        self._current_iteration += 1

        logger.debug(f"Started tool call iteration {self._current_iteration}")

    def reset(self):
        """Reset all tool call tracking state."""
        self._active_calls.clear()
        self._completed_calls.clear()
        self._call_history.clear()
        self._seen_message_ids.clear()
        self._id_to_state.clear()
        self._current_iteration = 0
        #
