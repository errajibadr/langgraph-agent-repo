"""Streaming parser for LangGraph tool calls and messages.

This module provides utilities for parsing streaming responses from LangGraph,
handling both regular message content and progressive tool call argument building.
"""

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from langchain_core.messages import AIMessage, BaseMessage

logger = logging.getLogger(__name__)


class ToolCallStatus(Enum):
    """Status of a streaming tool call."""

    BUILDING = "building"
    COMPLETE = "complete"
    ERROR = "error"


@dataclass
class ToolCallState:
    """State of a streaming tool call."""

    id: Optional[str]
    name: Optional[str]
    accumulated_args: str = ""
    parsed_args: Optional[Dict[str, Any]] = None
    status: ToolCallStatus = ToolCallStatus.BUILDING
    error_message: Optional[str] = None

    def try_parse_args(self) -> bool:
        """Attempt to parse accumulated arguments as JSON.

        Returns:
            True if parsing succeeded, False otherwise.
        """
        if not self.accumulated_args.strip():
            return False

        try:
            # Try to parse the accumulated JSON
            self.parsed_args = json.loads(self.accumulated_args)
            self.status = ToolCallStatus.COMPLETE
            return True
        except json.JSONDecodeError as e:
            # Not ready to parse yet, or malformed JSON
            if self.accumulated_args.count("{") > 0 and self.accumulated_args.count("}") > 0:
                # Looks like it should be complete but failed to parse
                self.status = ToolCallStatus.ERROR
                self.error_message = f"JSON parse error: {str(e)}"
                logger.warning(f"Failed to parse tool call args: {self.accumulated_args}")
            return False


@dataclass
class StreamingState:
    """Current state of streaming parsing."""

    content: str = ""
    tool_calls: Dict[int, ToolCallState] = field(default_factory=dict)  # Active tool calls (current iteration)
    tool_call_history: List[Dict[str, Any]] = field(default_factory=list)  # Completed calls from previous iterations
    completed_tool_calls: List[Dict[str, Any]] = field(
        default_factory=list
    )  # All completed calls (deprecated, use history)
    is_complete: bool = False
    current_iteration: int = 0

    def get_active_tool_calls(self) -> Dict[int, ToolCallState]:
        """Get tool calls that are still being built."""
        return {idx: state for idx, state in self.tool_calls.items() if state.status == ToolCallStatus.BUILDING}

    def get_completed_tool_calls(self) -> Dict[int, ToolCallState]:
        """Get tool calls that have been completed in current iteration."""
        return {idx: state for idx, state in self.tool_calls.items() if state.status == ToolCallStatus.COMPLETE}

    def get_all_completed_tool_calls(self) -> List[Dict[str, Any]]:
        """Get all completed tool calls from all iterations."""
        current_completed = []
        for state in self.tool_calls.values():
            if state.status == ToolCallStatus.COMPLETE and state.parsed_args is not None:
                current_completed.append(
                    {
                        "id": state.id,
                        "name": state.name,
                        "args": state.parsed_args,
                        "type": "tool_call",
                        "iteration": self.current_iteration,
                    }
                )
        return self.tool_call_history + current_completed


