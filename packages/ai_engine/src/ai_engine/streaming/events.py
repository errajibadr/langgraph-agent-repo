"""Streaming event definitions.

All event types for the streaming system, including:
- Base events
- Token streaming events
- Channel monitoring events
- Tool call streaming events
"""

import asyncio
from dataclasses import KW_ONLY, dataclass, field
from typing import Any, Dict, Literal, Optional

from langchain_core.messages import BaseMessage


@dataclass
class StreamEvent:
    """Base streaming event."""

    namespace: str  # Which namespace/subgraph this came from
    _: KW_ONLY
    timestamp: float = field(default_factory=lambda: asyncio.get_event_loop().time())
    task_id: Optional[str] = field(default=None)  # For parallel subgraph separation


@dataclass
class TokenStreamEvent(StreamEvent):
    """Token-by-token LLM output streaming."""

    content_delta: str  # New content chunk
    accumulated_content: str  # Full content so far
    message_id: Optional[str] = field(default=None)
    node_name: Optional[str] = field(default=None)  # Node that generated this token
    message: Optional[BaseMessage] = field(default=None)  # Full message for context


@dataclass
class ChannelValueEvent(StreamEvent):
    """State channel value update."""

    channel: str  # State channel key
    value: Any  # The actual state value
    value_delta: Optional[Any] = field(default=None)  # Change from previous value
    node_name: Optional[str] = field(default=None)  # Node that updated this value


@dataclass
class ChannelUpdateEvent(StreamEvent):
    """State channel update/delta."""

    channel: str  # State channel key
    node_name: str  # Node that made the update
    state_update: Dict[str, Any]  # The state delta for this channel


@dataclass
class ArtifactEvent(StreamEvent):
    """Artifact creation/update from state channel."""

    channel: str  # Source state channel
    artifact_type: str  # Document, UserClarification, etc.
    artifact_data: Any  # The artifact content
    is_update: bool = field(default=False)  # True if updating existing artifact
    node_name: Optional[str] = field(default=None)


# Tool Call Streaming Events
# Integrates with the documented tool call streaming pattern


@dataclass
class MessageReceivedEvent(StreamEvent):
    """Complete message received from channel with deduplication info.

    This event is emitted when a complete message appears in a channel
    (like "messages" state). It includes deduplication information to
    indicate if this message was already processed via token streaming.
    """

    message: BaseMessage  # The complete message
    was_streamed: bool  # True if already processed via token streaming
    has_tool_calls: bool  # Whether message contains tool calls
    tool_call_ids: list[str] = field(default_factory=list)  # Tool call IDs if present
    source: str = field(default="channel")  # Source: "channel" vs "stream"
    message_type: str = field(default="")  # "ai", "tool", "human", etc.

    @property
    def id(self) -> str:
        return self.message.id or ""


@dataclass
class ToolCallEvent:
    """Tool call lifecycle events."""

    tool_name: str
    namespace: str
    task_id: str | None
    tool_call_id: str
    message_id: str
    index: int
    status: Literal[
        "started_streaming",
        "args_streaming",
        "completed_streaming",
        "error_streaming",
        "result_received",
        "result_error",
    ]
    args: dict[str, Any] | None = None  # Tool call arguments
    args_delta: str = field(default="")
    args_accumulated: str = field(default="")
    result: Optional[Any] = None
    error: Optional[str] = None


@dataclass
class ToolCallStartedStreamEvent(StreamEvent):
    """Tool call started - first message with complete metadata."""

    tool_call_id: str  # From first message
    tool_name: str  # From first message
    index: int  # Tool call index
    message_id: str  # Message ID for linking chunks


@dataclass
class ToolCallProgressStreamEvent(StreamEvent):
    """Tool call argument streaming progress."""

    tool_call_id: str  # Tool call identifier
    args_delta: str  # New argument chunk
    accumulated_args: str  # Full args accumulated so far
    is_valid_json: bool  # Whether accumulated args parse as JSON
    index: int  # Tool call index
    message_id: str  # Message ID for linking


@dataclass
class ToolCallCompletedStreamEvent(StreamEvent):
    """Tool call completed with final parsed arguments."""

    tool_call_id: str  # Tool call identifier
    tool_name: str  # Tool name
    final_args: str  # Complete JSON string
    parsed_args: Dict[str, Any]  # Parsed arguments
    index: int  # Tool call index
    message_id: str  # Message ID


@dataclass
class ToolCallErrorEvent(StreamEvent):
    """Tool call encountered an error during streaming."""

    tool_call_id: Optional[str] = field(default=None)  # May not have ID if error early
    tool_name: Optional[str] = field(default=None)  # May not have name
    error_message: str = ""  # Error description
    accumulated_args: str = ""  # Args accumulated before error
    index: int = 0  # Tool call index
    message_id: Optional[str] = field(default=None)  # Message ID if available
