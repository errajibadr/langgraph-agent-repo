"""Unified streaming service for LangGraph conversational chat.

This service handles:
- Connecting to LangGraph and streaming events
- Processing events and updating chat state (live_chat, chat_history)
- Triggering live container updates
- Managing streaming lifecycle

Architecture: Single unified service that owns the entire streaming pipeline
from LangGraph events to chat state updates.
"""

import logging
import uuid
from datetime import datetime
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional, Set

import streamlit as st
from ai_engine.streaming.config import ChannelConfig, ChannelType, TokenStreamingConfig
from ai_engine.streaming.events import (
    ArtifactEvent,
    ChannelValueEvent,
    MessageReceivedEvent,
    StreamEvent,
    TokenStreamEvent,
    ToolCallEvent,
)
from ai_engine.streaming.processor import ChannelStreamingProcessor

from frontend.types.messages import AIMessage, ArtifactData, ArtifactMessage, ToolCallMessage, UserMessage

logger = logging.getLogger(__name__)


class ConversationalStreamingService:
    """Unified service for streaming from LangGraph and managing conversational chat state.

    This service:
    1. Connects to LangGraph via ChannelStreamingProcessor
    2. Processes streaming events (tokens, tool calls, artifacts)
    3. Updates chat state in st.session_state (live_chat during streaming)
    4. Triggers container updates for real-time UI
    5. Manages session lifecycle and cleanup
    """

    # Default namespaces to enable token streaming for
    _DEFAULT_NAMESPACES = {"main"}

    def __init__(
        self,
        enabled_namespaces: Optional[Set[str]] = None,
        include_tool_calls: bool = True,
        include_artifacts: bool = True,
        include_tags: Optional[Set[str]] = None,
        exclude_tags: Optional[Set[str]] = None,
    ):
        """Initialize the conversational streaming service.

        Args:
            enabled_namespaces: Set of namespaces to enable token streaming for.
                               If None, enables for default namespaces.
            include_tool_calls: Whether to enable tool call streaming
            include_artifacts: Whether to monitor artifact channels
        """
        self.enabled_namespaces = enabled_namespaces or self._DEFAULT_NAMESPACES

        # Configure channels for monitoring
        channels = [
            ChannelConfig(key="messages", channel_type=ChannelType.MESSAGE),
        ]

        if include_artifacts:
            channels.append(ChannelConfig(key="artifacts", channel_type=ChannelType.ARTIFACT, artifact_type="artifact"))
            channels.append(
                ChannelConfig(key="research_brief", channel_type=ChannelType.ARTIFACT, artifact_type="artifact")
            )

        # Configure token streaming for multiple namespaces
        token_streaming_config = TokenStreamingConfig(
            enabled_namespaces=self.enabled_namespaces,
            include_tool_calls=include_tool_calls,
            include_tags=include_tags,
            exclude_tags=exclude_tags,
        )

        # Create the underlying LangGraph stream processor
        self.processor = ChannelStreamingProcessor(channels=channels, token_streaming=token_streaming_config)

        # Container update callback for live UI updates
        self._container_update_callback: Optional[Callable] = None

        logger.info(f"ConversationalStreamingService initialized with namespaces: {self.enabled_namespaces}")

    async def stream_conversation(
        self,
        graph,
        context: Dict[str, Any],
        input_data: Dict[str, Any],
        config: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> AsyncGenerator[StreamEvent, None]:
        """Stream from LangGraph and update chat state in real-time.

        This is the main entry point for streaming. It:
        1. Streams events from the LangGraph
        2. Processes each event to update chat state
        3. Triggers container updates for live UI
        4. Yields events for any additional processing

        Args:
            graph: The LangGraph to stream from
            input_data: Input data for the graph
            config: LangGraph config (e.g., thread_id)
            **kwargs: Additional arguments passed to graph streaming

        Yields:
            StreamEvent instances (TokenStreamEvent, ToolCallEvent, etc.)
        """
        logger.info("Starting conversational streaming")

        async for event in self.processor.stream(
            graph=graph, input_data=input_data, config=config, context=context, **kwargs
        ):
            await self._handle_event(event)

            # Trigger live container update
            self._trigger_container_update()

            # if any additional processing needed
            yield event

        logger.info("Conversational streaming completed")

    async def _handle_event(self, event: StreamEvent):
        """Route event to appropriate handler and update chat state.

        Args:
            event: StreamEvent from LangGraph
        """
        if isinstance(event, TokenStreamEvent):
            await self._handle_token_stream(event)
        elif isinstance(event, MessageReceivedEvent):
            await self._handle_message_received(event)
        elif isinstance(event, ToolCallEvent):
            await self._handle_tool_call(event)
        elif isinstance(event, ChannelValueEvent):
            await self._handle_channel_update(event)
        elif isinstance(event, ArtifactEvent):
            await self._handle_artifact(event)

    async def _handle_token_stream(self, event: TokenStreamEvent):
        """Handle token streaming event - update or create AI message in live_chat."""
        if not event.message_id:
            logger.warning(f"Received TokenStreamEvent without message_id in namespace {event.namespace}")
            return

        # Find existing message in live_chat
        existing_msg = self._find_message_in_live_chat(event.message_id)

        if existing_msg:
            # Update existing message content (token streaming)
            existing_msg["content"] = event.accumulated_content
            logger.debug(f"Updated live message {event.message_id} in namespace {event.namespace}")
        else:
            # Create new AI message in live_chat (type: AIMessage)
            new_message: AIMessage = {
                "id": event.message_id,
                "namespace": event.namespace,
                "role": "ai",
                "content": event.accumulated_content,
                "timestamp": datetime.now().isoformat(),
            }
            st.session_state.live_chat.append(new_message)
            logger.debug(f"Created new live message {event.message_id} in namespace {event.namespace}")

    async def _handle_message_received(self, event: MessageReceivedEvent):
        """Handle message received event - ensure message exists in live_chat."""
        existing_msg = self._find_message_in_live_chat(event.message_id)

        if existing_msg:
            # Update existing message content
            existing_msg["content"] = event.message.content
            logger.debug(f"Updated message {event.message_id} in namespace {event.namespace}")
        else:
            # Create new message in live_chat (type: AIMessage or UserMessage)
            role = event.message_type if event.message_type in ["ai", "user"] else "ai"
            new_message: AIMessage | UserMessage = {
                "id": event.message_id,
                "namespace": event.namespace,
                "role": role,  # type: ignore
                "content": event.message.content,
                "timestamp": datetime.now().isoformat(),
            }
            st.session_state.live_chat.append(new_message)
            logger.debug(f"Created new message {event.message_id} in namespace {event.namespace}")

    async def _handle_tool_call(self, event: ToolCallEvent):
        """Handle tool call event - update or create tool call entry in live_chat."""
        existing_tool = self._find_tool_call_in_live_chat(event.tool_call_id)

        if existing_tool:
            # Update existing tool call status/result
            existing_tool["status"] = event.status  # type: ignore
            if event.args:
                existing_tool["args"] = event.args
            if event.result:
                existing_tool["result"] = event.result
            logger.debug(f"Updated tool call {event.tool_call_id} with status {event.status}")
        else:
            # Create new tool call entry in live_chat (type: ToolCallMessage)
            new_tool_call: ToolCallMessage = {
                "namespace": event.namespace,
                "message_id": event.message_id,
                "tool_call_id": event.tool_call_id,
                "role": "tool_call",
                "name": event.tool_name,
                "status": event.status,  # type: ignore
                "timestamp": datetime.now().isoformat(),
            }
            if event.args:
                new_tool_call["args"] = event.args
            if event.result:
                new_tool_call["result"] = event.result

            st.session_state.live_chat.append(new_tool_call)
            logger.debug(f"Created new tool call {event.tool_call_id} for {event.tool_name}")

    async def _handle_channel_update(self, event: ChannelValueEvent):
        """Handle channel update events (logged for debugging)."""
        if event.channel in ["messages", "artifacts"]:
            logger.debug(f"Channel update: {event.channel} in namespace {event.namespace}")

    async def _handle_artifact(self, event: ArtifactEvent):
        """Handle artifacts by attaching them to the most recent AI message in the namespace.

        Note: event.artifact_data can be either:
        - A list of Pydantic artifact models (from agents)
        - A single dict (from other sources)
        """
        # Find the most recent AI message in this namespace
        recent_ai_msg = None
        for msg in reversed(st.session_state.live_chat):
            if msg.get("role") == "ai" and msg.get("namespace") == event.namespace:
                recent_ai_msg = msg
                break

        # Normalize artifact_data to a list
        artifacts_list = event.artifact_data if isinstance(event.artifact_data, list) else [event.artifact_data]

        if recent_ai_msg:
            # Add artifacts to the message (properly typed as ArtifactData)
            if "artifacts" not in recent_ai_msg:
                recent_ai_msg["artifacts"] = []

            # Process each artifact individually
            for artifact_item in artifacts_list:
                # Convert Pydantic model to dict if needed
                if hasattr(artifact_item, "model_dump"):
                    artifact_dict = artifact_item.model_dump()
                elif isinstance(artifact_item, dict):
                    artifact_dict = artifact_item
                else:
                    logger.warning(f"Unexpected artifact type: {type(artifact_item)}")
                    continue

                # Extract artifact type from the artifact itself, or use event type
                artifact_type = artifact_dict.get("type", event.artifact_type)

                artifact_data: ArtifactData = {
                    "type": artifact_type,  # type: ignore
                    "id": artifact_dict.get("id", f"{event.namespace}_{uuid.uuid4()}"),
                    "data": artifact_dict,  # Store the full artifact dict
                    "namespace": event.namespace,
                    "timestamp": datetime.now().isoformat(),
                }
                recent_ai_msg["artifacts"].append(artifact_data)

            logger.info(f"Added {len(artifacts_list)} artifact(s) to message in namespace {event.namespace}")
        else:
            # Create standalone artifact message if no AI message found
            # Convert to dict if it's a Pydantic model or list
            if isinstance(event.artifact_data, list):
                artifact_data_dict = [
                    item.model_dump() if hasattr(item, "model_dump") else item for item in event.artifact_data
                ]
            elif hasattr(event.artifact_data, "model_dump"):
                artifact_data_dict = event.artifact_data.model_dump()
            else:
                artifact_data_dict = event.artifact_data

            artifact_message: ArtifactMessage = {
                "namespace": event.namespace,
                "role": "artifact",
                "artifact_type": event.artifact_type,
                "artifact_data": artifact_data_dict,  # type: ignore
                "timestamp": datetime.now().isoformat(),
            }
            st.session_state.live_chat.append(artifact_message)
            logger.info(f"Created standalone artifact message: {event.artifact_type}")

    def _find_message_in_live_chat(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Find existing message in live_chat by message_id."""
        for msg in st.session_state.live_chat:
            if msg.get("id") == message_id:
                return msg
        return None

    def _find_tool_call_in_live_chat(self, tool_call_id: str) -> Optional[Dict[str, Any]]:
        """Find existing tool call in live_chat by tool_call_id."""
        for msg in st.session_state.live_chat:
            if msg.get("tool_call_id") == tool_call_id and msg.get("role") == "tool_call":
                return msg
        return None

    def set_container_update_callback(self, callback: Callable):
        """Set callback function to trigger live container updates.

        Args:
            callback: Function to call when chat state is updated (for live UI updates)
        """
        self._container_update_callback = callback
        logger.debug("Container update callback registered")

    def _trigger_container_update(self):
        """Trigger live container update if callback is set."""
        if self._container_update_callback:
            try:
                self._container_update_callback()
            except Exception as e:
                logger.error(f"Error triggering container update: {e}")

    def add_namespace(self, namespace: str) -> None:
        """Add a new namespace for token streaming.

        Args:
            namespace: Namespace to enable streaming for
        """
        self.enabled_namespaces.add(namespace)
        self.processor.token_streaming.enabled_namespaces.add(namespace)
        logger.info(f"Added namespace for streaming: {namespace}")

    def remove_namespace(self, namespace: str) -> None:
        """Remove a namespace from token streaming.

        Args:
            namespace: Namespace to disable streaming for
        """
        self.enabled_namespaces.discard(namespace)
        self.processor.token_streaming.enabled_namespaces.discard(namespace)
        logger.info(f"Removed namespace from streaming: {namespace}")

    def reset_session(self) -> None:
        """Reset streaming session - clears processor state and chat history."""
        # Reset processor state
        self.processor._previous_state.clear()
        self.processor._message_accumulators.clear()
        self.processor._seen_message_ids.clear()
        self.processor.tool_call_tracker.reset()

        # Clear chat history
        if "chat_history" in st.session_state:
            st.session_state.chat_history.clear()

        logger.info("Streaming session reset")


# Factory function for easy service creation
def create_streaming_service(
    agent_names: Optional[List[str]] = None,
    include_tool_calls: bool = True,
    include_artifacts: bool = True,
    include_tags: Optional[Set[str]] = None,
    exclude_tags: Optional[Set[str]] = None,
) -> ConversationalStreamingService:
    """Create a conversational streaming service.

    Args:
        agent_names: List of agent names to enable streaming for.
                    If None, uses default namespaces.
        include_tool_calls: Whether to enable tool call streaming
        include_artifacts: Whether to monitor artifact channels

    Returns:
        Configured ConversationalStreamingService instance
    """
    # Convert agent names to namespace format if provided
    if agent_names:
        enabled_namespaces = {"main"}
        for agent_name in agent_names:
            # Convert from display names to namespace format
            namespace = agent_name.lower().replace(" ", "_")
            enabled_namespaces.add(namespace)
    else:
        enabled_namespaces = {"main"}

    service = ConversationalStreamingService(
        enabled_namespaces=enabled_namespaces,
        include_tool_calls=include_tool_calls,
        include_artifacts=include_artifacts,
        include_tags=include_tags,
        exclude_tags=exclude_tags,
    )

    logger.info(f"Created streaming service with namespaces: {enabled_namespaces}")
    return service
    #
    #
    #
    #
