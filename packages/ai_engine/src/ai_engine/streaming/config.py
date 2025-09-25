"""Streaming configuration classes and enums.

Defines how streaming should behave:
- Stream modes for channel monitoring
- Channel configuration for state monitoring
- Token streaming configuration for LLM output
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional, Set


class StreamMode(Enum):
    """Streaming modes for state channel monitoring."""

    VALUES_ONLY = "values"  # Stream full state values after node execution
    UPDATES_ONLY = "updates"  # Stream only state deltas/changes


@dataclass
class ChannelConfig:
    """Configuration for monitoring a state channel.

    A channel represents a key in the LangGraph state (e.g., "messages", "notes").
    This configures how that channel should be monitored and streamed.
    """

    key: str  # State key to monitor (e.g., "messages", "notes", "questions")
    stream_mode: StreamMode = StreamMode.VALUES_ONLY  # How to stream this channel
    artifact_type: Optional[str] = None  # Map to artifact type for UI display
    filter_fn: Optional[Callable[[Any], bool]] = None  # Custom filter for values

    def __post_init__(self):
        """Validate configuration."""
        if not self.key:
            raise ValueError("Channel key cannot be empty")

        if self.artifact_type and not isinstance(self.artifact_type, str):
            raise ValueError("artifact_type must be a string if provided")


@dataclass
class TokenStreamingConfig:
    """Configuration for token-by-token streaming from namespaces.

    Controls which namespaces should stream LLM output token-by-token,
    and optionally includes tool call streaming.
    """

    enabled_namespaces: Set[str] = field(default_factory=lambda: {"main"})  # Namespaces to stream from
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
            # Default to monitoring messages
            self.channels = [ChannelConfig(key="messages")]

        if self.token_streaming is None:
            self.token_streaming = TokenStreamingConfig()


# Convenience functions for common configurations


def create_message_only_config() -> StreamingConfig:
    """Create config that only monitors the messages channel."""
    return StreamingConfig(
        channels=[ChannelConfig(key="messages", stream_mode=StreamMode.VALUES_ONLY)],
        token_streaming=TokenStreamingConfig(enabled_namespaces={"main"}),
    )


def create_artifact_config() -> StreamingConfig:
    """Create config for artifact-based streaming."""
    return StreamingConfig(
        channels=[
            ChannelConfig(key="messages", stream_mode=StreamMode.VALUES_ONLY),
            ChannelConfig(key="notes", artifact_type="Document"),
            ChannelConfig(key="questions", artifact_type="UserClarification"),
            ChannelConfig(key="artifacts", artifact_type="GeneratedArtifact"),
        ],
        token_streaming=TokenStreamingConfig(enabled_namespaces={"main"}),
    )
