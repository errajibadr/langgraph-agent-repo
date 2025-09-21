"""New chat interface UI component with graph catalog integration."""

import uuid
from typing import Any, Dict

import streamlit as st
from langchain_core.messages import HumanMessage

from frontend.services.graph_catalog import catalog
from frontend.types import CreativityLevel

from .artifacts_display import render_artifacts
from .configuration import render_example_configurations


def render_chat_interface():
    """Render the main chat interface with graph catalog support."""
    # Initialize session if needed
    _init_chat_session()

    # Header with clear button
    _render_header()

    # Check if we have both a model and a graph
    has_model = "current_model" in st.session_state
    has_graph = "current_graph" in st.session_state

    if has_model and has_graph:
        st.info(f"🟢 Connected to **{st.session_state.current_provider}** provider")
        st.info(f"🧠 Using **{st.session_state.current_graph_info.name}** agent")
        st.info(f"🧵 Thread ID: {st.session_state.thread_id}")

        # Main chat area
        _render_chat_area()

    elif not has_model:
        st.info("👈 Please configure a provider in the sidebar and test the connection to start chatting!")
        render_example_configurations()

    elif not has_graph:
        st.info("👈 Please select an AI agent in the sidebar to start chatting!")

    else:
        st.error("Unexpected state - please refresh the page")


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
            # Clear any pending artifacts
            if "pending_artifacts" in st.session_state:
                del st.session_state.pending_artifacts
            st.rerun()


def _render_chat_area():
    """Render the chat messages and input area."""
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

            # Display artifacts if present in message
            if "artifacts" in message and message["artifacts"]:
                _render_message_artifacts(message["artifacts"], message.get("message_id", "unknown"))

    # Handle pending artifacts from last response
    if st.session_state.get("pending_artifacts"):
        selected_artifact_id = render_artifacts(
            st.session_state.pending_artifacts, key_prefix=f"pending_{st.session_state.thread_id}"
        )

        if selected_artifact_id:
            # User selected an artifact - process it as a new message
            selected_artifact = next(
                (a for a in st.session_state.pending_artifacts if a.id == selected_artifact_id), None
            )
            if selected_artifact:
                _process_artifact_selection(selected_artifact)
                return

    # Chat input with message processing
    if prompt := st.chat_input("What would you like to ask?"):
        _process_user_message(prompt)


def _render_message_artifacts(artifacts, message_id: str):
    """Render artifacts that are part of a chat message."""
    if not artifacts:
        return

    selected_artifact_id = render_artifacts(artifacts, key_prefix=f"msg_{message_id}")

    if selected_artifact_id:
        selected_artifact = next((a for a in artifacts if a.id == selected_artifact_id), None)
        if selected_artifact:
            _process_artifact_selection(selected_artifact)


def _process_artifact_selection(artifact):
    """Process user selection of an artifact."""
    # Add user selection as a message
    selection_message = f"Selected: {artifact.title}"
    st.session_state.messages.append({"role": "user", "content": selection_message})

    # Clear pending artifacts
    if "pending_artifacts" in st.session_state:
        del st.session_state.pending_artifacts

    # Process the selection (for now, just acknowledge it)
    with st.chat_message("assistant"):
        response = f"✅ You selected: **{artifact.title}**\n\n{artifact.description}\n\nI'll proceed with this choice."
        st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})


def _process_user_message(prompt: str):
    """Process user message using the selected graph."""
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Generate assistant response using selected graph
    with st.chat_message("assistant"):
        try:
            # Check if graph is available
            if not st.session_state.get("current_graph"):
                st.error("No agent selected. Please select an agent in the sidebar.")
                return

            with st.spinner(f"Processing with {st.session_state.current_graph_info.name}..."):
                # Create input state for the graph
                state_schema = st.session_state.current_state_schema
                input_state = state_schema(
                    messages=[HumanMessage(content=prompt)], current_round=0, max_rounds=3, artifacts=[]
                )

                # Configuration with thread_id
                config = {"configurable": {"thread_id": st.session_state.thread_id}}

                # Stream the graph
                response_content = ""
                response_artifacts = []

                for chunk in st.session_state.current_graph.stream(
                    input_state,
                    config=config,  # type: ignore
                    stream_mode="values",
                ):
                    if isinstance(chunk, dict):
                        if "messages" in chunk and chunk["messages"]:
                            latest_message = chunk["messages"][-1]
                            if hasattr(latest_message, "content"):
                                response_content = latest_message.content

                        if "artifacts" in chunk and chunk["artifacts"]:
                            response_artifacts = chunk["artifacts"]

                if response_content:
                    st.markdown(response_content)

                    # Create message with artifacts
                    message_id = str(uuid.uuid4())
                    message_data = {"role": "assistant", "content": response_content, "message_id": message_id}

                    if response_artifacts:
                        message_data["artifacts"] = response_artifacts
                        # Store artifacts as pending for interaction
                        st.session_state.pending_artifacts = response_artifacts

                    # Add to chat history
                    st.session_state.messages.append(message_data)
                else:
                    st.warning("No response received from agent.")

        except Exception as e:
            st.error(f"Error generating response: {str(e)}")
            st.exception(e)


def _init_chat_session():
    """Initialize chat session state."""
    if "thread_id" not in st.session_state:
        st.session_state.thread_id = str(uuid.uuid4())

    if "messages" not in st.session_state:
        st.session_state.messages = []


def _get_current_temperature() -> float:
    """Get current temperature from creativity selection."""
    selected_creativity = st.session_state.get("creativity_select", CreativityLevel.MEDIUM.value)
    creativity_level = CreativityLevel.from_string(selected_creativity)
    return creativity_level.temperature
