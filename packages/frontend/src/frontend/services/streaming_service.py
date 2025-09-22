"""Streaming service for Streamlit UI integration.

This module provides utilities for integrating LangGraph streaming
with Streamlit components, handling real-time updates for tool calls
and message content.
"""

import asyncio
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

import streamlit as st
from ai_engine.utils.streaming_parser import StreamingGraphParser, ToolCallState, ToolCallStatus, create_ui_parser


@dataclass
class UIToolCallDisplay:
    """Display state for a tool call in the UI."""

    index: int
    name: str
    call_id: str
    status: ToolCallStatus
    args_preview: str
    final_args: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class StreamlitStreamingService:
    """Service for handling streaming updates in Streamlit."""

    def __init__(self):
        """Initialize the streaming service."""
        self.active_tool_calls: Dict[int, UIToolCallDisplay] = {}
        self.historical_tool_calls: List[Dict[str, Any]] = []
        self.current_iteration = 0
        self.content = ""
        self.parser: Optional[StreamingGraphParser] = None

        # Streamlit containers for dynamic updates
        self.content_container = None
        self.tool_calls_container = None
        self.history_container = None

    def initialize_ui_containers(self):
        """Initialize Streamlit containers for streaming updates."""
        if "streaming_content" not in st.session_state:
            st.session_state.streaming_content = ""
        if "streaming_tool_calls" not in st.session_state:
            st.session_state.streaming_tool_calls = {}
        if "streaming_history" not in st.session_state:
            st.session_state.streaming_history = []
        if "current_iteration" not in st.session_state:
            st.session_state.current_iteration = 0

        # Create containers
        self.content_container = st.empty()
        self.tool_calls_container = st.empty()
        self.history_container = st.empty()

    def _on_content_update(self, content: str):
        """Handle content streaming updates."""
        self.content = content
        st.session_state.streaming_content = content
        if self.content_container:
            with self.content_container.container():
                if content.strip():
                    st.markdown(f"**Assistant:** {content}")

    def _on_tool_call_start(self, idx: int, name: str, call_id: str):
        """Handle tool call start."""
        display = UIToolCallDisplay(
            index=idx, name=name, call_id=call_id, status=ToolCallStatus.BUILDING, args_preview="Building arguments..."
        )
        self.active_tool_calls[idx] = display
        st.session_state.streaming_tool_calls[idx] = display
        self._update_tool_calls_display()

    def _on_tool_call_update(self, idx: int, state: ToolCallState):
        """Handle tool call argument updates."""
        if idx in self.active_tool_calls:
            display = self.active_tool_calls[idx]
            display.status = state.status
            display.args_preview = (
                state.accumulated_args[:100] + "..." if len(state.accumulated_args) > 100 else state.accumulated_args
            )
            display.error_message = state.error_message

            st.session_state.streaming_tool_calls[idx] = display
            self._update_tool_calls_display()

    def _on_tool_call_complete(self, idx: int, state: ToolCallState):
        """Handle tool call completion."""
        if idx in self.active_tool_calls:
            display = self.active_tool_calls[idx]
            display.status = ToolCallStatus.COMPLETE
            display.final_args = state.parsed_args
            display.args_preview = "✅ Complete"

            st.session_state.streaming_tool_calls[idx] = display
            self._update_tool_calls_display()

    def _on_iteration_start(self, iteration: int):
        """Handle new iteration start."""
        # Move current tool calls to history
        for idx, display in self.active_tool_calls.items():
            if display.status == ToolCallStatus.COMPLETE:
                self.historical_tool_calls.append(
                    {
                        "iteration": self.current_iteration,
                        "index": idx,
                        "name": display.name,
                        "args": display.final_args,
                        "call_id": display.call_id,
                    }
                )

        # Clear active tool calls for new iteration
        self.active_tool_calls.clear()
        self.current_iteration = iteration

        # Update session state
        st.session_state.streaming_history = self.historical_tool_calls
        st.session_state.streaming_tool_calls = {}
        st.session_state.current_iteration = iteration

        # Update displays
        self._update_tool_calls_display()
        self._update_history_display()

    def _update_tool_calls_display(self):
        """Update the tool calls display in Streamlit."""
        if not self.tool_calls_container:
            return

        with self.tool_calls_container.container():
            if self.active_tool_calls:
                st.markdown(f"### 🔧 Active Tool Calls (Iteration {self.current_iteration})")

                for idx, display in self.active_tool_calls.items():
                    with st.expander(f"Tool Call {idx}: {display.name}", expanded=True):
                        col1, col2 = st.columns([1, 3])

                        with col1:
                            if display.status == ToolCallStatus.BUILDING:
                                st.markdown("🔄 **Building**")
                            elif display.status == ToolCallStatus.COMPLETE:
                                st.markdown("✅ **Complete**")
                            elif display.status == ToolCallStatus.ERROR:
                                st.markdown("❌ **Error**")

                        with col2:
                            if display.status == ToolCallStatus.COMPLETE and display.final_args:
                                st.json(display.final_args)
                            elif display.status == ToolCallStatus.ERROR and display.error_message:
                                st.error(display.error_message)
                            else:
                                st.code(display.args_preview, language="json")

    def _update_history_display(self):
        """Update the historical tool calls display in Streamlit."""
        if not self.history_container or not self.historical_tool_calls:
            return

        with self.history_container.container():
            st.markdown("### 📚 Tool Call History")

            # Group by iteration
            iterations = {}
            for call in self.historical_tool_calls:
                iter_num = call["iteration"]
                if iter_num not in iterations:
                    iterations[iter_num] = []
                iterations[iter_num].append(call)

            for iter_num, calls in iterations.items():
                with st.expander(f"🔄 Iteration {iter_num} ({len(calls)} tool calls)", expanded=False):
                    for call in calls:
                        st.markdown(f"**{call['name']}** (Index {call['index']})")
                        if call["args"]:
                            st.json(call["args"])
                        st.markdown("---")

    def create_parser(self) -> StreamingGraphParser:
        """Create a streaming parser configured for Streamlit."""
        self.parser = StreamingGraphParser(
            on_content_update=self._on_content_update,
            on_tool_call_start=self._on_tool_call_start,
            on_tool_call_update=self._on_tool_call_update,
            on_tool_call_complete=self._on_tool_call_complete,
            on_iteration_start=self._on_iteration_start,
        )
        return self.parser

    def reset_session(self):
        """Reset the streaming session."""
        self.active_tool_calls.clear()
        self.historical_tool_calls.clear()
        self.current_iteration = 0
        self.content = ""
        if self.parser:
            self.parser.reset()

        # Clear session state
        st.session_state.streaming_content = ""
        st.session_state.streaming_tool_calls = {}
        st.session_state.streaming_history = []
        st.session_state.current_iteration = 0

        # Clear containers
        if self.content_container:
            self.content_container.empty()
        if self.tool_calls_container:
            self.tool_calls_container.empty()
        if self.history_container:
            self.history_container.empty()

    def get_final_summary(self) -> Dict[str, Any]:
        """Get a summary of the completed streaming session."""
        # Current iteration completed calls
        current_completed_calls = []
        for display in self.active_tool_calls.values():
            if display.status == ToolCallStatus.COMPLETE:
                current_completed_calls.append(
                    {
                        "name": display.name,
                        "args": display.final_args,
                        "id": display.call_id,
                        "iteration": self.current_iteration,
                    }
                )

        # All completed calls (historical + current)
        all_completed_calls = self.historical_tool_calls + current_completed_calls

        return {
            "final_content": self.content,
            "current_iteration_calls": current_completed_calls,
            "historical_calls": self.historical_tool_calls,
            "all_completed_calls": all_completed_calls,
            "total_iterations": self.current_iteration + 1,
            "total_tool_calls": len(all_completed_calls),
        }


