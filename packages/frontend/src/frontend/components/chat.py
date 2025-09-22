"""New chat interface UI component with graph catalog integration."""

import uuid

import streamlit as st
from langchain_core.messages import HumanMessage

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
        st.write(f"🔍 DEBUG: Rendering {len(st.session_state.pending_artifacts)} pending artifacts")  # Debug

        # Use a unique key based on artifacts to prevent conflicts
        artifacts_key = f"pending_{len(st.session_state.pending_artifacts)}_{hash(str([a.id for a in st.session_state.pending_artifacts]))}"

        selected_artifact_id = render_artifacts(st.session_state.pending_artifacts, key_prefix=artifacts_key)

        if selected_artifact_id:
            # User selected an artifact - process it as a new message
            selected_artifact = next(
                (a for a in st.session_state.pending_artifacts if a.id == selected_artifact_id), None
            )
            if selected_artifact:
                st.write(f"🔍 DEBUG: Processing artifact selection: {selected_artifact.title}")
                _process_artifact_selection(selected_artifact)
                st.rerun()  # Force rerun to clear pending artifacts
                return
    else:
        st.write("🔍 DEBUG: No pending artifacts found")  # Debug

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

    # Continue the clarification workflow with the selection
    with st.chat_message("assistant"):
        try:
            with st.spinner("Processing your selection..."):
                # Create follow-up message to send back to clarify agent
                follow_up_message = f"I selected: {artifact.title}. {artifact.description}"

                # Create input state with the selection

                input_state = {
                    "messages": [HumanMessage(content=follow_up_message)],
                    "artifacts": [],
                }

                # Configuration with thread_id
                config = {"configurable": {"thread_id": st.session_state.thread_id}}

                # Stream the graph again with the selection
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

                    # Create message with potential new artifacts
                    message_id = str(uuid.uuid4())
                    message_data = {"role": "assistant", "content": response_content, "message_id": message_id}

                    if response_artifacts:
                        message_data["artifacts"] = response_artifacts
                        st.session_state.pending_artifacts = response_artifacts

                    # Add to chat history
                    st.session_state.messages.append(message_data)
                else:
                    # Fallback acknowledgment
                    response = f"✅ You selected: **{artifact.title}**\n\n{artifact.description}\n\nI'll proceed with this choice."
                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})

        except Exception as e:
            st.error(f"Error processing selection: {str(e)}")
            # Fallback acknowledgment
            response = (
                f"✅ You selected: **{artifact.title}**\n\n{artifact.description}\n\nI'll proceed with this choice."
            )
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
                input_state = {
                    "messages": [HumanMessage(content=prompt)],
                    "artifacts": [],
                }

                # Configuration with thread_id
                config = {"configurable": {"thread_id": st.session_state.thread_id}}
                context = {"user_id": st.session_state.user_id}

                # Stream the graph
                response_content = ""
                response_artifacts = []

                for chunk in st.session_state.current_graph.stream(
                    input_state,
                    config=config,  # type: ignore
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
                            st.write(f"🔍 DEBUG: Found {len(response_artifacts)} artifacts")  # Debug

                if response_content:
                    st.markdown(response_content)

                    # Create message with artifacts
                    message_id = str(uuid.uuid4())
                    message_data = {"role": "assistant", "content": response_content, "message_id": message_id}

                    if response_artifacts:
                        st.write(f"🔍 DEBUG: Adding {len(response_artifacts)} artifacts to message")  # Debug
                        message_data["artifacts"] = response_artifacts
                        # Store artifacts as pending for interaction (don't display immediately)
                        st.session_state.pending_artifacts = response_artifacts
                        st.write(f"🔍 DEBUG: Artifacts stored as pending: {[a.id for a in response_artifacts]}")
                        st.write(f"🔍 DEBUG: Session state keys after storing: {list(st.session_state.keys())}")
                    else:
                        st.write("🔍 DEBUG: No artifacts in response")  # Debug

                    # Add to chat history
                    st.session_state.messages.append(message_data)

                    # If we have artifacts, force a rerun to display them
                    if response_artifacts:
                        st.write("🔍 DEBUG: Forcing rerun to display artifacts")
                        st.rerun()
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
