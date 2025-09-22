"""New chat interface UI component with graph catalog integration."""

import uuid

import streamlit as st
from langchain_core.messages import HumanMessage

from frontend.services.streaming_v2 import run_async_streaming
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
        st.markdown(
            f"<span style='font-size:0.95em;'>"
            f"🟢 <b>{st.session_state.current_provider}</b> &nbsp;|&nbsp; "
            f"🧠 <b>{st.session_state.current_graph_info.name}</b> &nbsp;|&nbsp; "
            f"🧵 <code>{st.session_state.thread_id}</code>"
            f"</span>",
            unsafe_allow_html=True,
        )

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
            st.rerun()


def _render_chat_area():
    """Render the chat messages and input area."""
    # Display chat history with inline artifact handling
    for message in st.session_state.messages:
        # Handle different message types for natural chat flow
        if message["role"] in ["user", "assistant"]:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

                # Handle artifacts inline with message
                if "artifacts" in message and message["artifacts"]:
                    selected_artifact_id = render_artifacts(
                        message["artifacts"], key_prefix=f"msg_{message.get('message_id', 'unknown')}"
                    )

                    if selected_artifact_id:
                        # Process artifact selection as a new user interaction
                        selected_artifact = next(
                            (a for a in message["artifacts"] if a.id == selected_artifact_id), None
                        )
                        if selected_artifact:
                            artifact_content = f"Selected: {selected_artifact.title}. {selected_artifact.description}"
                            _process_interaction(artifact_content)
                            st.rerun()
                            return

        elif message["role"] == "tool_call":
            # Display tool call as assistant message
            with st.chat_message("assistant"):
                st.markdown(message["content"])
                if message.get("status") == "executing":
                    with st.spinner(f"Executing {message.get('tool_name', 'tool')}..."):
                        st.empty()

        elif message["role"] == "tool_result":
            # Display tool result as assistant message
            with st.chat_message("assistant"):
                st.markdown(message["content"])

                # Add expandable section for full result if available
                if message.get("full_result") and len(str(message["full_result"])) > 200:
                    with st.expander("View full result", expanded=False):
                        st.text(str(message["full_result"]))

    # Handle user text input
    if prompt := st.chat_input("What would you like to ask?"):
        _process_interaction(prompt)


def _process_interaction(content: str):
    """Unified processing for all user interactions (text input and artifact selections)."""
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": content})

    # Display user message
    with st.chat_message("user"):
        st.markdown(content)

    # Generate and display assistant response
    with st.chat_message("assistant"):
        _stream_graph_response(content)


def _stream_graph_response(content: str):
    """Stream graph response and handle artifacts in a unified way."""
    try:
        # Check if graph is available
        if not st.session_state.get("current_graph"):
            st.error("No agent selected. Please select an agent in the sidebar.")
            return

        # Create input state for the graph
        input_state = {
            "messages": [HumanMessage(content=content)],
            "artifacts": [],
        }

        # Configuration with thread_id and context
        config = {"configurable": {"thread_id": st.session_state.thread_id}}
        context = {"user_id": st.session_state.user_id}

        # Check if this is a supervisor agent for advanced streaming
        graph_id = st.session_state.get("current_graph_id", "")
        is_supervisor = graph_id == "supervisor_agent"

        if is_supervisor:
            # Use new async streaming for supervisor agent with chat flow integration
            result = run_async_streaming(st.session_state.current_graph, input_state, config, context)

            response_content = result["response"]
            response_artifacts = result["artifacts"]

            # The streaming handler already added all messages to session state
            # No need to display anything here as it's handled in the chat flow
            return

        else:
            # Use traditional streaming for other agents
            with st.spinner(f"Processing with {st.session_state.current_graph_info.name}..."):
                response_content = ""
                response_artifacts = []

                for chunk in st.session_state.current_graph.stream(
                    input_state,
                    config=config,
                    context=context,
                    stream_mode="values",
                ):
                    if isinstance(chunk, dict):
                        if "messages" in chunk and chunk["messages"]:
                            latest_message = chunk["messages"][-1]
                            if hasattr(latest_message, "content"):
                                response_content = latest_message.content

                        if "artifacts" in chunk and chunk["artifacts"]:
                            response_artifacts = chunk["artifacts"]

        # Display response content and handle artifacts (common for both modes)
        if response_content:
            if not is_supervisor:  # Only display if not already shown in async mode
                st.markdown(response_content)

            # Create message data with artifacts
            message_id = str(uuid.uuid4())
            message_data = {"role": "assistant", "content": response_content, "message_id": message_id}

            # Add artifacts to message if present
            if response_artifacts:
                message_data["artifacts"] = response_artifacts

                # Display artifacts immediately in current context
                selected_artifact_id = render_artifacts(response_artifacts, key_prefix=f"current_{message_id}")

                # Handle immediate artifact selection
                if selected_artifact_id:
                    selected_artifact = next((a for a in response_artifacts if a.id == selected_artifact_id), None)
                    if selected_artifact:
                        # Add to chat history first
                        st.session_state.messages.append(message_data)

                        # Process artifact selection
                        artifact_content = f"Selected: {selected_artifact.title}. {selected_artifact.description}"
                        _process_interaction(artifact_content)
                        st.rerun()
                        return

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
        st.session_state.user_id = str("h88214")

    if "messages" not in st.session_state:
        st.session_state.messages = []


def _get_current_temperature() -> float:
    """Get current temperature from creativity selection."""
    selected_creativity = st.session_state.get("creativity_select", CreativityLevel.MEDIUM.value)
    creativity_level = CreativityLevel.from_string(selected_creativity)
    return creativity_level.temperature
