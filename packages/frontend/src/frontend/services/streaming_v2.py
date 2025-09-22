"""Advanced streaming service for async chunk-based streaming in Streamlit.

This module provides utilities for handling async LangGraph streaming
with real-time UI updates for tool calls and workflow progress.
Designed to complement the existing token-based streaming service.
"""

import asyncio
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Set

import streamlit as st
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage


class ToolStatus(Enum):
    """Status of a tool call execution."""

    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ToolCallInfo:
    """Information about a tool call for UI display."""

    call_id: str
    name: str
    args: Dict[str, Any]
    status: ToolStatus
    result: Optional[str] = None
    error: Optional[str] = None
    is_agent: bool = False

    def __post_init__(self):
        """Detect if this is an agent tool call."""
        self.is_agent = "agent" in self.name.lower()


class AsyncStreamingHandler:
    """Handler for async chunk-based streaming with progressive UI updates."""

    def __init__(self):
        """Initialize the streaming handler."""
        self.active_tools: Dict[str, ToolCallInfo] = {}
        self.completed_tools: List[ToolCallInfo] = []
        self.current_response = ""
        self.artifacts = []

        # UI containers
        self.response_container = None
        self.tools_container = None
        self.progress_container = None

    def initialize_ui_containers(self):
        """Initialize Streamlit containers for progressive updates."""
        self.response_container = st.empty()
        self.tools_container = st.empty()
        self.progress_container = st.empty()

    def _get_tool_icon(self, tool_info: ToolCallInfo) -> str:
        """Get appropriate icon for tool type."""
        if tool_info.is_agent:
            return "🤖"
        elif "think" in tool_info.name.lower():
            return "🧠"
        else:
            return "⚙️"

    def _get_status_indicator(self, status: ToolStatus) -> str:
        """Get status indicator for tool status."""
        status_map = {
            ToolStatus.PENDING: "⏳",
            ToolStatus.EXECUTING: "🔄",
            ToolStatus.COMPLETED: "✅",
            ToolStatus.FAILED: "❌",
        }
        return status_map.get(status, "❓")

    def _update_response_display(self):
        """Update the main response display."""
        if self.response_container and self.current_response:
            with self.response_container.container():
                st.markdown(self.current_response)

    def _update_tools_display(self):
        """Update the tools execution display."""
        if not self.tools_container:
            return

        with self.tools_container.container():
            if self.active_tools or self.completed_tools:
                st.markdown("### 🔧 Tool Execution Status")

                # Show active tools
                if self.active_tools:
                    st.markdown("**Active:**")
                    for tool_info in self.active_tools.values():
                        icon = self._get_tool_icon(tool_info)
                        status_icon = self._get_status_indicator(tool_info.status)

                        col1, col2, col3 = st.columns([1, 3, 1])
                        with col1:
                            st.markdown(f"{icon} {status_icon}")
                        with col2:
                            st.markdown(f"**{tool_info.name}**")
                        with col3:
                            if tool_info.status == ToolStatus.EXECUTING:
                                st.markdown("🔄")

                        # Show args in expandable section
                        if tool_info.args:
                            with st.expander(f"Args for {tool_info.name}", expanded=False):
                                st.json(tool_info.args)

                # Show recently completed tools
                if self.completed_tools:
                    st.markdown("**Recently Completed:**")
                    for tool_info in self.completed_tools[-3:]:  # Show last 3
                        icon = self._get_tool_icon(tool_info)
                        status_icon = self._get_status_indicator(tool_info.status)

                        col1, col2 = st.columns([1, 3])
                        with col1:
                            st.markdown(f"{icon} {status_icon}")
                        with col2:
                            st.markdown(f"**{tool_info.name}**")

                        # Show result in expandable section
                        if tool_info.result:
                            with st.expander(f"Result from {tool_info.name}", expanded=False):
                                st.text(
                                    tool_info.result[:500] + "..." if len(tool_info.result) > 500 else tool_info.result
                                )

    def _update_progress_display(self):
        """Update the overall progress display."""
        if not self.progress_container:
            return

        total_tools = len(self.active_tools) + len(self.completed_tools)
        if total_tools > 0:
            completed = len(self.completed_tools)
            progress = completed / total_tools

            with self.progress_container.container():
                st.progress(progress, text=f"Progress: {completed}/{total_tools} tools completed")

    def process_chunk(self, chunk: Dict[str, Any]):
        """Process a streaming chunk and update UI accordingly."""
        try:
            if "messages" in chunk and chunk["messages"]:
                latest_message = chunk["messages"][-1]

                # Handle AI message with potential tool calls
                if isinstance(latest_message, AIMessage):
                    if latest_message.content:
                        self.current_response = latest_message.content
                        self._update_response_display()

                    # Handle tool calls
                    if hasattr(latest_message, "tool_calls") and latest_message.tool_calls:
                        for tool_call in latest_message.tool_calls:
                            tool_info = ToolCallInfo(
                                call_id=tool_call["id"],
                                name=tool_call["name"],
                                args=tool_call["args"],
                                status=ToolStatus.EXECUTING,
                            )
                            self.active_tools[tool_call["id"]] = tool_info

                        self._update_tools_display()
                        self._update_progress_display()

                # Handle tool message (tool result)
                elif isinstance(latest_message, ToolMessage):
                    tool_id = latest_message.tool_call_id
                    if tool_id in self.active_tools:
                        tool_info = self.active_tools[tool_id]
                        tool_info.status = ToolStatus.COMPLETED
                        tool_info.result = latest_message.content

                        # Move to completed
                        self.completed_tools.append(tool_info)
                        del self.active_tools[tool_id]

                        self._update_tools_display()
                        self._update_progress_display()

            # Handle artifacts
            if "artifacts" in chunk and chunk["artifacts"]:
                self.artifacts = chunk["artifacts"]

        except Exception as e:
            st.error(f"Error processing chunk: {str(e)}")

    async def stream_graph_async(self, graph, input_state, config, context):
        """Stream graph execution asynchronously with progressive updates."""
        try:
            async for chunk in graph.astream(input_state, config=config, context=context, stream_mode="values"):
                self.process_chunk(chunk)
                # Small delay to allow UI updates
                await asyncio.sleep(0.01)

        except Exception as e:
            st.error(f"Error during streaming: {str(e)}")
            raise

    def get_final_result(self) -> Dict[str, Any]:
        """Get the final streaming result."""
        return {
            "response": self.current_response,
            "artifacts": self.artifacts,
            "completed_tools": len(self.completed_tools),
            "total_tools": len(self.active_tools) + len(self.completed_tools),
        }

    def reset(self):
        """Reset the handler for a new streaming session."""
        self.active_tools.clear()
        self.completed_tools.clear()
        self.current_response = ""
        self.artifacts = []

        # Clear UI containers
        if self.response_container:
            self.response_container.empty()
        if self.tools_container:
            self.tools_container.empty()
        if self.progress_container:
            self.progress_container.empty()


def create_async_streaming_handler() -> AsyncStreamingHandler:
    """Create and initialize an async streaming handler."""
    handler = AsyncStreamingHandler()
    handler.initialize_ui_containers()
    return handler


def run_async_streaming(graph, input_state, config, context) -> Dict[str, Any]:
    """Run async streaming in a synchronous Streamlit context."""
    handler = create_async_streaming_handler()

    # Run async streaming in sync context
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(handler.stream_graph_async(graph, input_state, config, context))
        return handler.get_final_result()
    finally:
        loop.close()
