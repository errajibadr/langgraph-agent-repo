"""LangGraph streaming infrastructure.

Provides clean separation of concerns:
- Channel monitoring: Track state changes across all namespaces
- Token streaming: Stream LLM output from specific namespaces
- Tool call streaming: Handle complex tool call argument streaming

This package consolidates and improves upon the functionality from:
- utils/channel_streaming_v2.py
- utils/streaming_parser.py
"""

from ai_engine.streaming.config import ChannelConfig, ChannelType, StreamMode, TokenStreamingConfig

# Event types
from ai_engine.streaming.events import (
    ArtifactEvent,
    ChannelUpdateEvent,
    ChannelValueEvent,
    StreamEvent,
    TokenStreamEvent,
    ToolCallEvent,
)

# Convenience functions
from ai_engine.streaming.factories import create_default_channels, create_simple_processor

# Core processor and configuration
from ai_engine.streaming.processor import ChannelStreamingProcessor

# Tool call handling
from ai_engine.streaming.tool_calls import ToolCallState, ToolCallStatus, ToolCallTracker

__all__ = [
    # Core components
    "ChannelStreamingProcessor",
    "ChannelConfig",
    "TokenStreamingConfig",
    "StreamMode",
    "ChannelType",
    # Events
    "StreamEvent",
    "TokenStreamEvent",
    "ChannelValueEvent",
    "ChannelUpdateEvent",
    "ArtifactEvent",
    "ToolCallEvent",
    # Tool calls
    "ToolCallTracker",
    "ToolCallState",
    "ToolCallStatus",
    # Factories
    "create_default_channels",
    "create_simple_processor",
]