# Convenience functions for Streamlit integration


def create_streaming_chat_interface() -> StreamlitStreamingService:
    """Create a complete streaming chat interface for Streamlit."""
    service = StreamlitStreamingService()
    service.initialize_ui_containers()
    return service


def display_streaming_progress(service: StreamlitStreamingService):
    """Display streaming progress indicators."""
    if service.active_tool_calls:
        progress_text = f"Processing {len(service.active_tool_calls)} tool calls..."
        building_count = sum(1 for d in service.active_tool_calls.values() if d.status == ToolCallStatus.BUILDING)

        if building_count > 0:
            st.info(f"🔄 {progress_text} ({building_count} in progress)")
        else:
            st.success("✅ All tool calls completed!")


# Example usage for Streamlit apps
def example_streamlit_integration():
    """Example of how to integrate streaming with a Streamlit app."""
    st.title("🤖 LangGraph Streaming Demo")

    # Initialize streaming service
    if "streaming_service" not in st.session_state:
        st.session_state.streaming_service = create_streaming_chat_interface()

    service = st.session_state.streaming_service

    # User input
    user_input = st.text_input("Ask a question:", key="user_input")

    if st.button("Send", key="send_button"):
        if user_input:
            # Reset for new session
            service.reset_session()

            # Create parser
            parser = service.create_parser()

            # Here you would integrate with your LangGraph streaming
            st.info("This is where you'd integrate with your LangGraph streaming...")

            # Example of simulated streaming (replace with actual graph streaming)
            # async for mode, chunk in graph.astream(...):
            #     if mode == "messages" and isinstance(chunk[0], BaseMessage):
            #         parser.process_chunk(chunk[0])

    # Display progress
    display_streaming_progress(service)

    # Show final summary if available
    if st.button("Show Summary"):
        summary = service.get_final_summary()
        st.json(summary)
