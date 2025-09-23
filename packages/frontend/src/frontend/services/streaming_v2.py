"""Advanced streaming service for async chunk-based streaming in Streamlit.

This module provides utilities for handling async LangGraph streaming
with real-time UI updates for tool calls and workflow progress.
Designed to complement the existing token-based streaming service.
"""

import asyncio
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Set

import streamlit as st
from langchain_core.messages import AIMessage, ToolMessage

from frontend.utils.formatting import beautify_tool_name


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

        # Turn scoping: prevent showing previous-turn content until new turn starts
        self.previous_assistant_content: Optional[str] = None
        self.current_turn_started: bool = False

    def initialize_streaming_display(self):
        """Initialize the streaming display container."""
        st.markdown("🚀 **Agent - Live Streaming**")
        self.streaming_container = st.empty()
        # Ensure starting from a clean container for this session
        self.streaming_container.empty()

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
        beautiful_name = beautify_tool_name(tool_info.name)
        content = f"{icon} **{beautiful_name}** ⚙️ Executing..."

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
            beautiful_name = beautify_tool_name(tool_info.name)
            base_content = f"{icon} **{beautiful_name}** ✅ Completed"

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
            beautiful_name = beautify_tool_name(tool_info.name)
            message["content"] = f"{icon} **{beautiful_name}** ❌ Failed"
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

                # Consider only the latest AI message to avoid replaying history
                latest_ai_message = None
                for _m in reversed(messages):
                    if isinstance(_m, AIMessage):
                        latest_ai_message = _m
                        break

                # Handle the latest AI message
                if latest_ai_message is not None:
                    content_text = str(latest_ai_message.content) if latest_ai_message.content is not None else ""
                    content_text = content_text.strip()

                    # Determine if a new turn has actually started
                    if not self.current_turn_started:
                        has_new_tool_calls = bool(getattr(latest_ai_message, "tool_calls", None))
                        is_same_as_previous = bool(
                            self.previous_assistant_content
                            and content_text
                            and content_text == str(self.previous_assistant_content).strip()
                        )
                        if has_new_tool_calls or (content_text and not is_same_as_previous):
                            self.current_turn_started = True

                    # Update assistant content only once the new turn has started
                    if self.current_turn_started and content_text and content_text != self.current_response:
                        self.current_response = content_text

                        if self.streaming_messages and self.streaming_messages[-1]["role"] == "assistant":
                            self.streaming_messages[-1]["content"] = self.current_response
                        else:
                            self.streaming_messages.append({"role": "assistant", "content": self.current_response})

                    # Handle tool calls - gate by cross-turn seen set to avoid duplicates
                    if hasattr(latest_ai_message, "tool_calls") and latest_ai_message.tool_calls:
                        for tool_call in latest_ai_message.tool_calls:
                            tool_call_id = tool_call.get("id")
                            if (
                                tool_call_id
                                and tool_call_id not in self.processed_tool_call_ids
                                and tool_call_id not in self.active_tools
                                and tool_call_id not in st.session_state.get("seen_tool_call_ids", set())
                            ):
                                # Ensure the turn is started when a tool call appears
                                self.current_turn_started = True

                                # Mark as processed (local + global)
                                self.processed_tool_call_ids.add(tool_call_id)
                                if "seen_tool_call_ids" not in st.session_state:
                                    st.session_state.seen_tool_call_ids = set()
                                st.session_state.seen_tool_call_ids.add(tool_call_id)

                                tool_info = ToolCallInfo(
                                    call_id=tool_call_id,
                                    name=tool_call.get("name", "unknown_tool"),
                                    args=tool_call.get("args", {}),
                                    status=ToolStatus.EXECUTING,
                                )
                                self.active_tools[tool_call_id] = tool_info
                                self._add_tool_call_message(tool_info)

                # Process tool results only for currently active tools and unseen results
                for message in messages:
                    if isinstance(message, ToolMessage):
                        tool_id = message.tool_call_id
                        if (
                            tool_id
                            and tool_id not in self.processed_tool_result_ids
                            and tool_id in self.active_tools
                            and tool_id not in st.session_state.get("seen_tool_result_ids", set())
                        ):
                            # Mark result as processed (local + global)
                            self.processed_tool_result_ids.add(tool_id)
                            if "seen_tool_result_ids" not in st.session_state:
                                st.session_state.seen_tool_result_ids = set()
                            st.session_state.seen_tool_result_ids.add(tool_id)

                            tool_info = self.active_tools[tool_id]
                            tool_info.status = ToolStatus.COMPLETED
                            tool_info.result = message.content

                            self._update_tool_result_message(tool_info)
                            del self.active_tools[tool_id]

                # Update display after processing updates
                self._update_streaming_display()

            # Handle artifacts only after the turn has started
            if "artifacts" in chunk and chunk["artifacts"] and self.current_turn_started:
                # Store artifacts for final persisted message; avoid injecting into temporary streaming dicts
                self.artifacts = chunk["artifacts"]

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

        # Clean up any existing tool summaries to prevent duplication
        self._cleanup_old_tool_summaries()

        # Add tool execution summary as a separate message (only if tools were used)
        if self.all_tool_executions:
            # Add tool summary as a message with full results for expandable sections
            tool_summary_message = {
                "role": "assistant",
                "tool_summary": True,
                "content": "### 🔧 Tool Execution Summary",
                "tool_executions": self.all_tool_executions,  # For detailed expandable view
                "message_id": str(uuid.uuid4()),  # Add unique ID to prevent conflicts
            }
            st.session_state.messages.append(tool_summary_message)

        # Add final assistant response to session state
        if self.current_response:
            message_data: Dict[str, Any] = {
                "role": "assistant",
                "content": self.current_response,
                "message_id": str(uuid.uuid4()),  # Add unique ID
            }
            if self.artifacts:
                message_data["artifacts"] = self.artifacts
            st.session_state.messages.append(message_data)

        # Clear streaming display and show completion
        if self.streaming_container:
            self.streaming_container.empty()
            with self.streaming_container.container():
                st.success("✅ **Streaming completed** - Results added to chat history")
                st.info("👆 Check the chat above for the complete response and tool execution details")

    def _cleanup_old_tool_summaries(self):
        """Remove old tool summary messages to prevent duplication."""
        if "messages" in st.session_state:
            # Filter out old tool summary messages
            st.session_state.messages = [msg for msg in st.session_state.messages if not msg.get("tool_summary", False)]

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
        self.current_turn_started = False
        # Clear the streaming container if it exists
        if self.streaming_container:
            self.streaming_container.empty()


