"""Simple conversational chat interface using ConversationalStreamAdapter.

Phase 2: Clean, simple chat that leverages the new conversational streaming architecture
built in Phase 1. Starts with basic message streaming and builds from there.
"""

import asyncio
import uuid
from typing import Any, Optional

import streamlit as st
from frontend.services.conversational_stream_adapter import (
    get_avatar,
    get_speaker_for_namespace,
    get_tool_status_display,
)
from frontend.services.stream_processor_integration import (
    ConversationalStreamProcessor,
    create_simple_conversational_processor,
)
from langchain_core.messages import HumanMessage


def render_chat_interface():
    """Render the main conversational chat interface."""
    # Initialize session
    _init_chat_session()

    # Header
    _render_header()

    # Check if we have both a model and a graph
    has_model = "current_model" in st.session_state
    has_graph = "current_graph" in st.session_state

    if has_model and has_graph:
        st.markdown(
            f"<span style='font-size:0.95em;'>"
            f"🟢 <b>{st.session_state.current_provider}</b> &nbsp;|&nbsp; "
            f"🧠 <b>{st.session_state.current_graph_info.name}</b> &nbsp;|&nbsp; "
            f"🧵 <code>{st.session_state.thread_id}</code>"
            f"</span>",
            unsafe_allow_html=True,
        )

        # Main chat area using conversational streaming
        _render_conversational_chat()

    elif not has_model:
        st.info("👈 Please configure a provider in the sidebar and test the connection to start chatting!")
    elif not has_graph:
        st.info("👈 Please select an AI agent in the sidebar to start chatting!")
    else:
        st.error("Unexpected state - please refresh the page")

    # Add debug section in development
    with st.expander("🔧 Development Debug Tools", expanded=False):
        _show_debug_info()

        if st.button("🧪 Add Test Messages"):
            _add_test_messages()

        st.subheader("Message Architecture V2 Info")
        st.info("""
        **Architecture V2: Sequential Message Flow**
        - Data Layer: ConversationalStreamAdapter updates st.session_state.messages
        - UI Layer: Chat Component renders messages chronologically  
        - Message types: user, ai, tool_call, artifact
        - Real-time: Adapter updates session state during streaming
        """)


def _render_header():
    """Render the header with clear conversation button."""
    col1, col2 = st.columns([4, 1])
    with col1:
        st.header("💬 Conversational AI Chat")
    with col2:
        if st.button("🗑️ Clear", help="Clear conversation history"):
            _clear_conversation()
            st.rerun()


def _render_conversational_chat():
    """Render conversation from st.session_state.messages in chronological order."""

    # Display all historical messages from session state
    for message in st.session_state.messages:
        if message["role"] == "user":
            _render_user_message(message)
        elif message["role"] == "ai":
            _render_ai_message(message)
        elif message["role"] == "tool_call":
            _render_tool_call(message)
        elif message["role"] == "artifact":
            _render_artifact_message(message)

    # Handle new user input
    if prompt := st.chat_input("What would you like to ask?"):
        # Add user message to session state
        st.session_state.messages.append(
            {
                "role": "user",
                "content": prompt,
                "timestamp": str(uuid.uuid4()),  # Simple ID for user messages
            }
        )

        # Display user message immediately
        with st.chat_message("user"):
            st.markdown(prompt)

        # Start streaming (adapter will update session state)
        _stream_conversational_response(prompt)


def _render_user_message(message):
    """Render user message."""
    with st.chat_message("user"):
        st.markdown(message["content"])


def _render_ai_message(message):
    """Render AI message with proper speaker identification."""
    # Determine speaker and avatar from namespace
    speaker = get_speaker_for_namespace(message.get("namespace", "main"))
    avatar = get_avatar(speaker)

    with st.chat_message("assistant", avatar=avatar):
        # Speaker identification (if not main AI)
        if speaker != "AI":
            st.caption(f"🤖 {speaker} !")

        # Message content
        st.markdown(message["content"])

        # Display artifacts if present
        if "artifacts" in message and message["artifacts"]:
            _render_inline_artifacts(message["artifacts"])


def _render_tool_call(message):
    """Render tool call as inline work indicator."""
    # Tool status display
    tool_display = get_tool_status_display(message)
    st.caption(tool_display)

    # Expandable result for completed tools with results
    if message["status"] == "result_success" and message.get("result"):
        result_content = message["result"]["content"]
        result_text = str(result_content)

        if len(result_text) > 100:  # Show in expander for long results
            with st.expander(f"View {message['name']} full result", expanded=False):
                if isinstance(result_content, dict) or isinstance(result_content, list):
                    st.json(result_content)
                else:
                    st.text(result_text)
        else:
            # Show short results inline
            st.caption(f"Result: {result_text}")

    # Show error details for failed tools
    elif message["status"] == "result_error" and message.get("result"):
        with st.expander(f"Error details for {message['name']}", expanded=False):
            st.error(str(message["result"]))


def _render_artifact_message(message):
    """Render standalone artifact message."""
    # Determine speaker from namespace
    speaker = get_speaker_for_namespace(message.get("namespace", "main"))
    avatar = get_avatar(speaker)

    with st.chat_message("assistant", avatar=avatar):
        if speaker != "AI":
            st.caption(f"🤖 {speaker}")

        st.info(f"📋 Created {message['artifact_type']}")
        # Could expand this to show artifact content based on type
        if st.button(f"View {message['artifact_type']}", key=f"artifact_{message.get('timestamp', 'unknown')}"):
            st.json(message["artifact_data"])


