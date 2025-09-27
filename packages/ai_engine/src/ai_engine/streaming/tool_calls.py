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
from typing import Any, Dict, List, Literal, Optional, Set, Tuple

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


class ToolCallArgumentStatus(Enum):
    """Status of tool call argument construction (NOT execution).

    This tracks the lifecycle of building tool call arguments, whether from
    streaming chunks or complete state messages. Tool execution status is
    tracked separately via ToolCallEvent status fields.
    """

    INITIALIZING = "initializing"  # First message received with metadata
    STREAMING_ARGS = "streaming_args"  # Accumulating argument chunks
    ARGS_READY = "args_ready"  # Arguments parsed successfully, ready for execution
    ARGS_INVALID = "args_invalid"  # Failed to parse arguments


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
    status: ToolCallArgumentStatus = ToolCallArgumentStatus.INITIALIZING
    error_message: Optional[str] = None

    # Result state (from ToolMessage[Chunk])
    result: Optional[Dict[str, Any]] = None
    result_status: Optional[Literal["success", "error"]] = None  # "success" | "error"

    def add_args_chunk(self, args_chunk: str) -> bool:
        """Add an argument chunk and try to parse.

        Args:
            args_chunk: New chunk of arguments

        Returns:
            True if parsing succeeded (arguments are ready)
        """
        if self.status == ToolCallArgumentStatus.ARGS_INVALID:
            return False

        self.accumulated_args += args_chunk
        self.status = ToolCallArgumentStatus.STREAMING_ARGS

        # Try to parse the accumulated JSON
        return self.try_parse_args()

    def try_parse_args(self) -> bool:
        """Attempt to parse accumulated arguments as JSON.

        Returns:
            True if parsing succeeded and arguments are ready
        """
        if not self.accumulated_args.strip():
            return False

        try:
            # Try to parse the accumulated JSON
            self.parsed_args = json.loads(self.accumulated_args)
            self.status = ToolCallArgumentStatus.ARGS_READY
            logger.debug(f"Tool call {self.tool_call_id} arguments ready: {self.parsed_args}")
            return True
        except json.JSONDecodeError as e:
            # Check if it looks like it should be complete but failed
            if self._looks_complete_but_invalid():
                self.status = ToolCallArgumentStatus.ARGS_INVALID
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
    """Track tool call lifecycle with clear separation of concerns:

    - handle_tool_calls_from_stream(): Handle arguments incrementally from streaming chunks
    - handle_tool_calls_from_state(): Handle complete tool calls from state channels
    - handle_tool_execution_result(): Handle tool execution results

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

    def handle_tool_calls_from_stream(
        self, chunk: AIMessageChunk, namespace: str, task_id: Optional[str] = None
    ) -> List[ToolCallEvent]:
        """Handle tool call arguments incrementally from streaming chunks.

        Handles the complex streaming pattern where:
        1. First message contains complete metadata (id, name)
        2. Subsequent chunks only contain argument pieces
        3. Arguments are reconstructed incrementally until valid JSON

        Args:
            chunk: The AI message chunk to process
            namespace: Current namespace
            task_id: Optional task ID

        Returns:
            List of generated events (started, progress, ready, error)
        """
        events = []

        if not chunk.id:
            logger.warning("Missing Message ID for tool call processing")
            logger.debug(f"Message: {chunk.pretty_repr()}")
            return events

        if not chunk.tool_calls and not chunk.tool_call_chunks:
            return events

        # Check for tool call initialization (first message with complete metadata)
        for i, tool_call in enumerate(chunk.tool_calls):
            if tool_call.get("id") and tool_call.get("name"):
                # This is a first message with complete metadata
                index = chunk.additional_kwargs.get("tool_calls", [])[i].get("index", i)
                events.append(self._initialize_tool_call(chunk.id, index, tool_call, namespace, task_id))

        logger.debug(f"Initialized {len(events)} tool calls")

        # Process argument chunks
        for tool_call_chunk in chunk.tool_call_chunks:
            if tool_call_chunk["args"]:  # Only process chunks with argument content
                events.extend(self._process_tool_call_chunk(chunk.id, tool_call_chunk, namespace, task_id))

        return events

    def handle_tool_calls_from_state(
        self, message: AIMessage, namespace: str, task_id: Optional[str] = None
    ) -> List[ToolCallEvent]:
        """Handle complete tool calls from state channels.

        Handles complete tool calls from state channels where arguments are
        already parsed and ready for execution. Skips the streaming lifecycle
        and directly emits 'args_ready' events.

        Args:
            message: Complete AIMessage containing tool calls
            namespace: Current namespace
            task_id: Optional task ID

        Returns:
            List of ToolCallEvents with 'args_ready' status
        """
        events: List[ToolCallEvent] = []

        if not message.tool_calls:
            return events

        message_id = message.id or ""
        for index, tool_call in enumerate(message.tool_calls):
            tool_call_id = tool_call.get("id")
            tool_name = tool_call.get("name")
            args_obj = tool_call.get("args")

            if not tool_call_id or not tool_name:
                # Skip incomplete entries
                logger.warning("Skipping tool call without id or name in complete message processing")
                continue

            old_state = self._id_to_state.get(tool_call_id)

            # Arguments are already complete
            parsed_args: Optional[Dict[str, Any]] = args_obj
            accumulated_args: str = json.dumps(args_obj) if args_obj else ""

            # Register state for linking results
            state = ToolCallState(
                tool_call_id=tool_call_id,
                tool_name=tool_name,
                message_id=message_id,
                index=index,
                accumulated_args=accumulated_args,
                parsed_args=parsed_args,
                status=ToolCallArgumentStatus.ARGS_READY
                if parsed_args is not None
                else ToolCallArgumentStatus.ARGS_INVALID,
                result_status=old_state.result_status if old_state else None,
                result=old_state.result if old_state else None,
            )
            self._id_to_state[tool_call_id] = state

            # Skip if already processed (deduplication)
            if old_state and old_state.status in [
                ToolCallArgumentStatus.ARGS_READY,
                ToolCallArgumentStatus.ARGS_INVALID,
            ]:
                logger.debug(f"Tool call {tool_call_id} already processed; skipping emission")
                continue

            self._completed_calls.append(state)
            events.append(
                ToolCallEvent(
                    tool_name=tool_name,
                    namespace=namespace,
                    task_id=task_id or "",
                    tool_call_id=tool_call_id,
                    message_id=message_id,
                    index=index,
                    status="args_ready" if parsed_args is not None else "args_error",
                    args=parsed_args,
                    args_delta=accumulated_args,
                    args_accumulated=accumulated_args,
                    error=None if parsed_args is not None else "Invalid JSON args in complete message",
                )
            )

        return events

    def handle_tool_execution_result(
        self, result_message: ToolMessageChunk | ToolMessage, namespace: str, task_id: Optional[str] = None
    ) -> List[ToolCallEvent]:
        """Handle tool execution results.

        Processes ToolMessage/ToolMessageChunk containing the results of tool execution.
        Links results back to the original tool call state using tool_call_id.

        Args:
            result_message: Message containing tool execution result
            namespace: Current namespace
            task_id: Optional task ID

        Returns:
            List of ToolCallEvents with execution results
        """
        events: List[ToolCallEvent] = []

        tool_call_id = result_message.tool_call_id
        if not tool_call_id:
            return events

        state = self._id_to_state.get(tool_call_id)
        if state and state.result_status:
            logger.warning(f"Tool call {tool_call_id} result already processed")
            return []

        if not state:
            # Auto-create a synthetic state so the result can still be tracked
            logger.warning(f"Received tool result for unknown tool_call_id={tool_call_id}; creating synthetic state")
            state = ToolCallState(
                tool_call_id=tool_call_id,
                tool_name=result_message.name or "",
                message_id=result_message.id or "",
                index=0,
                status=ToolCallArgumentStatus.ARGS_READY,
            )
            self._id_to_state[tool_call_id] = state

        # Build result payload
        result_payload: Dict[str, Any] = {
            "content": result_message.content,
            "artifact": result_message.artifact,
            "status": result_message.status,
            "response_metadata": result_message.response_metadata,
        }

        state.result = result_payload
        state.result_status = result_message.status
        self._id_to_state[tool_call_id] = state

        status: str = "result_success" if result_message.status == "success" else "result_error"

        events.append(
            ToolCallEvent(
                tool_name=state.tool_name,
                namespace=namespace,
                task_id=task_id or "",
                tool_call_id=state.tool_call_id,
                message_id=result_message.id or state.message_id,
                index=state.index,
                status=status,  # "result_success" | "result_error"
                args=state.parsed_args,
                result=result_payload,
                error=str(result_message.content) if status == "result_error" else None,
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
            status=ToolCallArgumentStatus.INITIALIZING,
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
            status="args_started",
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

        # Add the chunk and check if arguments are ready
        is_ready = state.add_args_chunk(args_chunk)

        # If arguments are ready, generate completion event and move to completed
        if is_ready:
            if state.status == ToolCallArgumentStatus.ARGS_READY:
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
                status="args_streaming" if not is_ready else "args_ready",
                args=state.parsed_args,
            )
        ]

    def get_active_calls(self) -> Dict[Tuple[str, int], ToolCallState]:
        """Get currently active (streaming) tool calls."""
        return self._active_calls.copy()

    def get_completed_calls(self) -> List[ToolCallState]:
        """Get completed calls from current iteration."""
        return self._completed_calls.copy()

    def get_completed_calls_by_tool_call_id(self) -> set[str]:
        """Get completed calls by ID."""
        return {state.tool_call_id for state in self._completed_calls} | {
            str(call["id"]) for call in self._call_history
        }

    def get_all_completed_calls(self) -> List[Dict[str, Any]]:
        """Get all completed tool calls with history."""
        current_completed = []
        for state in self._completed_calls:
            if state.status == ToolCallArgumentStatus.ARGS_READY and state.parsed_args is not None:
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
            if state.status == ToolCallArgumentStatus.ARGS_READY and state.parsed_args is not None:
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

    def has_tool_call(self, tool_call_id: str) -> bool:
        """Check if a tool call has been processed."""
        return tool_call_id in self._id_to_state
