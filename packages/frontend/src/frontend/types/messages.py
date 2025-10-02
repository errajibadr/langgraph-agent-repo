"""Type definitions for chat messages and artifacts.

Provides type-safe structures for the streaming chat architecture.
"""

from datetime import datetime
from typing import Any, Literal, NotRequired, TypedDict

# ============================================================================
# ARTIFACT DATA TYPES
# ============================================================================


class ArtifactData(TypedDict):
    """Base artifact data structure."""

    id: str
    type: Literal["generic", "followup", "notes"]
    data: dict[str, Any]
    namespace: str
    timestamp: str


class GenericArtifactData(TypedDict):
    """Generic artifact with title and description."""

    id: str
    type: Literal["generic"]
    title: str
    description: str


class FollowupArtifactData(TypedDict):
    """Followup/question artifact with clickable value."""

    id: str
    type: Literal["followup"]
    title: str
    description: str
    value: str  # The value to send back when clicked


class NotesArtifactData(TypedDict):
    """Notes artifact with content."""

    id: str
    type: Literal["notes"]
    title: str
    description: str
    content: NotRequired[str]


# ============================================================================
# CHAT MESSAGE TYPES
# ============================================================================


class BaseMessage(TypedDict):
    """Base message structure."""

    namespace: str
    timestamp: str


class UserMessage(BaseMessage):
    """User message in chat."""

    id: str
    role: Literal["user"]
    content: str


class AIMessage(BaseMessage):
    """AI assistant message in chat."""

    id: str
    role: Literal["ai"]
    content: str
    artifacts: NotRequired[list[ArtifactData]]  # Inline artifacts


class ToolCallMessage(BaseMessage):
    """Tool call/execution message."""

    message_id: str  # Message id where we detected the ToolCall
    tool_call_id: str
    role: Literal["tool_call"]
    name: str
    status: Literal["invoked", "result_success", "result_error"]
    args: NotRequired[dict[str, Any]]
    result: NotRequired[dict[str, Any]]


class ArtifactMessage(BaseMessage):
    """Standalone artifact message (when no AI message to attach to)."""

    id: str
    role: Literal["artifact"]
    artifacts: list[ArtifactData]  # Use same structure as AIMessage


# Union type for all message types
ChatMessage = UserMessage | AIMessage | ToolCallMessage | ArtifactMessage