class StreamingGraphParser:
    """Parser for streaming LangGraph responses."""

    def __init__(
        self,
        on_content_update: Optional[Callable[[str], None]] = None,
        on_tool_call_start: Optional[Callable[[int, str, str], None]] = None,
        on_tool_call_update: Optional[Callable[[int, ToolCallState], None]] = None,
        on_tool_call_complete: Optional[Callable[[int, ToolCallState], None]] = None,
        on_stream_complete: Optional[Callable[[StreamingState], None]] = None,
        on_iteration_start: Optional[Callable[[int], None]] = None,
    ):
        """Initialize the streaming parser.

        Args:
            on_content_update: Callback for content updates (content)
            on_tool_call_start: Callback when tool call starts (index, name, id)
            on_tool_call_update: Callback for tool call updates (index, state)
            on_tool_call_complete: Callback when tool call completes (index, state)
            on_stream_complete: Callback when streaming is complete (final_state)
            on_iteration_start: Callback when new iteration starts (iteration_number)
        """
        self.state = StreamingState()
        self.on_content_update = on_content_update
        self.on_tool_call_start = on_tool_call_start
        self.on_tool_call_update = on_tool_call_update
        self.on_tool_call_complete = on_tool_call_complete
        self.on_stream_complete = on_stream_complete
        self.on_iteration_start = on_iteration_start

        # Internal tracking for tool call batches
        self._global_tool_counter = 0
        self._seen_tool_ids: set = set()

    def reset(self):
        """Reset parser state for a new streaming session."""
        self.state = StreamingState()
        self._global_tool_counter = 0
        self._seen_tool_ids.clear()

    def _detect_new_tool_call_batch(self, current_tool_ids: set) -> bool:
        """Detect if we have a new batch of tool calls (new iteration).

        Since LangGraph doesn't stream tools in parallel, each new tool call ID
        that we haven't seen before indicates a new tool call batch.

        Args:
            current_tool_ids: Set of tool call IDs in current chunk

        Returns:
            True if we have new tool calls and existing completed ones
        """
        # If we have new tool call IDs that we haven't seen before
        # AND we have existing completed tool calls, it's a new batch
        if current_tool_ids and not current_tool_ids.intersection(self._seen_tool_ids):
            # Check if we have any completed tool calls to flush
            has_completed = any(state.status == ToolCallStatus.COMPLETE for state in self.state.tool_calls.values())
            return has_completed

        return False

    def _flush_completed_to_history(self):
        """Move completed tool calls from current iteration to history."""
        for idx, state in self.state.tool_calls.items():
            if state.status == ToolCallStatus.COMPLETE and state.parsed_args is not None:
                self.state.tool_call_history.append(
                    {
                        "id": state.id,
                        "name": state.name,
                        "args": state.parsed_args,
                        "type": "tool_call",
                        "iteration": self.state.current_iteration,
                        "global_index": self._global_tool_counter,
                    }
                )

        # Clear current tool calls for new iteration
        self.state.tool_calls.clear()
        self.state.current_iteration += 1

        if self.on_iteration_start:
            self.on_iteration_start(self.state.current_iteration)

    def process_chunk(self, chunk_message: BaseMessage) -> StreamingState:
        """Process a streaming chunk from LangGraph.

        Args:
            chunk_message: The streaming message chunk

        Returns:
            Current streaming state
        """
        if not isinstance(chunk_message, AIMessage):
            return self.state

        # Collect current tool IDs for batch detection
        current_tool_ids = set()

        # Extract tool IDs from tool_calls
        if hasattr(chunk_message, "tool_calls") and chunk_message.tool_calls:
            for tool_call in chunk_message.tool_calls:
                if tool_call.get("id"):
                    current_tool_ids.add(tool_call["id"])

        # Extract tool IDs from tool_call_chunks
        if hasattr(chunk_message, "tool_call_chunks") and getattr(chunk_message, "tool_call_chunks", None):
            for chunk in getattr(chunk_message, "tool_call_chunks", []):
                if chunk.get("id"):
                    current_tool_ids.add(chunk["id"])

        # Detect new tool call batch and flush if needed
        if self._detect_new_tool_call_batch(current_tool_ids):
            logger.info(f"🔄 New tool call batch detected! Moving to iteration {self.state.current_iteration + 1}")
            self._flush_completed_to_history()

        # Update tracking set
        self._seen_tool_ids.update(current_tool_ids)

        # Handle content updates
        content = getattr(chunk_message, "content", "")
        if content and isinstance(content, str) and content != self.state.content:
            self.state.content = content
            if self.on_content_update:
                self.on_content_update(self.state.content)

        # Handle initial tool calls (complete tool call info)
        if hasattr(chunk_message, "tool_calls") and chunk_message.tool_calls:
            for idx, tool_call in enumerate(chunk_message.tool_calls):
                if idx not in self.state.tool_calls:
                    # New tool call detected
                    self._global_tool_counter += 1
                    tool_state = ToolCallState(
                        id=tool_call.get("id"),
                        name=tool_call.get("name"),
                    )
                    self.state.tool_calls[idx] = tool_state

                    if self.on_tool_call_start:
                        self.on_tool_call_start(idx, tool_call.get("name") or "", tool_call.get("id") or "")

        # Handle tool call chunks (progressive argument building)
        tool_call_chunks = getattr(chunk_message, "tool_call_chunks", None)
        if tool_call_chunks:
            for chunk in tool_call_chunks:
                idx = chunk.get("index", 0)

                # Ensure we have a tool call state for this index
                if idx not in self.state.tool_calls:
                    # Create a new tool call state if we don't have one
                    self._global_tool_counter += 1
                    tool_state = ToolCallState(
                        id=chunk.get("id"),
                        name=chunk.get("name"),
                    )
                    self.state.tool_calls[idx] = tool_state

                    if self.on_tool_call_start and chunk.get("name"):
                        self.on_tool_call_start(idx, chunk.get("name", ""), chunk.get("id", ""))
                else:
                    tool_state = self.state.tool_calls[idx]

                # Update tool call information
                if chunk.get("name") and not tool_state.name:
                    tool_state.name = chunk["name"]
                if chunk.get("id") and not tool_state.id:
                    tool_state.id = chunk["id"]

                # Accumulate arguments
                if "args" in chunk and chunk["args"] is not None:
                    tool_state.accumulated_args += str(chunk["args"])

                    # Try to parse if it looks like complete JSON - this updates the status
                    was_complete = tool_state.status == ToolCallStatus.COMPLETE
                    tool_state.try_parse_args()

                    # Trigger callbacks
                    if self.on_tool_call_update:
                        self.on_tool_call_update(idx, tool_state)

                    # If tool call just completed, trigger completion callback
                    if not was_complete and tool_state.status == ToolCallStatus.COMPLETE:
                        if self.on_tool_call_complete:
                            self.on_tool_call_complete(idx, tool_state)

        return self.state

    def get_current_state(self) -> StreamingState:
        """Get the current streaming state."""
        return self.state

    def is_streaming_complete(self) -> bool:
        """Check if streaming appears to be complete."""
        # Consider streaming complete if we have tool calls and they're all complete or errored
        if not self.state.tool_calls:
            return False

        return all(
            state.status in [ToolCallStatus.COMPLETE, ToolCallStatus.ERROR] for state in self.state.tool_calls.values()
        )

    def get_final_tool_calls(self) -> List[Dict[str, Any]]:
        """Get final tool calls in LangChain format from all iterations."""
        return self.state.get_all_completed_tool_calls()


