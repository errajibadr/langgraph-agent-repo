"""Corrected channel-based streaming processor for LangGraph.

Proper separation of concerns:
1. Channel Streaming: Monitor state key changes (messages, notes, etc.) via values/updates
2. Token Streaming: Stream LLM output token-by-token from specific namespaces
3. Namespace handling: Support nested graph execution paths
"""

import asyncio
import logging
from dataclasses import KW_ONLY, dataclass, field
from enum import Enum
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional, Set

from langchain_core.messages import AIMessage, BaseMessage

logger = logging.getLogger(__name__)


class StreamMode(Enum):
    """Streaming modes for state channel monitoring."""

    VALUES_ONLY = "values"  # Stream full state values after node execution
    UPDATES_ONLY = "updates"  # Stream only state deltas/changes


@dataclass
class ChannelConfig:
    """Configuration for monitoring a state channel."""

    key: str  # State key to monitor (e.g., "messages", "notes", "questions")
    stream_mode: StreamMode = StreamMode.VALUES_ONLY
    artifact_type: Optional[str] = None  # Map to artifact type
    filter_fn: Optional[Callable[[Any], bool]] = None  # Custom filter


@dataclass
class TokenStreamingConfig:
    """Configuration for token-by-token streaming from namespaces."""

    enabled_namespaces: Set[str] = field(default_factory=lambda: {"main"})  # Which namespaces to stream tokens from
    message_tags: Optional[Set[str]] = None  # Filter by message tags (e.g., agent_name)


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


