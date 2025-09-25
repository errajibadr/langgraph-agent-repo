"""Convenience factory functions for common streaming configurations.

Provides easy-to-use factory functions that create commonly used
streaming processor configurations without requiring detailed setup.
"""

from typing import Optional, Set

from .config import ChannelConfig, StreamMode, TokenStreamingConfig
from .processor import ChannelStreamingProcessor


def create_default_channels() -> list[ChannelConfig]:
    """Create default channel configuration for common use cases.

    Returns:
        List of channel configs for messages, notes, questions, and artifacts
    """
    return [
        ChannelConfig(key="messages", stream_mode=StreamMode.VALUES_ONLY),
        ChannelConfig(key="notes", artifact_type="Document"),
        ChannelConfig(key="questions", artifact_type="UserClarification"),
        ChannelConfig(key="artifacts", artifact_type="GeneratedArtifact"),
    ]


def create_simple_processor(
    token_namespaces: Optional[Set[str]] = None,
    prefer_updates: bool = False,
    include_tool_calls: bool = False,
) -> ChannelStreamingProcessor:
    """Create a simple processor with sensible defaults.

    Args:
        token_namespaces: Namespaces to stream tokens from (defaults to {"main"})
        prefer_updates: Use updates mode instead of values for performance
        include_tool_calls: Enable tool call streaming events

    Returns:
        Configured ChannelStreamingProcessor
    """
    return ChannelStreamingProcessor(
        channels=create_default_channels(),
        token_streaming=TokenStreamingConfig(
            enabled_namespaces=token_namespaces or {"main"},
            include_tool_calls=include_tool_calls,
        ),
        prefer_updates=prefer_updates,
    )


def create_message_only_processor(
    token_namespaces: Optional[Set[str]] = None,
    include_tool_calls: bool = False,
) -> ChannelStreamingProcessor:
    """Create processor that only monitors the messages channel.

    Lightweight option when you only need basic message streaming.

    Args:
        token_namespaces: Namespaces to stream tokens from
        include_tool_calls: Enable tool call streaming

    Returns:
        Configured ChannelStreamingProcessor
    """
    return ChannelStreamingProcessor(
        channels=[ChannelConfig(key="messages", stream_mode=StreamMode.VALUES_ONLY)],
        token_streaming=TokenStreamingConfig(
            enabled_namespaces=token_namespaces or {"main"},
            include_tool_calls=include_tool_calls,
        ),
    )


def create_artifact_processor(
    artifact_channels: Optional[dict[str, str]] = None,
    token_namespaces: Optional[Set[str]] = None,
    include_tool_calls: bool = False,
) -> ChannelStreamingProcessor:
    """Create processor optimized for artifact-based streaming.

    Args:
        artifact_channels: Dict of channel_key -> artifact_type mappings
        token_namespaces: Namespaces to stream tokens from
        include_tool_calls: Enable tool call streaming

    Returns:
        Configured ChannelStreamingProcessor with artifact mappings
    """
    # Default artifact channels
    if artifact_channels is None:
        artifact_channels = {
            "notes": "Document",
            "questions": "UserClarification",
            "artifacts": "GeneratedArtifact",
            "documents": "Document",
            "clarifications": "UserClarification",
        }

    # Create channel configs with artifact mappings
    channels = [ChannelConfig(key="messages", stream_mode=StreamMode.VALUES_ONLY)]

    for channel_key, artifact_type in artifact_channels.items():
        channels.append(ChannelConfig(key=channel_key, artifact_type=artifact_type))

    return ChannelStreamingProcessor(
        channels=channels,
        token_streaming=TokenStreamingConfig(
            enabled_namespaces=token_namespaces or {"main"},
            include_tool_calls=include_tool_calls,
        ),
    )


def create_multi_agent_processor(
    agent_namespaces: Set[str],
    include_tool_calls: bool = True,
    prefer_updates: bool = True,
) -> ChannelStreamingProcessor:
    """Create processor optimized for multi-agent scenarios.

    Args:
        agent_namespaces: Set of agent/namespace names to stream from
        include_tool_calls: Enable tool call streaming (recommended for agents)
        prefer_updates: Use updates mode for better performance with many agents

    Returns:
        Configured ChannelStreamingProcessor for multi-agent streaming
    """
    return ChannelStreamingProcessor(
        channels=[
            ChannelConfig(key="messages", stream_mode=StreamMode.VALUES_ONLY),
            ChannelConfig(key="supervisor_messages", stream_mode=StreamMode.UPDATES_ONLY),
            ChannelConfig(key="notes", artifact_type="Document"),
            ChannelConfig(key="questions", artifact_type="UserClarification"),
            ChannelConfig(key="artifacts", artifact_type="GeneratedArtifact"),
        ],
        token_streaming=TokenStreamingConfig(
            enabled_namespaces=agent_namespaces,
            include_tool_calls=include_tool_calls,
        ),
        prefer_updates=prefer_updates,
    )


def create_performance_optimized_processor(
    monitored_channels: list[str],
    token_namespaces: Set[str],
    include_tool_calls: bool = False,
) -> ChannelStreamingProcessor:
    """Create processor optimized for performance with minimal overhead.

    Uses updates-only mode and minimal channel monitoring for high-throughput scenarios.

    Args:
        monitored_channels: List of channels to monitor (minimal set recommended)
        token_namespaces: Namespaces to stream tokens from
        include_tool_calls: Enable tool call streaming (adds overhead)

    Returns:
        Performance-optimized ChannelStreamingProcessor
    """
    channels = [ChannelConfig(key=channel, stream_mode=StreamMode.UPDATES_ONLY) for channel in monitored_channels]

    return ChannelStreamingProcessor(
        channels=channels,
        token_streaming=TokenStreamingConfig(
            enabled_namespaces=token_namespaces,
            include_tool_calls=include_tool_calls,
        ),
        prefer_updates=True,  # Always use updates for performance
    )


def create_debug_processor(
    include_all_channels: bool = True,
    token_namespaces: Optional[Set[str]] = None,
) -> ChannelStreamingProcessor:
    """Create processor for debugging with extensive monitoring.

    Monitors many common channels and includes tool call streaming for full visibility.
    Not recommended for production due to overhead.

    Args:
        include_all_channels: Monitor all common channels
        token_namespaces: Namespaces to stream tokens from

    Returns:
        Debug-oriented ChannelStreamingProcessor
    """
    if include_all_channels:
        channels = [
            ChannelConfig(key="messages", stream_mode=StreamMode.VALUES_ONLY),
            ChannelConfig(key="supervisor_messages", stream_mode=StreamMode.VALUES_ONLY),
            ChannelConfig(key="notes", artifact_type="Document"),
            ChannelConfig(key="questions", artifact_type="UserClarification"),
            ChannelConfig(key="artifacts", artifact_type="GeneratedArtifact"),
            ChannelConfig(key="documents", artifact_type="Document"),
            ChannelConfig(key="clarifications", artifact_type="UserClarification"),
            ChannelConfig(key="state", stream_mode=StreamMode.VALUES_ONLY),
            ChannelConfig(key="metadata", stream_mode=StreamMode.VALUES_ONLY),
        ]
    else:
        channels = create_default_channels()

    return ChannelStreamingProcessor(
        channels=channels,
        token_streaming=TokenStreamingConfig(
            enabled_namespaces=token_namespaces or {"main"},
            include_tool_calls=True,  # Always include for debugging
        ),
        prefer_updates=False,  # Use values for full state visibility
    )
