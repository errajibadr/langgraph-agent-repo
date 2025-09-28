"""Conversational Stream Adapter for Streamlit UI integration.

This module provides the core conversational streaming experience that transforms
namespace-based streaming into natural conversation flow with real-time work visibility.

Replaces both streaming_service.py and streaming_v2.py with a unified approach
leveraging the Stream Processor's event-driven architecture.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

import streamlit as st
from ai_engine.streaming.events import ArtifactEvent, ChannelValueEvent, StreamEvent, TokenStreamEvent, ToolCallEvent
from ai_engine.streaming.processor import ChannelStreamingProcessor

logger = logging.getLogger(__name__)


@dataclass
class NamespaceState:
    """State for a namespace in conversational streaming."""

    namespace: str
    task_id: Optional[str]
    display_name: str
    is_main: bool
    is_active: bool
    parent_namespace: Optional[str] = None

    # Content state
    message_buffer: str = ""
    active_tool_calls: Dict[str, "ToolCallState"] = field(default_factory=dict)

    # UI state
    container: Optional[Any] = None
    token_streaming_enabled: bool = False


@dataclass
class ToolCallState:
    """State for a tool call within conversation context."""

    call_id: str
    name: str
    namespace: str
    status: str  # 'building', 'executing', 'completed', 'error'
    args_preview: str = "Building arguments..."
    final_args: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None
    error_message: Optional[str] = None
    display_index: int = 0


class ConversationalStreamAdapter:
    """Adapter that transforms Stream Processor events into conversational flow."""

    def __init__(self):
        """Initialize the conversational stream adapter."""
        self.chat_container = None
        self.current_speaker: Optional[str] = None
        self.namespaces: Dict[str, NamespaceState] = {}
        self.speaker_containers: Dict[str, Any] = {}

        # Work indicators and conversation flow
        self.conversation_history: List[Dict[str, Any]] = []
        self.active_speakers: Set[str] = set()

        # UI containers
        self.current_message_container: Optional[Any] = None
        self.current_work_container: Optional[Any] = None

        # Speaker avatars for conversational experience
        self.speaker_avatars = {
            "AI": "🤖",
            "Analysis Agent": "📊",
            "Research Agent": "🔍",
            "Report Generator": "📝",
            "Clarify Agent": "❓",
            "Data Processor": "⚙️",
            "Deep Research Agent": "🔬",
            "Aiops Supervisor Agent": "👔",
            "Aiops Deepsearch Agent": "🕵️",
        }

    def get_speaker_for_namespace(self, namespace: str) -> str:
        """Map namespace to conversational speaker name."""
        if namespace in ["main", "()", "", "messages"]:
            return "AI"
        else:
            # Clean namespace for display (analysis_agent -> Analysis Agent)
            return namespace.replace("_", " ").title()

    def get_avatar(self, speaker: str) -> str:
        """Get avatar for speaker."""
        return self.speaker_avatars.get(speaker, "🤖")

    async def process_event(self, event: StreamEvent):
        """Process events maintaining conversational flow."""

        # Determine the "speaker" for this event
        speaker = self.get_speaker_for_namespace(event.namespace)

        # Ensure namespace state exists
        if event.namespace not in self.namespaces:
            self.namespaces[event.namespace] = NamespaceState(
                namespace=event.namespace,
                task_id=getattr(event, "task_id", None),
                display_name=speaker,
                is_main=(event.namespace in ["main", "()", "", "messages"]),
                is_active=True,
                token_streaming_enabled=True,
            )

        # Route event to appropriate handler
        if isinstance(event, TokenStreamEvent):
            await self.handle_conversational_streaming(speaker, event)
        elif isinstance(event, ToolCallEvent):
            await self.handle_conversational_tool_call(speaker, event)
        elif isinstance(event, ChannelValueEvent):
            await self.handle_conversational_update(speaker, event)
        elif isinstance(event, ArtifactEvent):
            await self.handle_conversational_artifact(speaker, event)

    async def handle_conversational_streaming(self, speaker: str, event: TokenStreamEvent):
        """Handle token streaming as conversational flow."""
        namespace_state = self.namespaces[event.namespace]

        # Start new speaker turn if needed
        if self.current_speaker != speaker:
            await self.start_new_speaker_turn(speaker)

        # Update message buffer
        namespace_state.message_buffer = event.accumulated_content

        # Update streaming display
        if self.current_message_container:
            with self.current_message_container:
                if event.accumulated_content.strip():
                    st.markdown(event.accumulated_content)

    async def handle_conversational_tool_call(self, speaker: str, event: ToolCallEvent):
        """Handle tool calls as part of conversation."""
        namespace_state = self.namespaces[event.namespace]

        # Start new speaker turn if needed
        if self.current_speaker != speaker:
            await self.start_new_speaker_turn(speaker)

        # Update tool call state
        tool_call_state = ToolCallState(
            call_id=event.tool_call_id,
            name=event.tool_name,
            namespace=event.namespace,
            status=event.status,
            args_preview=event.args_accumulated or "Building arguments...",
            final_args=event.args,
            error_message=event.error,
        )

        namespace_state.active_tool_calls[event.tool_call_id] = tool_call_state

        # Show work indicator
        await self.show_work_indicator(speaker, f"🔧 Calling {event.tool_name}...")

    async def handle_conversational_update(self, speaker: str, event: ChannelValueEvent):
        """Handle channel updates in conversational context."""
        # For now, we'll focus on critical updates that should be shown
        if event.channel in ["messages", "artifacts"]:
            logger.debug(f"Channel update from {speaker}: {event.channel}")

    async def handle_conversational_artifact(self, speaker: str, event: ArtifactEvent):
        """Handle artifacts within conversation context."""
        # Start new speaker turn if needed
        if self.current_speaker != speaker:
            await self.start_new_speaker_turn(speaker)

        # Show artifacts as part of speaker's message
        # This will integrate with existing artifact display components
        logger.info(f"Artifact from {speaker}: {event.artifact_type}")

    async def start_new_speaker_turn(self, speaker: str):
        """Start a new conversational turn for the speaker."""
        self.current_speaker = speaker
        self.active_speakers.add(speaker)

        # Create new chat message
        with st.chat_message("assistant", avatar=self.get_avatar(speaker)):
            # Speaker identification if not main AI
            if speaker != "AI":
                st.caption(f"🤖 {speaker}")

            # Create containers for this speaker's content
            self.current_message_container = st.empty()
            self.current_work_container = st.empty()

        # Store container reference
        self.speaker_containers[speaker] = {
            "message_container": self.current_message_container,
            "work_container": self.current_work_container,
        }

    async def show_work_indicator(self, speaker: str, indicator_text: str):
        """Show work indicator as part of conversation."""
        if self.current_work_container and speaker == self.current_speaker:
            with self.current_work_container:
                st.caption(indicator_text)

    def initialize_ui_containers(self):
        """Initialize Streamlit containers for conversational streaming."""
        # Initialize session state for conversational streaming
        if "conversational_state" not in st.session_state:
            st.session_state.conversational_state = {"speakers": [], "current_speaker": None, "active_work": {}}

        # Main chat container will be managed dynamically
        # as speakers start their turns

    def reset_session(self):
        """Reset the conversational session."""
        self.namespaces.clear()
        self.speaker_containers.clear()
        self.conversation_history.clear()
        self.active_speakers.clear()
        self.current_speaker = None
        self.current_message_container = None
        self.current_work_container = None

        # Clear session state
        if "conversational_state" in st.session_state:
            st.session_state.conversational_state = {"speakers": [], "current_speaker": None, "active_work": {}}

    def get_conversation_summary(self) -> Dict[str, Any]:
        """Get a summary of the conversation."""
        active_tool_calls = []
        for namespace_state in self.namespaces.values():
            for tool_call in namespace_state.active_tool_calls.values():
                if tool_call.status == "completed":
                    active_tool_calls.append(
                        {
                            "speaker": namespace_state.display_name,
                            "tool": tool_call.name,
                            "args": tool_call.final_args,
                            "result": tool_call.result,
                        }
                    )

        return {
            "speakers_involved": list(self.active_speakers),
            "current_speaker": self.current_speaker,
            "total_namespaces": len(self.namespaces),
            "completed_tool_calls": active_tool_calls,
            "conversation_active": len(self.active_speakers) > 0,
        }


# Factory function for easy integration
def create_conversational_stream_adapter() -> ConversationalStreamAdapter:
    """Create a conversational stream adapter configured for Streamlit."""
    adapter = ConversationalStreamAdapter()
    adapter.initialize_ui_containers()
    return adapter


# Example usage
async def example_conversational_streaming():
    """Example of conversational streaming usage."""
    st.title("🤖 Conversational AI Streaming")

    # Initialize conversational adapter
    if "conversational_adapter" not in st.session_state:
        st.session_state.conversational_adapter = create_conversational_stream_adapter()

    adapter = st.session_state.conversational_adapter

    # User input
    user_input = st.text_input("Ask a question:", key="conv_input")

    if st.button("Send", key="conv_send"):
        if user_input:
            # Reset for new conversation
            adapter.reset_session()

            # Here you would integrate with LangGraph streaming using Stream Processor
            st.info("This is where LangGraph streaming integration would happen...")

            # Example: processor.stream(graph, input_data, config)
            # async for event in processor.stream(...):
            #     await adapter.process_event(event)

    # Show conversation summary
    if st.button("Show Conversation Summary"):
        summary = adapter.get_conversation_summary()
        st.json(summary)
