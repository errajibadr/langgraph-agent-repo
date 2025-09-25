"""Channel-based streaming processor for LangGraph.

A simplified approach to handling LangGraph streaming that focuses on:
1. Channel-based state streaming (messages, notes, artifacts, etc.)
2. Namespace-aware token streaming
3. Artifact mapping from state keys
4. Task ID separation for parallel subgraphs
"""

import asyncio
import logging
from dataclasses import KW_ONLY, dataclass, field
from enum import Enum
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional, Set, Union

from langchain_core.messages import AIMessage, BaseMessage, ToolMessage

logger = logging.getLogger(__name__)


class StreamMode(Enum):
    """Streaming modes for different content types."""

    TOKEN_BY_TOKEN = "token"  # Stream message content token by token
    VALUES_ONLY = "values"  # Only stream final state values (full state after node)
    UPDATES_ONLY = "updates"  # Only stream state deltas/changes
    BOTH = "both"  # Stream both tokens and values/updates


@dataclass
class ChannelConfig:
    """Configuration for a streaming channel."""

    key: str  # State key to monitor
    stream_mode: StreamMode = StreamMode.VALUES_ONLY
    namespaces: Set[str] = field(default_factory=lambda: {"main"})  # Which namespaces to stream from
    artifact_type: Optional[str] = None  # Map to artifact type
    filter_fn: Optional[Callable[[Any], bool]] = None  # Custom filter
    message_tags: Optional[Set[str]] = None  # Filter token streaming by message tags (e.g., agent_name)


@dataclass
class StreamEvent:
    """Base streaming event."""

    namespace: str  # Which namespace/subgraph this came from
    channel: str  # Which state channel
    _: KW_ONLY
    timestamp: float = field(default_factory=lambda: asyncio.get_event_loop().time())
    task_id: Optional[str] = field(default=None)  # For parallel subgraph separation


@dataclass
class TokenStreamEvent(StreamEvent):
    """Token-by-token content streaming."""

    content_delta: str = field()  # New content chunk
    accumulated_content: str = field()  # Full content so far
    message_id: Optional[str] = field(default=None)
    node_name: Optional[str] = field(default=None)  # Node that generated this token


@dataclass
class ValueStreamEvent(StreamEvent):
    """State value update."""

    value: Any  # The actual state value
    value_delta: Optional[Any] = field(default=None)  # Change from previous value
    node_name: Optional[str] = field(default=None)  # Node that updated this value


@dataclass
class UpdateStreamEvent(StreamEvent):
    """State update/delta event."""

    node_name: str  # Node that made the update
    state_update: Dict[str, Any]  # The state delta


@dataclass
class ArtifactStreamEvent(StreamEvent):
    """Artifact creation/update event."""

    artifact_type: str  # Document, UserClarification, etc.
    artifact_data: Any  # The artifact content
    is_update: bool = field(default=False)  # True if updating existing artifact
    node_name: Optional[str] = field(default=None)  # Node that created/updated this artifact


