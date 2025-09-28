"""Stream Processor Integration for Conversational Streaming.

This module configures and integrates the Stream Processor with the
ConversationalStreamAdapter to provide seamless conversational streaming
with multi-namespace support.
"""

import logging
from typing import Any, AsyncGenerator, Dict, List, Optional, Set

from ai_engine.streaming.config import ChannelConfig, ChannelType, TokenStreamingConfig
from ai_engine.streaming.events import StreamEvent, ToolCallEvent
from ai_engine.streaming.processor import ChannelStreamingProcessor

from .conversational_stream_adapter import ConversationalStreamAdapter

logger = logging.getLogger(__name__)


class ConversationalStreamProcessor:
    """Processor that integrates Stream Processor with Conversational Adapter."""

    def __init__(
        self,
        enabled_namespaces: Optional[Set[str]] = None,
        include_tool_calls: bool = True,
        include_artifacts: bool = True,
    ):
        """Initialize the conversational stream processor.

        Args:
            enabled_namespaces: Set of namespaces to enable token streaming for.
                               If None, enables for common agent namespaces.
            include_tool_calls: Whether to enable tool call streaming
            include_artifacts: Whether to monitor artifact channels
        """
        self.enabled_namespaces = enabled_namespaces or {
            "main",
            "messages",
            "analysis_agent",
            "research_agent",
            "deep_research_agent",
            "report_generator",
            "clarify_agent",
            "aiops_supervisor_agent",
            "aiops_deepsearch_agent",
        }

        # Configure channels for monitoring
        channels = [
            ChannelConfig(key="messages", channel_type=ChannelType.MESSAGE),
        ]

        if include_artifacts:
            channels.append(ChannelConfig(key="artifacts", channel_type=ChannelType.ARTIFACT))

        # Configure token streaming for multiple namespaces
        token_streaming_config = TokenStreamingConfig(
            enabled_namespaces=self.enabled_namespaces, include_tool_calls=include_tool_calls
        )

        # Create the underlying Stream Processor
        self.processor = ChannelStreamingProcessor(channels=channels, token_streaming=token_streaming_config)

        # Initialize conversational adapter
        self.adapter = ConversationalStreamAdapter()

    async def stream_with_conversation(
        self, graph, input_data: Dict[str, Any], config: Optional[Dict[str, Any]] = None, **kwargs
    ) -> AsyncGenerator[StreamEvent | ToolCallEvent, None]:
        """Stream from a LangGraph with conversational processing.

        Args:
            graph: The LangGraph to stream from
            input_data: Input data for the graph
            config: LangGraph config
            **kwargs: Additional arguments passed to graph streaming

        Yields:
            StreamEvent or ToolCallEvent instances processed through conversation
        """
        logger.info("Starting conversational streaming")

        async for event in self.processor.stream(graph, input_data, config, **kwargs):
            # Process event through conversational adapter
            await self.adapter.process_event(event)

            # Yield the event for any additional processing
            yield event

    def get_adapter(self) -> ConversationalStreamAdapter:
        """Get the conversational adapter instance."""
        return self.adapter

    def add_namespace(self, namespace: str) -> None:
        """Add a new namespace for token streaming."""
        self.enabled_namespaces.add(namespace)
        # Recreate token streaming config with new namespace
        self.processor.token_streaming.enabled_namespaces.add(namespace)
        logger.debug(f"Added namespace for streaming: {namespace}")

    def remove_namespace(self, namespace: str) -> None:
        """Remove a namespace from token streaming."""
        self.enabled_namespaces.discard(namespace)
        self.processor.token_streaming.enabled_namespaces.discard(namespace)
        logger.debug(f"Removed namespace from streaming: {namespace}")

    def reset_session(self) -> None:
        """Reset both the processor and adapter for a new session."""
        # Reset the adapter's conversational state
        self.adapter.reset_session()

        # Reset processor state (clear tracking)
        self.processor._previous_state.clear()
        self.processor._message_accumulators.clear()
        self.processor._seen_message_ids.clear()
        self.processor.tool_call_tracker.reset()

        logger.debug("Conversational streaming session reset")


def create_conversational_processor(
    agent_names: Optional[List[str]] = None, include_tool_calls: bool = True, include_artifacts: bool = True
) -> ConversationalStreamProcessor:
    """Factory function to create a conversational stream processor.

    Args:
        agent_names: List of agent names to enable streaming for.
                    If None, uses default common agents.
        include_tool_calls: Whether to enable tool call streaming
        include_artifacts: Whether to monitor artifact channels

    Returns:
        Configured ConversationalStreamProcessor instance
    """
    # Convert agent names to namespace format if provided
    if agent_names:
        enabled_namespaces = {"main", "messages"}
        for agent_name in agent_names:
            # Convert from display names to namespace format
            namespace = agent_name.lower().replace(" ", "_")
            enabled_namespaces.add(namespace)
    else:
        enabled_namespaces = None  # Use defaults

    processor = ConversationalStreamProcessor(
        enabled_namespaces=enabled_namespaces,
        include_tool_calls=include_tool_calls,
        include_artifacts=include_artifacts,
    )

    # Initialize the adapter's UI containers
    processor.adapter.initialize_ui_containers()

    return processor


# Convenience configurations for different use cases
def create_simple_conversational_processor() -> ConversationalStreamProcessor:
    """Create a simple processor for basic conversational streaming."""
    return create_conversational_processor(
        agent_names=["Analysis Agent", "Research Agent"], include_tool_calls=True, include_artifacts=False
    )


def create_full_conversational_processor() -> ConversationalStreamProcessor:
    """Create a full-featured processor for complex multi-agent conversations."""
    return create_conversational_processor(
        agent_names=[
            "Deep Research Agent",
            "Aiops Supervisor Agent",
            "Aiops Deepsearch Agent",
            "Report Generator",
            "Clarify Agent",
        ],
        include_tool_calls=True,
        include_artifacts=True,
    )


def create_custom_conversational_processor(
    namespaces: Set[str], include_tool_calls: bool = True, include_artifacts: bool = True
) -> ConversationalStreamProcessor:
    """Create a custom processor with specific namespace configuration.

    Args:
        namespaces: Exact set of namespaces to enable streaming for
        include_tool_calls: Whether to enable tool call streaming
        include_artifacts: Whether to monitor artifact channels

    Returns:
        Configured ConversationalStreamProcessor instance
    """
    processor = ConversationalStreamProcessor(
        enabled_namespaces=namespaces, include_tool_calls=include_tool_calls, include_artifacts=include_artifacts
    )

    processor.adapter.initialize_ui_containers()
    return processor
