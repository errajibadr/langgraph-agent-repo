"""Conversational Stream Adapter for Sequential Message Architecture.

This module provides the data layer for conversational streaming that transforms
namespace-based streaming events into sequential message structure in st.session_state.

Architecture V2: Pure data layer - no UI concerns, updates st.session_state.messages directly.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

import streamlit as st
from ai_engine.streaming.events import ArtifactEvent, ChannelValueEvent, StreamEvent, TokenStreamEvent, ToolCallEvent

logger = logging.getLogger(__name__)


class ConversationalStreamAdapter:
    """Adapter that processes streaming events and updates sequential message structure in session state.

    Architecture V2: Pure data layer - focuses on building st.session_state.messages chronologically.
    No UI container management - that's handled by the Chat Component (UI Layer).
    """

    def __init__(self):
        """Initialize the conversational stream adapter."""
        # Initialize session state messages if not exists
        if "messages" not in st.session_state:
            st.session_state.messages = []

        # Speaker avatars for namespace mapping (used by UI layer)
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
            # Convert namespace to display name (analysis_agent:task_123 → Analysis Agent)
            base_name = namespace.split(":")[0]
            return base_name.replace("_", " ").title()

    def get_avatar(self, speaker: str) -> str:
        """Get avatar for speaker."""
        return self.speaker_avatars.get(speaker, "🤖")

    async def process_event(self, event: StreamEvent):
        """Process events and update sequential message structure in session state."""

        # Route event to appropriate handler
        if isinstance(event, TokenStreamEvent):
            await self.handle_conversational_streaming(event)
        elif isinstance(event, ToolCallEvent):
            await self.handle_conversational_tool_call(event)
        elif isinstance(event, ChannelValueEvent):
            await self.handle_conversational_update(event)
        elif isinstance(event, ArtifactEvent):
            await self.handle_conversational_artifact(event)

    async def handle_conversational_streaming(self, event: TokenStreamEvent):
        """Update or create AI message in session state."""

        # Skip if no message_id (shouldn't happen in normal streaming)
        if not event.message_id:
            logger.warning(f"Received TokenStreamEvent without message_id in namespace {event.namespace}")
            return

        # Find existing message in session state
        existing_msg = self._find_message_in_session_state(event.message_id, event.namespace)

        if existing_msg:
            # Update existing message content (token streaming)
            existing_msg["content"] = event.accumulated_content
            logger.debug(f"Updated message {event.message_id} in namespace {event.namespace}")
        else:
            # Create new AI message in session state
            new_message = {
                "id": event.message_id,
                "namespace": event.namespace,
                "role": "ai",
                "content": event.accumulated_content,
                "timestamp": datetime.now().isoformat(),
            }
            st.session_state.messages.append(new_message)
            logger.debug(f"Created new message {event.message_id} in namespace {event.namespace}")

    async def handle_conversational_tool_call(self, event: ToolCallEvent):
        """Update or create tool call entry in session state."""

        # Find existing tool call entry
        existing_tool = self._find_tool_call_in_session_state(event.tool_call_id)

        if existing_tool:
            # Update existing tool call status/result
            existing_tool["status"] = event.status
            if event.args:
                existing_tool["args"] = event.args
            if event.result:
                existing_tool["result"] = event.result
            logger.debug(f"Updated tool call {event.tool_call_id} with status {event.status}")
        else:
            # Create new tool call entry in session state
            new_tool_call = {
                "namespace": event.namespace,
                "message_id": event.message_id,
                "tool_call_id": event.tool_call_id,
                "role": "tool_call",
                "name": event.tool_name,
                "status": event.status,
                "args": event.args,
                "result": event.result,
                "timestamp": datetime.now().isoformat(),
            }
            st.session_state.messages.append(new_tool_call)
            logger.debug(f"Created new tool call {event.tool_call_id} for {event.tool_name}")

    async def handle_conversational_update(self, event: ChannelValueEvent):
        """Handle channel updates in conversational context."""
        # For now, we'll focus on critical updates that should be shown
        if event.channel in ["messages", "artifacts"]:
            logger.debug(f"Channel update: {event.channel} in namespace {event.namespace}")

    async def handle_conversational_artifact(self, event: ArtifactEvent):
        """Handle artifacts by adding them to the most recent AI message in the namespace."""

        # Find the most recent AI message in this namespace to attach artifact to
        recent_ai_msg = None
        for msg in reversed(st.session_state.messages):
            if msg.get("role") == "ai" and msg.get("namespace") == event.namespace:
                recent_ai_msg = msg
                break

        if recent_ai_msg:
            # Add artifact to the message
            if "artifacts" not in recent_ai_msg:
                recent_ai_msg["artifacts"] = []

            artifact_data = {
                "type": event.artifact_type,
                "data": event.artifact_data,
                "namespace": event.namespace,
                "timestamp": datetime.now().isoformat(),
            }
            recent_ai_msg["artifacts"].append(artifact_data)
            logger.info(f"Added artifact {event.artifact_type} to message in namespace {event.namespace}")
        else:
            # Create standalone artifact message if no AI message found
            artifact_message = {
                "namespace": event.namespace,
                "role": "artifact",
                "artifact_type": event.artifact_type,
                "artifact_data": event.artifact_data,
                "timestamp": datetime.now().isoformat(),
            }
            st.session_state.messages.append(artifact_message)
            logger.info(f"Created standalone artifact message: {event.artifact_type}")

    def _find_message_in_session_state(self, message_id: str, namespace: str) -> Optional[Dict[str, Any]]:
        """Find existing AI message in session state."""
        for msg in st.session_state.messages:
            if msg.get("id") == message_id and msg.get("namespace") == namespace and msg.get("role") == "ai":
                return msg
        return None

    def _find_tool_call_in_session_state(self, tool_call_id: str) -> Optional[Dict[str, Any]]:
        """Find existing tool call in session state."""
        for msg in st.session_state.messages:
            if msg.get("tool_call_id") == tool_call_id and msg.get("role") == "tool_call":
                return msg
        return None

    def reset_session(self):
        """Reset the conversational session by clearing messages."""
        if "messages" in st.session_state:
            st.session_state.messages.clear()
        logger.debug("Conversational session reset - messages cleared")

    def get_conversation_summary(self) -> Dict[str, Any]:
        """Get a summary of the current conversation."""
        if "messages" not in st.session_state:
            return {"total_messages": 0, "speakers": [], "tool_calls": 0}

        speakers = set()
        tool_calls = 0

        for message in st.session_state.messages:
            if message.get("role") == "ai" and message.get("namespace"):
                speaker = self.get_speaker_for_namespace(message["namespace"])
                speakers.add(speaker)
            elif message.get("role") == "tool_call":
                tool_calls += 1

        return {
            "total_messages": len(st.session_state.messages),
            "speakers": list(speakers),
            "tool_calls": tool_calls,
            "messages": st.session_state.messages,  # Include full messages for detailed summary
        }


# Factory function for easy integration
def create_conversational_stream_adapter() -> ConversationalStreamAdapter:
    """Create a conversational stream adapter configured for sequential message architecture."""
    adapter = ConversationalStreamAdapter()
    return adapter


# Utility functions for UI layer
def get_speaker_for_namespace(namespace: str) -> str:
    """Map namespace to display name - utility for UI layer."""
    if namespace in ["main", "()", "", "messages"]:
        return "AI"
    # Convert namespace to display name (analysis_agent:task_123 → Analysis Agent)
    base_name = namespace.split(":")[0]
    return base_name.replace("_", " ").title()


def get_avatar(speaker: str) -> str:
    """Get emoji avatar for speaker - utility for UI layer."""
    avatars = {
        "AI": "🤖",
        "Analysis Agent": "📊",
        "Research Agent": "🔍",
        "Report Generator": "📝",
        "Data Processor": "⚙️",
        "Deep Research Agent": "🔬",
        "Aiops Supervisor Agent": "👔",
        "Aiops Deepsearch Agent": "🕵️",
    }
    return avatars.get(speaker, "🤖")


def get_tool_status_display(tool_message: Dict[str, Any]) -> str:
    """Convert tool call status to user-friendly display - utility for UI layer."""
    status_map = {
        "args_streaming": f"🔧 Calling {tool_message['name']}...",
        "args_started": f"🔧 Calling {tool_message['name']}...",
        "args_completed": f"🔍 Executing {tool_message['name']}...",
        "args_ready": f"🔍 Executing {tool_message['name']}...",
        "result_success": f"✅ {tool_message['name']} completed",
        "result_error": f"❌ {tool_message['name']} failed",
    }
    return status_map.get(tool_message["status"], f"🔧 {tool_message['name']}")


# Example usage for testing
async def example_sequential_streaming():
    """Example of sequential streaming usage."""
    st.title("🤖 Sequential Conversational Streaming")

    # Initialize adapter
    if "conversational_adapter" not in st.session_state:
        st.session_state.conversational_adapter = create_conversational_stream_adapter()

    adapter = st.session_state.conversational_adapter

    # Show current message state
    if st.button("Show Message State"):
        summary = adapter.get_conversation_summary()
        st.json(summary)

    # Reset session
    if st.button("Reset Session"):
        adapter.reset_session()
        st.success("Session reset - messages cleared")
        st.rerun()