def create_async_streaming_handler() -> AsyncStreamingHandler:
    """Create and initialize an async streaming handler."""
    handler = AsyncStreamingHandler()
    handler.initialize_streaming_display()
    return handler


def run_async_streaming(graph, input_state, config, context) -> Dict[str, Any]:
    """Run async streaming in a synchronous Streamlit context with real-time display."""
    # Clear any existing streaming displays from previous interactions
    _clear_existing_streaming_displays()

    handler = create_async_streaming_handler()
    # Provide previous assistant content for turn scoping
    handler.previous_assistant_content = _get_last_assistant_message_content()

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


def _clear_existing_streaming_displays():
    """Clear any existing streaming displays from previous interactions."""
    streaming_keys = [
        "streaming_content",
        "streaming_tool_calls",
        "streaming_history",
        "current_iteration",
        "streaming_service",
    ]
    for key in streaming_keys:
        if key in st.session_state:
            del st.session_state[key]


# Helper to fetch last assistant message content from session history
def _get_last_assistant_message_content() -> Optional[str]:
    try:
        if "messages" in st.session_state and st.session_state.messages:
            for msg in reversed(st.session_state.messages):
                if msg.get("role") == "assistant" and not msg.get("tool_summary", False):
                    return str(msg.get("content", ""))
    except Exception:
        return None
    return None
