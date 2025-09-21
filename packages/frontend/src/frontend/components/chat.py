"""Chat interface UI component."""

import os

# Import clarification graph
import sys
import uuid

import streamlit as st
from langchain_core.messages import HumanMessage

from frontend.types import CreativityLevel

from .configuration import render_example_configurations


def render_chat_interface():
    """Render the main chat interface with 2-row layout."""
    # Initialize clarification graph and thread_id if not exists
    _init_clarification_session()

    # Header with clear button
    _render_header()

    if "current_model" in st.session_state:
        st.info(f"🟢 Connected to **{st.session_state.current_provider}** provider")
        st.info(f"🧵 Thread ID: {st.session_state.thread_id}")

        # Row 1: Chat area (messages + input)
        _render_chat_area()

        # Row 2: Settings controls
        # st.markdown("---")  # Visual separator
        # selected_model, selected_temperature = render_chat_settings()

    else:
        st.info("👈 Please configure a provider in the sidebar and test the connection to start chatting!")
        render_example_configurations()


def _render_header():
    """Render the header with clear conversation button."""
    col1, col2 = st.columns([4, 1])
    with col1:
        st.header("💬 Chat Interface")
    with col2:
        if st.button("🗑️ Clear", help="Clear conversation history"):
            st.session_state.messages = []
            # Generate new thread_id for new conversation
            st.session_state.thread_id = str(uuid.uuid4())
            st.rerun()


def _render_chat_area():
    """Render the chat messages and input area."""
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input with message processing
    if prompt := st.chat_input("What would you like to ask?"):
        _process_user_message(prompt)


def _process_user_message(prompt: str):
    """Process user message using clarification graph."""
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Generate assistant response using clarification graph
    with st.chat_message("assistant"):
        try:
            # Check if clarification graph is available
            if not hasattr(st.session_state, "clarify_graph") or st.session_state.clarify_graph is None:
                st.error("Clarification graph not initialized. Please refresh the page.")
                return

            with st.spinner("Processing with clarification agent..."):
                # Create input state for the graph
                InputState = st.session_state.InputState
                input_state = InputState(messages=[HumanMessage(content=prompt)])

                # Configuration with thread_id
                config = {"configurable": {"thread_id": st.session_state.thread_id}}

                # Stream the clarification graph
                response_content = ""
                for mode, chunk in st.session_state.clarify_graph.stream(
                    input_state,
                    config=config,
                    stream_mode=["values"],
                ):
                    if chunk and "messages" in chunk and chunk["messages"]:
                        latest_message = chunk["messages"][-1]
                        if hasattr(latest_message, "content"):
                            response_content = latest_message.content

                if response_content:
                    st.markdown(response_content)
                    # Add to chat history
                    st.session_state.messages.append({"role": "assistant", "content": response_content})
                else:
                    st.warning("No response received from clarification agent.")

        except Exception as e:
            st.error(f"Error generating response: {str(e)}")
            st.error(f"Details: {type(e).__name__}: {str(e)}")


def _init_clarification_session():
    """Initialize clarification graph and thread_id in session state."""
    if "thread_id" not in st.session_state:
        st.session_state.thread_id = str(uuid.uuid4())

    if "clarify_graph" not in st.session_state:
        # Dynamic import to avoid linting issues
        experiments_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..", "experiments"))
        if experiments_path not in sys.path:
            sys.path.append(experiments_path)
            sys.path.append(
                os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..", "langgraph-agent-repo"))
            )

        try:
            from experiments.agents.clarify import ClarifyState, get_clarify_graph

            print("Initializing clarification graph...")
            # Initialize the clarification graph
            st.session_state.clarify_graph = get_clarify_graph(
                state_schema=ClarifyState,
                name="ClarifyWithUser",
                system_prompt=None,  # Will use default CLARIFY_AIOPS_PROMPT
                enrich_query_enabled=True,
            )
            st.session_state.InputState = ClarifyState
        except ImportError as e:
            st.error(f"Failed to import clarification graph: {e}")
            return


def _get_current_temperature() -> float:
    """Get current temperature from creativity selection."""
    selected_creativity = st.session_state.get("creativity_select", CreativityLevel.MEDIUM.value)
    creativity_level = CreativityLevel.from_string(selected_creativity)
    return creativity_level.temperature
