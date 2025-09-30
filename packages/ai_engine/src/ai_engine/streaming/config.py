"""Streaming configuration classes and enums.

Defines how streaming should behave:
- Stream modes for channel monitoring
- Channel configuration for state monitoring
- Token streaming configuration for LLM output
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Literal, Optional, Set


class StreamMode(Enum):
    """Streaming modes for state channel monitoring."""

    VALUES_ONLY = "values"  # Stream full state values after node execution
    # UPDATES_ONLY = "updates"  # Stream only state deltas/changes


class ChannelType(Enum):
    """Type of a monitored channel.

    - MESSAGE: Channel contains BaseMessage objects (list or single). These are
      processed as whole messages (no token chunks) and can produce tool call
      lifecycle events when AI messages contain tool calls or when Tool messages
      contain tool results.
    - ARTIFACT: Channel represents artifacts/documents; values are emitted as
      ArtifactEvent. `artifact_type` must be provided.
    - GENERIC: Any other channel. Values/updates are emitted as ChannelValueEvent
      or ChannelUpdateEvent respectively.
    """

    MESSAGE = "message"
    ARTIFACT = "artifact"
    GENERIC = "generic"


@dataclass
class ChannelConfig:
    """Configuration for monitoring a state channel.

    A channel represents a key in the LangGraph state (e.g., "messages", "notes").
    This configures how that channel should be monitored and streamed.

    Notes:
    - Prefer setting `channel_type=ChannelType.MESSAGE` for message channels
      (e.g., `messages`, `supervisor_messages`, `internal_messages`).
    - For artifact channels, set `channel_type=ChannelType.ARTIFACT` and provide
      an `artifact_type` string to describe the artifact class for the UI.
    - The legacy `parse_messages` flag is deprecated. If present and True while
      `channel_type` is not explicitly set, it will be treated as a MESSAGE
      channel for backward compatibility.
    """

    key: str  # State key to monitor (e.g., "messages", "notes", "questions")
    stream_mode: StreamMode = StreamMode.VALUES_ONLY  # How to stream this channel
    channel_type: ChannelType = ChannelType.GENERIC  # Channel semantics
    artifact_type: str = "generic"  # Map to artifact type for UI display
    filter_fn: Optional[Callable[[Any], bool]] = None  # Custom filter for values
    # DEPRECATED: use channel_type=ChannelType.MESSAGE instead
    parse_messages: Optional[bool] = None  # kept for backward compatibility

    def __post_init__(self):
        """Validate configuration and apply backward-compatibility rules."""
        if not self.key:
            raise ValueError("Channel key cannot be empty")

        if self.channel_type == ChannelType.ARTIFACT and self.artifact_type == "generic":
            raise ValueError("artifact_type must be provided for artifact channels")

        if self.artifact_type and not isinstance(self.artifact_type, str):
            raise ValueError("artifact_type must be a string if provided")

        # Back-compat: if parse_messages is True and channel_type was not set
        # explicitly by caller (left to default GENERIC), treat as MESSAGE.
        if self.parse_messages is True and self.channel_type == ChannelType.GENERIC:
            self.channel_type = ChannelType.MESSAGE

        self.artifact_type = self.artifact_type.lower()
        self.key = self.key.lower()


@dataclass
class TokenStreamingConfig:
    """Configuration for token-by-token streaming from namespaces.

    Controls which namespaces should stream LLM output token-by-token,
    and optionally includes tool call streaming.
    """

    enabled_namespaces: Set[str | Literal["main", "all"]] = field(
        default_factory=lambda: {"main"}
    )  # Namespaces to stream from
    exclude_namespaces: Set[str | Literal["main", "all"]] = field(
        default_factory=lambda: set()
    )  # Namespaces to exclude from streaming
    message_tags: Optional[Set[str]] = None  # Filter by message tags (e.g., agent_name)
    include_tool_calls: bool = False  # Enable tool call streaming events

    def __post_init__(self):
        """Validate configuration."""
        if not self.enabled_namespaces:
            raise ValueError("At least one namespace must be enabled for token streaming")

        # Ensure namespaces is a set
        if isinstance(self.enabled_namespaces, (list, tuple)):
            self.enabled_namespaces = set(self.enabled_namespaces)

        # Ensure message_tags is a set if provided
        if self.message_tags and isinstance(self.message_tags, (list, tuple)):
            self.message_tags = set(self.message_tags)


@dataclass
class StreamingConfig:
    """Complete streaming configuration.

    Combines channel monitoring and token streaming configuration
    into a single configuration object.
    """

    channels: list[ChannelConfig] = field(default_factory=list)
    token_streaming: Optional[TokenStreamingConfig] = None
    prefer_updates: bool = False  # Use "updates" mode instead of "values" by default

    def __post_init__(self):
        """Set defaults if needed."""
        if not self.channels:
            # Default to monitoring messages channel as message-type
            self.channels = [
                ChannelConfig(key="messages", stream_mode=StreamMode.VALUES_ONLY, channel_type=ChannelType.MESSAGE)
            ]

        if self.token_streaming is None:
            self.token_streaming = TokenStreamingConfig()


# Convenience functions for common configurations


def create_message_only_config() -> StreamingConfig:
    """Create config that only monitors the messages channel as MESSAGE type."""
    return StreamingConfig(
        channels=[ChannelConfig(key="messages", stream_mode=StreamMode.VALUES_ONLY, channel_type=ChannelType.MESSAGE)],
        token_streaming=TokenStreamingConfig(enabled_namespaces={"main"}),
    )


def create_artifact_config() -> StreamingConfig:
    """Create config for artifact-based streaming."""
    return StreamingConfig(
        channels=[
            ChannelConfig(key="messages", stream_mode=StreamMode.VALUES_ONLY, channel_type=ChannelType.MESSAGE),
            ChannelConfig(key="notes", channel_type=ChannelType.ARTIFACT, artifact_type="Document"),
            ChannelConfig(key="questions", channel_type=ChannelType.ARTIFACT, artifact_type="UserClarification"),
            ChannelConfig(key="artifacts", channel_type=ChannelType.ARTIFACT, artifact_type="GeneratedArtifact"),
        ],
        token_streaming=TokenStreamingConfig(enabled_namespaces={"main"}),
    )
