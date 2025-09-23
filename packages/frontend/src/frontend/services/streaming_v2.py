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
    """Handler for async chunk-based streaming with in-place tool updates."""

    def __init__(self):
        """Initialize the streaming handler."""
        self.active_tools: Dict[str, ToolCallInfo] = {}
        self.current_response = ""
        self.artifacts = []

        # Streaming messages (temporary during streaming)
        self.streaming_messages: List[Dict[str, Any]] = []

        # Track tool message indices for in-place updates
        self.tool_message_indices: Dict[str, int] = {}

        # Track all tool executions for summary
        self.all_tool_executions: List[Dict[str, Any]] = []

        # Track processed tool call IDs to avoid duplicates
        self.processed_tool_call_ids: Set[str] = set()
        self.processed_tool_result_ids: Set[str] = set()

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

                elif message["role"] == "tool_execution":
                    with st.chat_message("assistant"):
                        st.markdown(message["content"])

                        # Show execution status
                        if message.get("status") == "executing":
                            st.info("⚙️ Executing...")
                        elif message.get("status") == "completed":
                            # Show result preview if available
                            if message.get("result_preview"):
                                st.success(f"Result: {message['result_preview']}")

    def _get_tool_icon(self, tool_info: ToolCallInfo) -> str:
        """Get appropriate icon for tool type."""
        if tool_info.is_agent:
            return "🤖"
        elif "think" in tool_info.name.lower():
            return "🧠"
        else:
            return "⚙️"

    def _add_tool_call_message(self, tool_info: ToolCallInfo):
        """Add initial tool execution message."""
        icon = self._get_tool_icon(tool_info)
        content = f"{icon} **{tool_info.name}** ⚙️ Executing..."

        # Add args preview
        if tool_info.args:
            args_preview = str(tool_info.args)
            if len(args_preview) > 100:
                args_preview = args_preview[:100] + "..."
            content += f"\n```json\n{args_preview}\n```"

        message = {
            "role": "tool_execution",
            "content": content,
            "tool_name": tool_info.name,
            "tool_id": tool_info.call_id,
            "status": "executing",
            "args": tool_info.args,
        }

        # Add message and track its index
        message_index = len(self.streaming_messages)
        self.streaming_messages.append(message)
        self.tool_message_indices[tool_info.call_id] = message_index

        # Track for summary
        self.all_tool_executions.append(
            {
                "tool_id": tool_info.call_id,
                "name": tool_info.name,
                "args": tool_info.args,
                "icon": icon,
                "status": "executing",
            }
        )

        self._update_streaming_display()

    def _update_tool_result_message(self, tool_info: ToolCallInfo):
        """Update existing tool message with result."""
        tool_id = tool_info.call_id

        if tool_id not in self.tool_message_indices:
            return

        message_index = self.tool_message_indices[tool_id]
        if message_index >= len(self.streaming_messages):
            return

        # Update the existing message
        message = self.streaming_messages[message_index]
        icon = self._get_tool_icon(tool_info)

        if tool_info.status == ToolStatus.COMPLETED:
            # Update content to show completion
            base_content = f"{icon} **{tool_info.name}** ✅ Completed"

            # Add args
            if tool_info.args:
                args_preview = str(tool_info.args)
                if len(args_preview) > 100:
                    args_preview = args_preview[:100] + "..."
                base_content += f"\n```json\n{args_preview}\n```"

            message["content"] = base_content
            message["status"] = "completed"

            # Add result preview
            if tool_info.result:
                result_preview = str(tool_info.result)
                if len(result_preview) > 150:
                    result_preview = result_preview[:150] + "..."
                message["result_preview"] = result_preview
                message["full_result"] = tool_info.result
        else:
            # Handle error case
            message["content"] = f"{icon} **{tool_info.name}** ❌ Failed"
            message["status"] = "failed"
            if tool_info.error:
                message["error"] = tool_info.error

        # Update tool execution tracking
        for exec_item in self.all_tool_executions:
            if exec_item["tool_id"] == tool_id:
                exec_item["status"] = "completed" if tool_info.status == ToolStatus.COMPLETED else "failed"
                exec_item["result"] = tool_info.result
                break

        self._update_streaming_display()

    def process_chunk(self, chunk: Dict[str, Any]):
        """Process a streaming chunk and update display in real-time."""
        try:
            if "messages" in chunk and chunk["messages"]:
                messages = chunk["messages"]

                # Process messages looking for new tool calls and pending tool results
                for message in messages:
                    # Handle AI message with potential tool calls
                    if isinstance(message, AIMessage):
                        # Update current response content (only from the latest AI message)
                        if message.content and message.content != self.current_response:
                            self.current_response = message.content

                            # Update the last assistant message or add new one
                            if self.streaming_messages and self.streaming_messages[-1]["role"] == "assistant":
                                self.streaming_messages[-1]["content"] = self.current_response
                            else:
                                self.streaming_messages.append({"role": "assistant", "content": self.current_response})

                        # Handle tool calls - only process NEW tool call IDs
                        if hasattr(message, "tool_calls") and message.tool_calls:
                            for tool_call in message.tool_calls:
                                tool_call_id = tool_call.get("id")
                                if (
                                    tool_call_id
                                    and tool_call_id not in self.processed_tool_call_ids
                                    and tool_call_id not in self.active_tools
                                ):
                                    # Mark as processed
                                    self.processed_tool_call_ids.add(tool_call_id)

                                    tool_info = ToolCallInfo(
                                        call_id=tool_call_id,
                                        name=tool_call.get("name", "unknown_tool"),
                                        args=tool_call.get("args", {}),
                                        status=ToolStatus.EXECUTING,
                                    )
                                    self.active_tools[tool_call_id] = tool_info
                                    self._add_tool_call_message(tool_info)

                    # Handle tool message (tool result) - only process NEW results for PENDING tools
                    elif isinstance(message, ToolMessage):
                        tool_id = message.tool_call_id
                        if tool_id and tool_id not in self.processed_tool_result_ids and tool_id in self.active_tools:
                            # Mark result as processed
                            self.processed_tool_result_ids.add(tool_id)

                            tool_info = self.active_tools[tool_id]
                            tool_info.status = ToolStatus.COMPLETED
                            tool_info.result = message.content

                            # Update existing tool message with result
                            self._update_tool_result_message(tool_info)

                            # Remove from active tools
                            del self.active_tools[tool_id]

                # Update display after processing all messages
                self._update_streaming_display()

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
        """Finalize streaming and add results to permanent chat history."""

        # Add tool execution summary as a separate message (only if tools were used)
        if self.all_tool_executions:
            # Add tool summary as a message with full results for expandable sections
            tool_summary_message = {
                "role": "assistant",
                "tool_summary": True,
                "content": "### 🔧 Tool Execution Summary",
                "tool_executions": self.all_tool_executions,  # For detailed expandable view
            }
            st.session_state.messages.append(tool_summary_message)
            # Add final assistant response to session state
        if self.current_response:
            message_data = {"role": "assistant", "content": self.current_response}
            if self.artifacts:
                message_data["artifacts"] = self.artifacts
            st.session_state.messages.append(message_data)

        # Clear streaming display and show completion
        if self.streaming_container:
            self.streaming_container.empty()
            with self.streaming_container.container():
                st.success("✅ **Streaming completed** - Results added to chat history")
                st.info("👆 Check the chat above for the complete response and tool execution details")

    def get_final_result(self) -> Dict[str, Any]:
        """Get the final streaming result."""
        return {
            "response": self.current_response,
            "artifacts": self.artifacts,
            "total_tools": len(self.all_tool_executions),
        }

    def reset(self):
        """Reset the handler for a new streaming session."""
        self.active_tools.clear()
        self.current_response = ""
        self.artifacts = []
        self.streaming_messages.clear()
        self.tool_message_indices.clear()
        self.all_tool_executions.clear()
        self.processed_tool_call_ids.clear()
        self.processed_tool_result_ids.clear()


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
