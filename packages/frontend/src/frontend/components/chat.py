"""New chat interface UI component with graph catalog integration."""

import uuid

import streamlit as st
from langchain_core.messages import HumanMessage

from frontend.services.streaming_v2 import run_async_streaming
from frontend.types import CreativityLevel
from frontend.utils.formatting import beautify_tool_name

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
            # Clear any persisted seen tool ids to avoid stale filtering
            if "seen_tool_call_ids" in st.session_state:
                del st.session_state.seen_tool_call_ids
            if "seen_tool_result_ids" in st.session_state:
                del st.session_state.seen_tool_result_ids
            st.rerun()


def _render_chat_area():
    """Render the chat messages and input area."""
    # Display chat history with inline artifact handling
    for message_idx, message in enumerate(st.session_state.messages):
        # Handle different message types for natural chat flow
        if message["role"] in ["user", "assistant"]:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

                # Handle tool summary with expandable details
                if message.get("tool_summary") and message.get("tool_executions"):
                    with st.expander("🔍 View Detailed Tool Results", expanded=False):
                        for tool_exec in message["tool_executions"]:
                            # Beautify tool name for display
                            beautiful_name = beautify_tool_name(tool_exec["name"])
                            st.markdown(f"**{tool_exec['icon']} {beautiful_name}**")

                            # Show full args
                            if tool_exec.get("args"):
                                st.code(str(tool_exec["args"]), language="json")

                            # Show full result
                            if tool_exec.get("result"):
                                # Generate unique key to prevent duplicates
                                unique_key = f"tool_result_{tool_exec['tool_id']}_{str(uuid.uuid4())[:8]}"
                                st.text_area(
                                    f"Full result from {beautiful_name}:",
                                    str(tool_exec["result"]),
                                    height=100,
                                    disabled=True,
                                    key=unique_key,
                                )

                            st.markdown("---")

                # Handle artifacts inline with message
                if "artifacts" in message and message["artifacts"]:
                    selected_index = render_artifacts(message["artifacts"], key_prefix=f"msg_{message_idx}")

                    if selected_index is not None:
                        # Process artifact selection as a new user interaction
                        if 0 <= selected_index < len(message["artifacts"]):
                            selected_artifact = message["artifacts"][selected_index]
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
    # Clean up old artifacts from previous messages to prevent accumulation
    _cleanup_old_artifacts()

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

        context = {"user_id": st.session_state.user_id, "model": st.session_state.current_model.model_name}

        # Use async streaming for all agents with chat flow integration
        run_async_streaming(st.session_state.current_graph, input_state, config, context)

        # The streaming handler has added all messages to session state
        # Trigger a rerun to refresh the chat display with permanent history
        st.rerun()

        # else:
        #     # Use traditional streaming for other agents
        #     with st.spinner(f"Processing with {st.session_state.current_graph_info.name}..."):
        #         response_content = ""
        #         response_artifacts = []

        #         for chunk in st.session_state.current_graph.stream(
        #             input_state,
        #             config=config,
        #             context=context,
        #             stream_mode="values",
        #         ):
        #             if isinstance(chunk, dict):
        #                 if "messages" in chunk and chunk["messages"]:
        #                     latest_message = chunk["messages"][-1]
        #                     if hasattr(latest_message, "content"):
        #                         response_content = latest_message.content

        #                 if "artifacts" in chunk and chunk["artifacts"]:
        #                     response_artifacts = chunk["artifacts"]

        # Display response content and handle artifacts (common for both modes)
        # if response_content:
        #     if not is_supervisor:  # Only display if not already shown in async mode
        #         st.markdown(response_content)

        #     # Create message data with artifacts
        #     message_id = str(uuid.uuid4())
        #     message_data = {"role": "assistant", "content": response_content, "message_id": message_id}

        #     # Add artifacts to message if present
        #     if response_artifacts:
        #         message_data["artifacts"] = response_artifacts

        #         # Display artifacts immediately in current context
        #         selected_artifact_id = render_artifacts(response_artifacts, key_prefix=f"current_{message_id}")

        #         # Handle immediate artifact selection
        #         if selected_artifact_id:
        #             selected_artifact = next((a for a in response_artifacts if a.id == selected_artifact_id), None)
        #             if selected_artifact:
        #                 # Add to chat history first
        #                 st.session_state.messages.append(message_data)

        #                 # Process artifact selection
        #                 artifact_content = f"Selected: {selected_artifact.title}. {selected_artifact.description}"
        #                 _process_interaction(artifact_content)
        #                 st.rerun()
        #                 return

        #     # Add to chat history
        #     st.session_state.messages.append(message_data)

        # else:
        #     st.warning("No response received from agent.")

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


def _cleanup_old_artifacts():
    """Clean up old artifacts from previous messages to prevent UI conflicts."""
    for message in st.session_state.messages:
        if "artifacts" in message and message["artifacts"]:
            # Convert artifacts to text summary and remove the interactive artifacts
            artifact_summary = []
            for artifact in message["artifacts"]:
                artifact_summary.append(f"• {artifact.title}: {artifact.description}")

            # Add artifact summary to the message content if not already there
            if artifact_summary and "Available options were:" not in message["content"]:
                message["content"] += "\n\n**Available options were:**\n" + "\n".join(artifact_summary)

            # Remove the interactive artifacts
            del message["artifacts"]


def _get_current_temperature() -> float:
    """Get current temperature from creativity selection."""
    selected_creativity = st.session_state.get("creativity_select", CreativityLevel.MEDIUM.value)
    creativity_level = CreativityLevel.from_string(selected_creativity)
    return creativity_level.temperature
