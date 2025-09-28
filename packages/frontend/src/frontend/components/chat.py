"""Simple conversational chat interface using ConversationalStreamAdapter.

Phase 2: Clean, simple chat that leverages the new conversational streaming architecture
built in Phase 1. Starts with basic message streaming and builds from there.
"""

import asyncio
import uuid
from typing import Any, Optional

import streamlit as st
from frontend.services.conversational_stream_adapter import ConversationalStreamAdapter
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
    """Render the conversational chat using the new streaming architecture."""

    # Display existing chat history (this is handled by Streamlit's chat UI naturally)
    # The conversational adapter will handle new streaming messages

    # Display conversation history from session
    # for message in st.session_state.messages:
    #     if message["role"] == "user":
    #         with st.chat_message("user"):
    #             st.markdown(message["content"])
    #     elif message["role"] == "assistant":
    #         with st.chat_message("assistant"):
    #             st.markdown(message["content"])

    # Handle user input
    if prompt := st.chat_input("What would you like to ask?"):
        # Add user message to history
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)

        # Stream AI response
        _stream_conversational_response(prompt)


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
        input_state = {"messages": [HumanMessage(content=user_input)], "artifacts": [], "iteration": 0}

        config = {"configurable": {"thread_id": st.session_state.thread_id}}

        # Run streaming in an async context
        response_content = asyncio.run(_run_streaming_conversation(processor, input_state, config))

        # Add assistant response to history
        if response_content:
            st.session_state.messages.append({"role": "assistant", "content": response_content})
            print(len(st.session_state.messages))

    except Exception as e:
        st.error(f"Error in conversational streaming: {str(e)}")
        st.exception(e)


async def _run_streaming_conversation(
    processor: ConversationalStreamProcessor, input_state: dict[str, Any], config: dict[str, Any]
) -> Optional[str]:
    """Run the conversational streaming process."""
    try:
        graph = st.session_state.current_graph

        # Container for collecting response
        response_content = ""

        # Process streaming events
        async for event in processor.stream_with_conversation(graph, input_state, config):
            # The processor already handles conversational adapter processing internally

            # Collect response content for session state
            if hasattr(event, "accumulated_content") and event.accumulated_content:
                response_content = event.accumulated_content

        return response_content

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
