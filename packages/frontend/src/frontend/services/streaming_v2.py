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
    result: Optional[Any] = None
    error: Optional[str] = None
    is_agent: bool = False

    def __post_init__(self):
        """Detect if this is an agent tool call."""
        self.is_agent = "agent" in self.name.lower()


class AsyncStreamingHandler:
    """Handler for async chunk-based streaming with chat flow integration."""

    def __init__(self):
        """Initialize the streaming handler."""
        self.active_tools: Dict[str, ToolCallInfo] = {}
        self.current_response = ""
        self.artifacts = []

        # Streaming messages (temporary during streaming)
        self.streaming_messages: List[Dict[str, Any]] = []

        # UI containers for real-time streaming display
        self.streaming_container = None

    def initialize_streaming_display(self):
        """Initialize the streaming display container."""
        st.markdown("🚀 **Supervisor Agent - Live Streaming**")
        self.streaming_container = st.empty()

    def _update_streaming_display(self):
        """Update the streaming display in real-time."""
        if not self.streaming_container:
            return

        with self.streaming_container.container():
            for i, message in enumerate(self.streaming_messages):
                if message["role"] == "assistant":
                    with st.chat_message("assistant"):
                        st.markdown(message["content"])

                elif message["role"] == "tool_call":
                    with st.chat_message("assistant"):
                        st.markdown(message["content"])
                        if message.get("status") == "executing":
                            st.info(f"⚙️ Executing {message.get('tool_name', 'tool')}...")

                elif message["role"] == "tool_result":
                    with st.chat_message("assistant"):
                        st.markdown(message["content"])

                        # Add expandable section for full result if available
                        if message.get("full_result") and len(str(message["full_result"])) > 200:
                            with st.expander("View full result", expanded=False):
                                st.text(str(message["full_result"]))

    def _get_tool_icon(self, tool_info: ToolCallInfo) -> str:
        """Get appropriate icon for tool type."""
        if tool_info.is_agent:
            return "🤖"
        elif "think" in tool_info.name.lower():
            return "🧠"
        else:
            return "⚙️"

    def _add_tool_call_message(self, tool_info: ToolCallInfo):
        """Add tool call announcement to streaming display."""
        icon = self._get_tool_icon(tool_info)
        content = f"{icon} **Calling {tool_info.name}**"

        # Add args preview if available
        if tool_info.args:
            args_preview = str(tool_info.args)
            if len(args_preview) > 100:
                args_preview = args_preview[:100] + "..."
            content += f"\n```json\n{args_preview}\n```"

        message = {
            "role": "tool_call",
            "content": content,
            "tool_name": tool_info.name,
            "tool_id": tool_info.call_id,
            "status": "executing",
        }

        self.streaming_messages.append(message)
        self._update_streaming_display()

    def _add_tool_result_message(self, tool_info: ToolCallInfo):
        """Add tool result to streaming display."""
        icon = self._get_tool_icon(tool_info)

        if tool_info.status == ToolStatus.COMPLETED:
            content = f"✅ **{tool_info.name} completed**"
            if tool_info.result:
                # Show preview of result
                result_preview = str(tool_info.result)
                if len(result_preview) > 200:
                    result_preview = result_preview[:200] + "..."
                content += f"\n\n{result_preview}"
        else:
            content = f"❌ **{tool_info.name} failed**"
            if tool_info.error:
                content += f"\n\nError: {tool_info.error}"

        message = {
            "role": "tool_result",
            "content": content,
            "tool_name": tool_info.name,
            "tool_id": tool_info.call_id,
            "full_result": tool_info.result,
            "status": "completed",
        }

        self.streaming_messages.append(message)
        self._update_streaming_display()

    def process_chunk(self, chunk: Dict[str, Any]):
        """Process a streaming chunk and update display in real-time."""
        try:
            if "messages" in chunk and chunk["messages"]:
                latest_message = chunk["messages"][-1]

                # Handle AI message with potential tool calls
                if isinstance(latest_message, AIMessage):
                    # Update current response content
                    if latest_message.content and latest_message.content != self.current_response:
                        self.current_response = latest_message.content

                        # Update the last assistant message or add new one
                        if self.streaming_messages and self.streaming_messages[-1]["role"] == "assistant":
                            self.streaming_messages[-1]["content"] = self.current_response
                        else:
                            self.streaming_messages.append({"role": "assistant", "content": self.current_response})

                        self._update_streaming_display()

                    # Handle tool calls - add them to streaming display
                    if hasattr(latest_message, "tool_calls") and latest_message.tool_calls:
                        for tool_call in latest_message.tool_calls:
                            # Only add if not already added and has valid id
                            tool_call_id = tool_call.get("id")
                            if tool_call_id and tool_call_id not in self.active_tools:
                                tool_info = ToolCallInfo(
                                    call_id=tool_call_id,
                                    name=tool_call.get("name", "unknown_tool"),
                                    args=tool_call.get("args", {}),
                                    status=ToolStatus.EXECUTING,
                                )
                                self.active_tools[tool_call_id] = tool_info
                                self._add_tool_call_message(tool_info)

                # Handle tool message (tool result)
                elif isinstance(latest_message, ToolMessage):
                    tool_id = latest_message.tool_call_id
                    if tool_id and tool_id in self.active_tools:
                        tool_info = self.active_tools[tool_id]
                        tool_info.status = ToolStatus.COMPLETED
                        tool_info.result = latest_message.content

                        # Add result to streaming display
                        self._add_tool_result_message(tool_info)

                        # Remove from active tools
                        del self.active_tools[tool_id]

            # Handle artifacts
            if "artifacts" in chunk and chunk["artifacts"]:
                self.artifacts = chunk["artifacts"]
                # Add artifacts to the last assistant message
                if self.streaming_messages and self.streaming_messages[-1]["role"] == "assistant":
                    self.streaming_messages[-1]["artifacts"] = self.artifacts
                    self._update_streaming_display()

        except Exception as e:
            st.error(f"Error processing chunk: {str(e)}")

    async def stream_graph_async(self, graph, input_state, config, context):
        """Stream graph execution asynchronously with real-time display."""
        try:
            async for chunk in graph.astream(input_state, config=config, context=context, stream_mode="values"):
                self.process_chunk(chunk)
                # Small delay to allow UI updates
                await asyncio.sleep(0.1)

        except Exception as e:
            st.error(f"Error during streaming: {str(e)}")
            raise

    def finalize_streaming(self):
        """Transfer streaming messages to session state and clean up."""
        # Add all streaming messages to session state
        st.session_state.messages.extend(self.streaming_messages)

        # Clear streaming display
        if self.streaming_container:
            self.streaming_container.empty()

        # Show completion message
        st.success(f"✅ **Completed** - {len(self.streaming_messages)} messages processed")

    def get_final_result(self) -> Dict[str, Any]:
        """Get the final streaming result."""
        return {
            "response": self.current_response,
            "artifacts": self.artifacts,
            "total_messages": len(self.streaming_messages),
        }

    def reset(self):
        """Reset the handler for a new streaming session."""
        self.active_tools.clear()
        self.current_response = ""
        self.artifacts = []
        self.streaming_messages.clear()


def create_async_streaming_handler() -> AsyncStreamingHandler:
    """Create and initialize an async streaming handler."""
    handler = AsyncStreamingHandler()
    handler.initialize_streaming_display()
    return handler


def run_async_streaming(graph, input_state, config, context) -> Dict[str, Any]:
    """Run async streaming in a synchronous Streamlit context with real-time display."""
    handler = create_async_streaming_handler()

    # Run async streaming in sync context
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(handler.stream_graph_async(graph, input_state, config, context))

        # Finalize streaming - transfer to session state
        handler.finalize_streaming()

        return handler.get_final_result()
    finally:
        loop.close()
