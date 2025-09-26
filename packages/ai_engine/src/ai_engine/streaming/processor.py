"""Core channel streaming processor.

Main processor that coordinates:
- Channel monitoring (state changes)
- Token streaming (LLM output)
- Tool call streaming (when enabled)

Integrates and improves the functionality from utils/channel_streaming_v2.py.
"""

import logging
from typing import Any, AsyncGenerator, Dict, List, Literal, Optional

from langchain_core.messages.ai import AIMessage, AIMessageChunk
from langchain_core.messages.base import BaseMessage
from langchain_core.messages.tool import ToolMessage, ToolMessageChunk

from .artifact_channel_handler import ArtifactChannelHandler
from .config import ChannelConfig, ChannelType, TokenStreamingConfig
from .events import StreamEvent, TokenStreamEvent, ToolCallEvent
from .message_channel_handler import MessageChannelHandler
from .tool_calls import ToolCallTracker

logger = logging.getLogger(__name__)


class ChannelStreamingProcessor:
    """Main streaming processor with separated concerns.

    Provides clean separation between:
    - Channel monitoring: Track state key changes across all namespaces
    - Token streaming: Stream LLM output token-by-token from specific namespaces
    - Tool call streaming: Handle complex tool call argument reconstruction
    """

    def __init__(
        self,
        channels: List[ChannelConfig],
        token_streaming: Optional[TokenStreamingConfig] = None,
        prefer_updates: bool = False,
    ):
        """Initialize the streaming processor.

        Args:
            channels: List of state channels to monitor
            token_streaming: Configuration for token streaming from namespaces
            prefer_updates: Use "updates" mode instead of "values" for state streaming
        """
        self.channels = {config.key: config for config in channels}
        self.token_streaming = token_streaming or TokenStreamingConfig()
        self.prefer_updates = prefer_updates

        # Initialize tool call tracker if enabled
        self.tool_call_tracker = ToolCallTracker()

        # State tracking
        self._previous_state: Dict[str, Any] = {}  # namespace:channel -> previous_value
        self._message_accumulators: Dict[str, str] = {}  # namespace:task_id -> accumulated content
        self._seen_message_ids: set[str] = set()

        # Handlers
        self._message_handler = MessageChannelHandler(
            tool_call_tracker=self.tool_call_tracker,
            seen_message_ids=self._seen_message_ids,
            parse_namespace_components=self._parse_namespace_components,
        )
        self._artifact_handler = ArtifactChannelHandler()

    @property
    def default_stream_mode(self) -> Literal["updates", "values"]:
        """Default stream mode. update or values depending on prefer_updates"""
        return "updates" if not self.prefer_updates else "values"

    async def stream(
        self, graph, input_data: Dict[str, Any], config: Optional[Dict[str, Any]] = None, **kwargs
    ) -> AsyncGenerator[StreamEvent | ToolCallEvent, None]:
        """Stream from a LangGraph with separated channel and token streaming.

        Args:
            graph: The LangGraph to stream from
            input_data: Input data for the graph
            config: LangGraph config
            **kwargs: Additional arguments passed to graph.astream()

        Yields:
            StreamEvent or ToolCallEvent instances for different types of events
        """
        # Determine which LangGraph streaming modes we need
        stream_modes = self._determine_stream_modes()

        logger.debug(f"Starting stream with modes: {stream_modes}")

        async for raw_output in graph.astream(
            input_data,
            config=config,
            stream_mode=stream_modes,
            subgraphs=True,  # Always enable subgraphs for namespace support
            **kwargs,
        ):
            # Parse the raw output into components
            namespace, mode, chunk = self._parse_raw_output(raw_output, stream_modes)

            # Process the chunk and emit events
            async for event in self._process_chunk(namespace, mode, chunk):
                yield event

    def _determine_stream_modes(self) -> List[str]:
        """Determine which LangGraph stream modes we need."""
        modes = set()

        # Always need values or updates for channel monitoring
        if self.channels:
            modes.add(self.default_stream_mode)

        # Add messages mode if token streaming is enabled
        if self.token_streaming.enabled_namespaces:
            modes.add("messages")

        return list(modes)

    def _parse_raw_output(self, raw_output, stream_modes: List[str]) -> tuple[str, str, Dict | tuple]:
        """Parse raw LangGraph output into (namespace, mode, chunk).

        Handles all LangGraph streaming output formats:
        - Single mode: chunk
        - Multi-mode: (mode, chunk)
        - Subgraphs + single: (namespace_tuple, chunk)
        - Subgraphs + multi: (namespace_tuple, mode, chunk)
        """
        # Case 1: Subgraphs enabled + multiple modes: (namespace_tuple, mode, chunk)
        if isinstance(raw_output, tuple) and len(raw_output) == 3:
            namespace_tuple, mode, chunk = raw_output
            namespace = self._format_namespace(namespace_tuple)
            return namespace, mode, chunk

        # Case 2: Two-element tuple - distinguish between cases
        elif isinstance(raw_output, tuple) and len(raw_output) == 2:
            first, second = raw_output

            # If first element is a string, it's (mode, chunk)
            if isinstance(first, str):
                mode, chunk = first, second
                namespace = "main"
                return namespace, mode, chunk

            # If first element is a Message, it's (message, metadata) from single "messages" mode
            if isinstance(first, BaseMessage):
                chunk = (first, second)  # Keep as tuple for message processing
                mode = "messages"
                namespace = "main"
                return namespace, mode, chunk

            # If first element is tuple (namespace), it's (namespace_tuple, chunk) for single mode
            if isinstance(first, tuple):
                namespace_tuple, chunk = first, second
                namespace = self._format_namespace(namespace_tuple)
                # Determine mode from stream_modes (should be single mode)
                mode = stream_modes[0] if len(stream_modes) == 1 else self.default_stream_mode
                return namespace, mode, chunk

            # Fallback: treat as values in main
            return "main", self.default_stream_mode, second

        # Case 3: Single chunk (single mode, no subgraphs)
        else:
            chunk = raw_output
            mode = stream_modes[0] if len(stream_modes) == 1 else self.default_stream_mode
            namespace = "main"
            return namespace, mode, chunk

    def _format_namespace(self, namespace_tuple: tuple) -> str:
        """Format namespace tuple into a string.

        Examples:
        - () -> "main"
        - ("parent_node:task_id",) -> "parent_node:task_id"
        - ("parent:task_id", "child:task_id") -> "parent:task_id:child:task_id"
        """
        if not namespace_tuple:
            return "main"
        return ":".join(str(part) for part in namespace_tuple)

    async def _process_chunk(
        self, namespace: str, mode: str, chunk: Any
    ) -> AsyncGenerator[StreamEvent | ToolCallEvent, None]:
        """Process a chunk and emit appropriate events."""
        logger.debug(f"Processing chunk: namespace={namespace}, mode={mode}")

        if mode == "messages":
            # Token streaming and tool call processing
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

    async def _process_token_chunk(
        self, namespace: str, chunk: tuple[BaseMessage, Dict[str, Any]]
    ) -> AsyncGenerator[StreamEvent | ToolCallEvent, None]:
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

        if not isinstance(message, AIMessageChunk) and not isinstance(message, ToolMessage):
            logger.warning(
                f"Expected either AIMessageChunk(or any Chunk Subclass) or ToolMessage, got {type(message)}; Skipping token streaming"
            )
            return

        msg_id = getattr(message, "id", None)
        if msg_id:
            self._seen_message_ids.add(msg_id)

        # if message is a tool call and tool call token by token streaming is enabled
        if self.token_streaming.include_tool_calls:
            if isinstance(message, AIMessageChunk) and (
                message.tool_calls or message.tool_call_chunks
            ):  # is a tool call
                node_name, task_id = self._parse_namespace_components(namespace)
                tool_events = self.tool_call_tracker.process_stream_tool_calls(message, namespace, task_id)  # type: ignore
                for event in tool_events:
                    yield event
            if isinstance(message, ToolMessageChunk) or isinstance(message, ToolMessage):  # tc_result
                # Tool Message = tool_call_id and content
                node_name, task_id = self._parse_namespace_components(namespace)
                tool_events = self.tool_call_tracker.process_tool_call_result(message, namespace, task_id)  # type: ignore
                for event in tool_events:
                    yield event

        # Handle regular content streaming for AIMessageChunk only
        if isinstance(message, AIMessageChunk) and hasattr(message, "content") and message.content is not None:
            node_name, task_id = self._parse_namespace_components(namespace)
            accumulator_key = f"{namespace}:{task_id or 'default'}"

            # Accumulate content
            if accumulator_key not in self._message_accumulators:
                self._message_accumulators[accumulator_key] = ""

            content_delta = message.content if isinstance(message.content, str) else str(message.content)
            self._message_accumulators[accumulator_key] += content_delta

            # Generate token stream event
            yield TokenStreamEvent(
                namespace=namespace,
                content_delta=content_delta,
                accumulated_content=self._message_accumulators[accumulator_key],
                message_id=getattr(message, "id", None),
                task_id=task_id,
                node_name=node_name,
                message=message,
            )

    def _should_stream_tokens_from_namespace(self, namespace: str) -> bool:
        """Check if we should stream tokens from this namespace."""
        # Extract the base namespace (first part before any task IDs)
        base_namespace = namespace.split(":")[0] if ":" in namespace else namespace
        return base_namespace in self.token_streaming.enabled_namespaces

    async def _process_channel_values(
        self, namespace: str, chunk: Dict[str, Any]
    ) -> AsyncGenerator[StreamEvent | ToolCallEvent, None]:
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

            # Extract components
            node_name, task_id = self._parse_namespace_components(namespace)

            # Calculate delta for generic channels
            value_delta = self._calculate_delta(previous_value, current_value)

            # Route based on channel type
            if config.channel_type == ChannelType.MESSAGE:
                # current_value expected to be BaseMessage or list[BaseMessage]
                async for event in self._message_handler.handle_values(
                    namespace=namespace,
                    channel_key=channel_key,
                    current_value=current_value,
                    previous_value=previous_value,
                ):
                    yield event
                continue

            # ARTIFACT or GENERIC
            async for event in self._artifact_handler.handle_values(
                namespace=namespace,
                channel_key=channel_key,
                current_value=current_value,
                previous_value=previous_value,
                artifact_type=config.artifact_type,
                node_name=node_name,
                task_id=task_id,
                value_delta=value_delta,
            ):
                yield event

    async def _process_channel_updates(
        self, namespace: str, chunk: Dict[str, Any]
    ) -> AsyncGenerator[StreamEvent | ToolCallEvent, None]:
        """Process state updates for channel monitoring."""
        # Updates format: {node_name: {channel: value, ...}}
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

            # Route based on channel type
            if config.channel_type == ChannelType.MESSAGE:
                # When updates mode is used for message channels, treat updates
                # as newly appended messages and process them similarly
                async for event in self._message_handler.handle_values(
                    namespace=namespace,
                    channel_key=channel_key,
                    current_value=update_value,
                    previous_value=None,
                ):
                    yield event
                continue

            # ARTIFACT or GENERIC
            async for event in self._artifact_handler.handle_update(
                namespace=namespace,
                channel_key=channel_key,
                update_value=update_value,
                artifact_type=config.artifact_type,
                node_name=node_name,
                task_id=task_id,
            ):
                yield event

    def _parse_namespace_components(self, namespace: str) -> tuple[str, Optional[str]]:
        """Parse namespace to extract node_name and task_id."""
        # TODO: review this namespace definition
        if namespace == "main":
            return "main", None

        # For nested namespaces like "parent:task_id:child:task_id"
        # This is heuristic-based and might need refinement
        parts = namespace.split(":")
        if len(parts) >= 2:
            # Assume last part might be task_id, everything else is node path
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

    # Tool call management methods

    def start_new_tool_call_iteration(self):
        """Start a new tool call iteration."""
        if self.tool_call_tracker:
            self.tool_call_tracker.start_new_iteration()

    def get_active_tool_calls(self):
        """Get currently active tool calls."""
        if self.tool_call_tracker:
            return self.tool_call_tracker.get_active_calls()
        return {}

    def get_completed_tool_calls(self):
        """Get all completed tool calls."""
        if self.tool_call_tracker:
            return self.tool_call_tracker.get_all_completed_calls()
        return []

    # Message parsing helper methods (kept for compatibility)

    def _is_message_channel_value(self, value: Any) -> bool:
        """Check if a channel value contains messages.

        DEPRECATED: Channel type should be used instead of this heuristic.
        """
        if isinstance(value, list):
            return len(value) > 0 and all(isinstance(item, BaseMessage) for item in value)
        elif isinstance(value, BaseMessage):
            return True
        return False

    def reset_state(self):
        """Reset all processor state."""
        self._previous_state.clear()
        self._message_accumulators.clear()
        self._seen_message_ids.clear()

        if self.tool_call_tracker:
            self.tool_call_tracker.reset()