def _render_inline_artifacts(artifacts):
    """Render artifacts inline with AI message."""
    with st.expander(f"📋 {len(artifacts)} Artifact(s)", expanded=False):
        for i, artifact in enumerate(artifacts):
            st.subheader(f"📋 {artifact['type']}")
            st.json(artifact["data"])
            if i < len(artifacts) - 1:
                st.divider()


def _stream_conversational_response(user_input: str):
    """Stream AI response using the conversational streaming architecture."""
    try:
        # Get or create conversational processor
        if "conversational_processor" not in st.session_state:
            st.session_state.conversational_processor = create_simple_conversational_processor()

        processor = st.session_state.conversational_processor

        # Reset processor for new conversation turn
        processor.reset_session()

        # Prepare graph input
        input_state = {"messages": [HumanMessage(content=user_input)], "artifacts": [], "research_iteration": 0}

        config = {"configurable": {"thread_id": st.session_state.thread_id}}

        # Run streaming in an async context
        asyncio.run(_run_streaming_conversation(processor, input_state, config))

        # After streaming completes, trigger rerun to show final state
        # The adapter has already updated st.session_state.messages during streaming
        st.rerun()

    except Exception as e:
        st.error(f"Error in conversational streaming: {str(e)}")
        st.exception(e)


async def _run_streaming_conversation(
    processor: ConversationalStreamProcessor, input_state: dict[str, Any], config: dict[str, Any]
) -> Optional[str]:
    """Run the conversational streaming process."""
    try:
        graph = st.session_state.current_graph

        # Process streaming events
        async for event in processor.stream_with_conversation(graph, input_state, config):
            pass

    except Exception as e:
        st.error(f"Error during streaming: {str(e)}")
        return None


def _init_chat_session():
    """Initialize chat session state."""
    if "thread_id" not in st.session_state:
        st.session_state.thread_id = str(uuid.uuid4())
        st.session_state.user_id = "demo_user"

    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "conversational_processor" not in st.session_state:
        st.session_state.conversational_processor = create_simple_conversational_processor()


def _clear_conversation():
    """Clear the conversation and reset session."""
    st.session_state.messages = []
    st.session_state.thread_id = str(uuid.uuid4())

    # Reset conversational processor
    if "conversational_processor" in st.session_state:
        st.session_state.conversational_processor.reset_session()


# Debugging utilities
def _show_debug_info():
    """Show debug information about current conversation state."""
    if st.button("🔍 Debug: Show Message State"):
        st.subheader("Current Message State")
        st.json(st.session_state.messages)

        if "conversational_processor" in st.session_state:
            adapter = st.session_state.conversational_processor.get_adapter()
            summary = adapter.get_conversation_summary()
            st.subheader("Conversation Summary")
            st.json(summary)


def _add_test_messages():
    """Add test messages to verify the rendering works correctly."""
    test_messages = [
        {
            "role": "user",
            "content": "Analyze this data and create a comprehensive report",
            "timestamp": "2024-01-01T10:00:00",
        },
        {
            "id": "msg_2",
            "namespace": "main",
            "role": "ai",
            "content": "I'll help you analyze the data and create a comprehensive report for you...",
            "timestamp": "2024-01-01T10:00:01",
        },
        {
            "namespace": "main",
            "message_id": "msg_2",
            "tool_call_id": "call_123",
            "role": "tool_call",
            "name": "think_tool",
            "status": "result_success",
            "args": {"reflection": "The user is asking me to analyze data..."},
            "result": "Reflection complete - proceeding with analysis",
            "timestamp": "2024-01-01T10:00:02",
        },
        {
            "namespace": "main",
            "message_id": "msg_2",
            "tool_call_id": "call_456",
            "role": "tool_call",
            "name": "analysis_agent",
            "status": "args_streaming",
            "args": None,
            "result": None,
            "timestamp": "2024-01-01T10:00:03",
        },
        {
            "id": "msg_3",
            "namespace": "analysis_agent:task_123",
            "role": "ai",
            "content": "Analyzing the data now... I've found several interesting patterns in the data. Analysis complete! Key findings: correlation coefficient 0.85, 3 main clusters identified.",
            "timestamp": "2024-01-01T10:00:04",
        },
        {
            "namespace": "analysis_agent:task_123",
            "message_id": "msg_3",
            "tool_call_id": "call_789",
            "role": "tool_call",
            "name": "data_processor",
            "status": "result_success",
            "args": {"query": "deep analysis"},
            "result": "covariance: 12.5, variance: 8.2, trends: upward",
            "timestamp": "2024-01-01T10:00:05",
        },
        {
            "id": "msg_4",
            "namespace": "main",
            "role": "ai",
            "content": "Here's your comprehensive analysis based on the detailed processing: The data shows strong correlation (0.85) with 3 distinct clusters and an upward trend. Covariance of 12.5 indicates significant relationships between variables.",
            "artifacts": [
                {
                    "type": "AnalysisReport",
                    "data": {"correlation": 0.85, "clusters": 3, "trend": "upward"},
                    "namespace": "main",
                    "timestamp": "2024-01-01T10:00:06",
                }
            ],
            "timestamp": "2024-01-01T10:00:06",
        },
    ]

    # Add test messages to session state
    st.session_state.messages.extend(test_messages)
    st.success(f"Added {len(test_messages)} test messages demonstrating the sequential conversation flow!")
    st.rerun()

    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