class ChannelStreamingProcessor:
    """Simplified channel-based streaming processor."""

    def __init__(
        self,
        channels: List[ChannelConfig],
        default_token_namespaces: Optional[Set[str]] = None,
        prefer_updates: bool = False,
    ):
        """
        Initialize the processor.

        Args:
            channels: List of channel configurations to monitor
            default_token_namespaces: Namespaces to stream token-by-token by default
            prefer_updates: Use "updates" mode instead of "values" for state streaming
        """
        self.channels = {config.key: config for config in channels}
        self.default_token_namespaces = default_token_namespaces or {"main"}
        self.prefer_updates = prefer_updates

        # State tracking
        self._previous_state: Dict[str, Any] = {}
        self._message_accumulators: Dict[str, str] = {}  # namespace:task_id -> accumulated content
        self._seen_message_ids: Set[str] = set()

    async def stream(
        self, graph, input_data: Dict[str, Any], config: Optional[Dict[str, Any]] = None, **kwargs
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        Stream from a LangGraph with channel-based processing.

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

        # Check what modes we need based on channel configurations
        for config in self.channels.values():
            if config.stream_mode == StreamMode.TOKEN_BY_TOKEN:
                modes.add("messages")
            elif config.stream_mode == StreamMode.VALUES_ONLY:
                modes.add("values")
            elif config.stream_mode == StreamMode.UPDATES_ONLY:
                modes.add("updates")
            elif config.stream_mode == StreamMode.BOTH:
                modes.add("messages")
                modes.add("updates" if self.prefer_updates else "values")

        # Default to values if no specific modes requested
        if not modes:
            modes.add("values")

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
        """Format namespace tuple into a string."""
        if not namespace_tuple:
            return "main"
        return ":".join(str(part) for part in namespace_tuple)

    async def _process_chunk(self, namespace: str, mode: str, chunk: Any) -> AsyncGenerator[StreamEvent, None]:
        """Process a chunk and emit appropriate events."""

        if mode == "messages":
            async for event in self._process_message_chunk(namespace, chunk):
                yield event
        elif mode == "values":
            async for event in self._process_values_chunk(namespace, chunk):
                yield event
        elif mode == "updates":
            async for event in self._process_updates_chunk(namespace, chunk):
                yield event

    async def _process_message_chunk(self, namespace: str, chunk: tuple) -> AsyncGenerator[StreamEvent, None]:
        """Process message chunks for token-by-token streaming."""
        message, metadata = chunk

        # Extract node name and task ID from namespace
        # Format: "node_name:task_id" or just "node_name"
        node_name, task_id = self._parse_namespace_for_messages(namespace)

        # Check if this channel/namespace should stream tokens
        should_stream_tokens = any(
            node_name in config.namespaces and config.stream_mode in (StreamMode.TOKEN_BY_TOKEN, StreamMode.BOTH)
            for config in self.channels.values()
            if config.key == "messages"  # Only check message channels
        )

        if not should_stream_tokens:
            return

        # Check message tags filtering
        message_config = self.channels.get("messages")
        if message_config and message_config.message_tags:
            # Check if message has required tags in metadata
            message_tags = set(metadata.get("tags", []))
            if not message_tags.intersection(message_config.message_tags):
                return

        # Handle AI message content streaming
        if isinstance(message, AIMessage) and hasattr(message, "content") and message.content:
            accumulator_key = f"{node_name}:{task_id or 'default'}"

            # Accumulate content
            if accumulator_key not in self._message_accumulators:
                self._message_accumulators[accumulator_key] = ""

            self._message_accumulators[accumulator_key] += message.content

            yield TokenStreamEvent(
                namespace=namespace,
                channel="messages",  # Channel is always "messages" for token streaming
                content_delta=message.content,
                accumulated_content=self._message_accumulators[accumulator_key],
                message_id=getattr(message, "id", None),
                task_id=task_id,
                node_name=node_name,
            )

    def _parse_namespace_for_messages(self, namespace: str) -> tuple[str, Optional[str]]:
        """Parse namespace for messages to extract node_name and task_id."""
        if namespace == "main":
            return "main", None

        # Format: "node_name:task_id"
        if ":" in namespace:
            parts = namespace.split(":")
            node_name = parts[0]
            task_id = parts[1] if len(parts) > 1 else None
            return node_name, task_id

        return namespace, None

    async def _process_values_chunk(self, namespace: str, chunk: Dict[str, Any]) -> AsyncGenerator[StreamEvent, None]:
        """Process state values chunk."""

        for channel_key, config in self.channels.items():
            if channel_key not in chunk:
                continue

            # Check if this namespace is relevant for this channel
            if namespace not in config.namespaces:
                continue

            current_value = chunk[channel_key]  # TODO: KEEP HARD fail ? or silent fail with .get() ?
            previous_value = self._previous_state.get(f"{namespace}:{channel_key}")

            # Skip if value hasn't changed
            if current_value == previous_value:
                continue

            # Update previous state
            self._previous_state[f"{namespace}:{channel_key}"] = current_value

            # Apply filter if configured
            if config.filter_fn and not config.filter_fn(current_value):
                continue

            # Determine value delta
            value_delta = self._calculate_delta(previous_value, current_value)

            # Extract task ID and node name
            node_name, task_id = self._parse_namespace_for_values(namespace)

            # Create appropriate event
            if config.artifact_type:
                yield ArtifactStreamEvent(
                    namespace=namespace,
                    channel=channel_key,
                    artifact_type=config.artifact_type,
                    artifact_data=current_value,
                    is_update=previous_value is not None,
                    task_id=task_id,
                    node_name=node_name,
                )
            else:
                yield ValueStreamEvent(
                    namespace=namespace,
                    channel=channel_key,
                    value=current_value,
                    value_delta=value_delta,
                    task_id=task_id,
                    node_name=node_name,
                )

    async def _process_updates_chunk(self, namespace: str, chunk: dict) -> AsyncGenerator[StreamEvent, None]:
        """Process state updates chunk."""
        node_name, state_update = next(iter(chunk.items()))

        # Check if any channels are interested in updates from this namespace
        for channel_key, config in self.channels.items():
            if config.stream_mode not in (StreamMode.UPDATES_ONLY, StreamMode.BOTH):
                continue

            if namespace not in config.namespaces:
                continue

            # Check if this update contains the channel we're monitoring
            if channel_key not in state_update:
                continue

            # Apply filter if configured
            update_value = state_update[channel_key]
            if config.filter_fn and not config.filter_fn(update_value):
                continue

            # Extract task ID
            _, task_id = self._parse_namespace_for_values(namespace)

            # Create appropriate event
            if config.artifact_type:
                yield ArtifactStreamEvent(
                    namespace=namespace,
                    channel=channel_key,
                    artifact_type=config.artifact_type,
                    artifact_data=update_value,
                    is_update=True,
                    task_id=task_id,
                    node_name=node_name,
                )
            else:
                yield UpdateStreamEvent(
                    namespace=namespace,
                    channel=channel_key,
                    node_name=node_name,
                    state_update=state_update,
                    task_id=task_id,
                )

    def _parse_namespace_for_values(self, namespace: str) -> tuple[str, Optional[str]]:
        """Parse namespace for values/updates to extract node_name and task_id."""
        if namespace == "main":
            return "main", None

        # For values/updates, namespace might be just the node name or include task ID
        if ":" in namespace:
            parts = namespace.split(":")
            # Last part is usually task ID, everything before is node path
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


# Convenience functions for common configurations


def create_default_channels() -> List[ChannelConfig]:
    """Create default channel configuration for typical LangGraph usage."""
    return [
        ChannelConfig(
            key="messages",
            stream_mode=StreamMode.TOKEN_BY_TOKEN,
            namespaces={"main"},  # Only main namespace by default
        ),
        ChannelConfig(key="notes", stream_mode=StreamMode.VALUES_ONLY, artifact_type="Document"),
        ChannelConfig(key="questions", stream_mode=StreamMode.VALUES_ONLY, artifact_type="UserClarification"),
        ChannelConfig(key="artifacts", stream_mode=StreamMode.VALUES_ONLY, artifact_type="GeneratedArtifact"),
    ]


def create_simple_processor(prefer_updates: bool = False) -> ChannelStreamingProcessor:
    """Create a simple processor with default configuration."""
    return ChannelStreamingProcessor(
        channels=create_default_channels(), default_token_namespaces={"main"}, prefer_updates=prefer_updates
    )


# Example usage
async def example_usage():
    """Example of how to use the channel streaming processor."""

    # Custom channel configuration
    channels = [
        ChannelConfig(
            key="messages",
            stream_mode=StreamMode.TOKEN_BY_TOKEN,
            namespaces={"main", "clarify"},  # Stream tokens from main and clarify nodes
            message_tags={"reasoning", "agent_name"},  # Only stream messages with these tags
        ),
        ChannelConfig(
            key="supervisor_messages",
            stream_mode=StreamMode.UPDATES_ONLY,  # Use updates for faster streaming
            namespaces={"main"},
        ),
        ChannelConfig(
            key="research_notes",
            stream_mode=StreamMode.VALUES_ONLY,
            artifact_type="ResearchDocument",
            filter_fn=lambda x: x is not None and len(str(x)) > 10,  # Only non-empty notes
        ),
    ]

    processor = ChannelStreamingProcessor(channels, prefer_updates=True)

    # Use with any LangGraph
    # graph = get_some_graph()
    # input_data = {"messages": [HumanMessage("Hello")]}

    # async for event in processor.stream(graph, input_data):
    #     if isinstance(event, TokenStreamEvent):
    #         print(f"[{event.node_name}:{event.task_id}] Token: {event.content_delta}")
    #     elif isinstance(event, ArtifactStreamEvent):
    #         print(f"[{event.node_name}] Artifact ({event.artifact_type}): {event.artifact_data}")
    #     elif isinstance(event, UpdateStreamEvent):
    #         print(f"[{event.node_name}] Update: {event.state_update}")
    #     elif isinstance(event, ValueStreamEvent):
    #         print(f"[{event.node_name}] Value update in {event.channel}: {event.value}")     #         print(f"[{event.node_name}] Value update in {event.channel}: {event.value}")