# Convenience functions for common use cases


def create_console_parser() -> StreamingGraphParser:
    """Create a parser that logs to console."""

    def on_content_update(content: str):
        print(f"💬 Content: {content}")

    def on_tool_call_start(idx: int, name: str, call_id: str):
        print(f"🔧 Tool Call {idx} Started: {name} (ID: {call_id})")

    def on_tool_call_update(idx: int, state: ToolCallState):
        if state.status == ToolCallStatus.BUILDING:
            preview = (
                state.accumulated_args[:50] + "..." if len(state.accumulated_args) > 50 else state.accumulated_args
            )
            print(f"🔄 Tool Call {idx} Building: {preview}")
        elif state.status == ToolCallStatus.ERROR:
            print(f"❌ Tool Call {idx} Error: {state.error_message}")

    def on_tool_call_complete(idx: int, state: ToolCallState):
        print(f"✅ Tool Call {idx} Complete: {state.name} with args {state.parsed_args}")

    def on_iteration_start(iteration: int):
        print(f"\n🔄 === New Tool Call Batch {iteration} Started ===")

    return StreamingGraphParser(
        on_content_update=on_content_update,
        on_tool_call_start=on_tool_call_start,
        on_tool_call_update=on_tool_call_update,
        on_tool_call_complete=on_tool_call_complete,
        on_iteration_start=on_iteration_start,
    )


def create_ui_parser(
    content_callback: Optional[Callable[[str], None]] = None,
    tool_start_callback: Optional[Callable[[int, str, str], None]] = None,
    tool_update_callback: Optional[Callable[[int, ToolCallState], None]] = None,
    tool_complete_callback: Optional[Callable[[int, ToolCallState], None]] = None,
) -> StreamingGraphParser:
    """Create a parser configured for UI integration."""
    return StreamingGraphParser(
        on_content_update=content_callback,
        on_tool_call_start=tool_start_callback,
        on_tool_call_update=tool_update_callback,
        on_tool_call_complete=tool_complete_callback,
    )