class ChannelStreamingProcessor:
    """Corrected channel-based streaming processor."""

    def __init__(
        self,
        channels: List[ChannelConfig],
        token_streaming: Optional[TokenStreamingConfig] = None,
        prefer_updates: bool = False,
    ):
        """
        Initialize the processor.

        Args:
            channels: List of state channels to monitor
            token_streaming: Configuration for token-by-token streaming from namespaces
            prefer_updates: Use "updates" mode instead of "values" for state streaming
        """
        self.channels = {config.key: config for config in channels}
        self.token_streaming = token_streaming or TokenStreamingConfig()
        self.prefer_updates = prefer_updates

        # State tracking
        self._previous_state: Dict[str, Any] = {}  # namespace:channel -> previous_value
        self._message_accumulators: Dict[str, str] = {}  # namespace:task_id -> accumulated content
        self._seen_message_ids: Set[str] = set()

    async def stream(
        self, graph, input_data: Dict[str, Any], config: Optional[Dict[str, Any]] = None, **kwargs
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        Stream from a LangGraph with separated channel and token streaming.

        Args:
            graph: The LangGraph to stream from
            input_data: Input data for the graph
            config: LangGraph config
            **kwargs: Additional arguments passed to graph.astream()
        """

        # Determine streaming configuration
        stream_modes = self._determine_stream_modes()

        async for raw_output in graph.astream(
            input_data,
            config=config,
            stream_mode=stream_modes,
            subgraphs=True,  # Always enable subgraphs for namespace support
            **kwargs,
        ):
            # Parse the raw output
            namespace, mode, chunk = self._parse_raw_output(raw_output, stream_modes)

            # Process based on mode and emit events
            async for event in self._process_chunk(namespace, mode, chunk):
                yield event

    def _determine_stream_modes(self) -> List[str]:
        """Determine which LangGraph stream modes we need."""
        modes = set()

        # Always need values or updates for channel monitoring
        if self.channels:
            modes.add("updates" if self.prefer_updates else "values")

        # Add messages mode if token streaming is enabled
        if self.token_streaming.enabled_namespaces:
            modes.add("messages")

        return list(modes)

    def _parse_raw_output(self, raw_output, stream_modes: List[str]) -> tuple[str, str, Any]:
        """Parse raw LangGraph output into (namespace, mode, chunk)."""

        # Case 1: Subgraphs enabled + multiple modes: (namespace_tuple, mode, chunk)
        if isinstance(raw_output, tuple) and len(raw_output) == 3:
            namespace_tuple, mode, chunk = raw_output
            namespace = self._format_namespace(namespace_tuple)
            return namespace, mode, chunk

        # Case 2: Two-element tuple - need to distinguish between cases
        elif isinstance(raw_output, tuple) and len(raw_output) == 2:
            first, second = raw_output

            # If first element is a string, it's (mode, chunk)
            if isinstance(first, str):
                mode, chunk = first, second
                namespace = "main"
                return namespace, mode, chunk

            # If first element is a Message, it's (message, metadata) from single "messages" mode
            elif isinstance(first, BaseMessage):
                chunk = (first, second)  # Keep as tuple for message processing
                mode = "messages"
                namespace = "main"
                return namespace, mode, chunk

            # If first element is a tuple (namespace), it's (namespace_tuple, chunk) for single mode
            elif isinstance(first, tuple):
                namespace_tuple, chunk = first, second
                namespace = self._format_namespace(namespace_tuple)
                # Determine mode from stream_modes (should be single mode)
                mode = stream_modes[0] if len(stream_modes) == 1 else "values"
                return namespace, mode, chunk

        # Case 3: Single chunk (single mode, no subgraphs)
        else:
            chunk = raw_output
            mode = stream_modes[0] if len(stream_modes) == 1 else "values"
            namespace = "main"
            return namespace, mode, chunk

    def _format_namespace(self, namespace_tuple: tuple) -> str:
        """
        Format namespace tuple into a string.

        Examples:
        - () -> "main"
        - ("parent_node:task_id",) -> "parent_node:task_id"
        - ("parent_node:task_id", "child_node:task_id") -> "parent_node:task_id:child_node:task_id"
        """
        if not namespace_tuple:
            return "main"
        return ":".join(str(part) for part in namespace_tuple)

    async def _process_chunk(self, namespace: str, mode: str, chunk: Any) -> AsyncGenerator[StreamEvent, None]:
        """Process a chunk and emit appropriate events."""

        if mode == "messages":
            # Token streaming from specific namespaces
            async for event in self._process_token_chunk(namespace, chunk):
                yield event
        elif mode == "values":
            # Channel value monitoring
            async for event in self._process_channel_values(namespace, chunk):
                yield event
        elif mode == "updates":
            # Channel update monitoring
            async for event in self._process_channel_updates(namespace, chunk):
                yield event

    async def _process_token_chunk(self, namespace: str, chunk: tuple) -> AsyncGenerator[TokenStreamEvent, None]:
        """Process message chunks for token-by-token streaming."""
        message, metadata = chunk

        # Check if this namespace should stream tokens
        if not self._should_stream_tokens_from_namespace(namespace):
            return

        # Check message tags filtering
        if self.token_streaming.message_tags:
            message_tags = set(metadata.get("tags", []))
            if not message_tags.intersection(self.token_streaming.message_tags):
                return

        # Handle AI message content streaming
        if isinstance(message, AIMessage) and hasattr(message, "content") and message.content:
            node_name, task_id = self._parse_namespace_components(namespace)
            accumulator_key = f"{namespace}:{task_id or 'default'}"

            # Accumulate content
            if accumulator_key not in self._message_accumulators:
                self._message_accumulators[accumulator_key] = ""

            self._message_accumulators[accumulator_key] += message.content

            yield TokenStreamEvent(
                namespace=namespace,
                content_delta=message.content,
                accumulated_content=self._message_accumulators[accumulator_key],
                message_id=getattr(message, "id", None),
                task_id=task_id,
                node_name=node_name,
            )

    def _should_stream_tokens_from_namespace(self, namespace: str) -> bool:
        """Check if we should stream tokens from this namespace."""
        # Extract the base namespace (first part before any task IDs)
        base_namespace = namespace.split(":")[0] if ":" in namespace else namespace
        return base_namespace in self.token_streaming.enabled_namespaces

    async def _process_channel_values(self, namespace: str, chunk: Dict[str, Any]) -> AsyncGenerator[StreamEvent, None]:
        """Process state values for channel monitoring."""

        for channel_key, config in self.channels.items():
            if channel_key not in chunk:
                continue

            current_value = chunk[channel_key]
            state_key = f"{namespace}:{channel_key}"
            previous_value = self._previous_state.get(state_key)

            # Skip if value hasn't changed
            if current_value == previous_value:
                continue

            # Update previous state
            self._previous_state[state_key] = current_value

            # Apply filter if configured
            if config.filter_fn and not config.filter_fn(current_value):
                continue

            # Calculate delta
            value_delta = self._calculate_delta(previous_value, current_value)

            # Extract components
            node_name, task_id = self._parse_namespace_components(namespace)

            # Create appropriate event
            if config.artifact_type:
                yield ArtifactEvent(
                    namespace=namespace,
                    channel=channel_key,
                    artifact_type=config.artifact_type,
                    artifact_data=current_value,
                    is_update=previous_value is not None,
                    task_id=task_id,
                    node_name=node_name,
                )
            else:
                yield ChannelValueEvent(
                    namespace=namespace,
                    channel=channel_key,
                    value=current_value,
                    value_delta=value_delta,
                    task_id=task_id,
                    node_name=node_name,
                )

    async def _process_channel_updates(
        self, namespace: str, chunk: Dict[str, Any]
    ) -> AsyncGenerator[StreamEvent, None]:
        """Process state updates for channel monitoring."""
        node_name, state_update = next(iter(chunk.items()))

        for channel_key, config in self.channels.items():
            if channel_key not in state_update:
                continue

            # Apply filter if configured
            update_value = state_update[channel_key]
            if config.filter_fn and not config.filter_fn(update_value):
                continue

            # Extract components
            _, task_id = self._parse_namespace_components(namespace)

            # Create appropriate event
            if config.artifact_type:
                yield ArtifactEvent(
                    namespace=namespace,
                    channel=channel_key,
                    artifact_type=config.artifact_type,
                    artifact_data=update_value,
                    is_update=True,
                    task_id=task_id,
                    node_name=node_name,
                )
            else:
                yield ChannelUpdateEvent(
                    namespace=namespace,
                    channel=channel_key,
                    node_name=node_name,
                    state_update={channel_key: update_value},  # Only this channel's update
                    task_id=task_id,
                )

    def _parse_namespace_components(self, namespace: str) -> tuple[str, Optional[str]]:
        """Parse namespace to extract node_name and task_id."""
        if namespace == "main":
            return "main", None

        # For nested namespaces like "parent:task_id:child:task_id"
        # Extract the last task_id and everything before it as node path
        parts = namespace.split(":")
        if len(parts) >= 2:
            # Assume last part might be task_id, everything else is node path
            # This is heuristic-based - might need refinement based on actual patterns
            return ":".join(parts[:-1]), parts[-1]

        return namespace, None

    def _calculate_delta(self, previous: Any, current: Any) -> Any:
        """Calculate delta between previous and current values."""
        if previous is None:
            return current

        # For lists, return new items
        if isinstance(current, list) and isinstance(previous, list):
            if len(current) > len(previous):
                return current[len(previous) :]

        # For dicts, return changed keys
        if isinstance(current, dict) and isinstance(previous, dict):
            delta = {}
            for key, value in current.items():
                if key not in previous or previous[key] != value:
                    delta[key] = value
            return delta if delta else None

        # For other types, return the new value if different
        return current if current != previous else None


# Convenience functions


def create_default_channels() -> List[ChannelConfig]:
    """Create default channel configuration."""
    return [
        ChannelConfig(key="messages", stream_mode=StreamMode.VALUES_ONLY),
        ChannelConfig(key="notes", artifact_type="Document"),
        ChannelConfig(key="questions", artifact_type="UserClarification"),
        ChannelConfig(key="artifacts", artifact_type="GeneratedArtifact"),
    ]


def create_simple_processor(
    token_namespaces: Optional[Set[str]] = None, prefer_updates: bool = False
) -> ChannelStreamingProcessor:
    """Create a simple processor with default configuration."""
    return ChannelStreamingProcessor(
        channels=create_default_channels(),
        token_streaming=TokenStreamingConfig(enabled_namespaces=token_namespaces or {"main"}),
        prefer_updates=prefer_updates,
    )


# Example usage
async def example_usage():
    """Example of the corrected approach."""

    # Separate channel and token streaming configuration
    channels = [
        # Monitor these state keys across all namespaces
        ChannelConfig(key="messages", stream_mode=StreamMode.VALUES_ONLY),
        ChannelConfig(key="supervisor_messages", stream_mode=StreamMode.UPDATES_ONLY),
        ChannelConfig(key="notes", artifact_type="Document", filter_fn=lambda x: x is not None and len(str(x)) > 5),
        ChannelConfig(key="questions", artifact_type="UserClarification"),
    ]

    # Token streaming from specific namespaces only
    token_config = TokenStreamingConfig(
        enabled_namespaces={"main", "clarify"},  # Only stream tokens from these namespaces
        message_tags={"agent_name"},  # Filter by agent tags
    )

    processor = ChannelStreamingProcessor(channels=channels, token_streaming=token_config, prefer_updates=True)

    # Usage remains the same
    # async for event in processor.stream(graph, input_data):
    #     if isinstance(event, TokenStreamEvent):
    #         print(f"[{event.namespace}] Token: {event.content_delta}")
    #     elif isinstance(event, ArtifactEvent):
    #         print(f"[{event.namespace}] Artifact: {event.artifact_data}")
    #     elif isinstance(event, ChannelValueEvent):
    #         print(f"[{event.namespace}] Channel {event.channel}: {event.value}")
    #     elif isinstance(event, ChannelUpdateEvent):
    #         print(f"[{event.namespace}] Update from {event.node_name}: {event.state_update}")
