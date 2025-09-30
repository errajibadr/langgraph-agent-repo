"""Simple conversational chat interface with unified streaming service.

This chat component provides:
- Real-time conversational streaming with multi-namespace support
- Live container updates for concurrent agent execution
- Clean historical conversation rendering
"""

import asyncio
import uuid
from datetime import datetime

import streamlit as st
from frontend.services.streaming_service import create_streaming_service
from frontend.utils.chat_utils import get_avatar, get_speaker_for_namespace, get_tool_status_display
from frontend.utils.debug_utils import add_test_messages, show_debug_info
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
        show_debug_info()

        if st.button("🧪 Add Test Messages"):
            add_test_messages()

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
    """Render conversation from chat_history in chronological order."""

    # Display all historical messages from chat_history
    for message in st.session_state.chat_history:
        _render_messages(message)

    # Handle new user input
    if prompt := st.chat_input("What would you like to ask?"):
        # Start streaming (will use live container system)
        _stream_conversational_response(prompt)


def _render_messages(message):
    """Render message."""
    if message["role"] == "user":
        _render_user_message(message)
    elif message["role"] == "ai":
        _render_ai_message(message)
    elif message["role"] == "tool_call":
        _render_tool_call(message)
    elif message["role"] == "artifact":
        _render_artifact_message(message)


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
            with st.expander(f"{message['name']} : {result_text[:25]}...", expanded=False):
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
    """Stream response using live container system with real-time namespace separation."""

    try:
        # Get or create streaming service
        if "streaming_service" not in st.session_state:
            st.session_state.streaming_service = create_streaming_service()

        service = st.session_state.streaming_service

        # Set up live container update callback
        service.set_container_update_callback(_update_live_containers)

        input_state = {"messages": [HumanMessage(content=user_input)], "artifacts": [], "research_iteration": 0}
        config = {"configurable": {"thread_id": st.session_state.thread_id}}

        # Process streaming events (service handles live_chat updates and container updates)
        async def process_live_events():
            """Process events with live container updates."""
            async for event in service.stream_conversation(st.session_state.current_graph, input_state, config):
                # Service handles everything - just wait for completion
                pass

        with st.container().empty():
            asyncio.run(process_live_events())

        # Finalize: transfer to history and cleanup
        _finalize_run_live_streaming()

    except Exception as e:
        st.error(f"Error in live container streaming: {str(e)}")
        st.exception(e)


def _init_chat_session():
    """Initialize chat session state."""
    if "thread_id" not in st.session_state:
        st.session_state.thread_id = str(uuid.uuid4())
        st.session_state.user_id = "demo_user"

    # Live Container Architecture - Complete State Structure
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []  # Final conversation history

    if "live_chat" not in st.session_state:
        st.session_state.live_chat = []  # Current live conversation (same structure as chat_history)

    if "live_speakers" not in st.session_state:
        st.session_state.live_speakers = {}  # namespace -> container mapping

    if "streaming_service" not in st.session_state:
        st.session_state.streaming_service = create_streaming_service()


# Live Container Management Functions


def _update_live_containers():
    """Update live containers maintaining chronological order."""

    # Clear all existing containers first (fresh render)
    _clear_live_containers()

    current_container = None

    # Process messages chronologically (preserves conversation order)

    for message in st.session_state.live_chat:
        message_namespace = message.get("namespace", "main")

        current_container = _get_or_create_namespace_container(message_namespace)

        with current_container:
            _render_messages(message)


def _get_or_create_namespace_container(namespace):
    """Get or create container for namespace with visual separation."""
    if namespace not in st.session_state.live_speakers:
        # Create new container with namespace header
        container = st.container()
        if namespace != "main":
            with container:
                speaker = get_speaker_for_namespace(namespace)
                avatar = get_avatar(speaker)
                st.markdown(f"### {avatar} {speaker}")
                st.markdown("---")

        st.session_state.live_speakers[namespace] = container

    return st.session_state.live_speakers[namespace]


def _clear_live_containers():
    """Clear all live containers."""

    if "live_speakers" in st.session_state and st.session_state.live_speakers:
        st.session_state.live_speakers = {}


def _finalize_run_live_streaming():
    """Transfer live_chat to chat_history and cleanup live containers."""

    # Transfer live conversation to history
    st.session_state.chat_history.extend(st.session_state.live_chat)

    # Clear live state
    st.session_state.live_chat = []
    st.session_state.live_speakers = {}

    # Rerun to show final history
    st.rerun()


def _clear_conversation():
    """Clear the conversation and reset session."""
    st.session_state.messages = []  # Legacy
    st.session_state.chat_history = []  # New architecture
    st.session_state.live_chat = []
    st.session_state.thread_id = str(uuid.uuid4())

    # Clear live containers
    _clear_live_containers()

    # Reset streaming service
    if "streaming_service" in st.session_state:
        st.session_state.streaming_service.reset_session()

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
