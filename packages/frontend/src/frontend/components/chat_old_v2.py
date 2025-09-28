"""Simplified chat interface with conversational streaming integration."""

import uuid

import streamlit as st
from frontend.services.stream_processor_integration import create_simple_conversational_processor
from frontend.types import CreativityLevel
from langchain_core.messages import HumanMessage

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
    # Display chat history - simplified for basic message streaming
    for message_idx, message in enumerate(st.session_state.messages):
        # Handle basic user and assistant messages
        if message["role"] in ["user", "assistant"]:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

                # Handle artifacts inline with message if present
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

    # Generate and display assistant response with conversational streaming
    import asyncio

    # Handle async streaming in Streamlit context
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(_stream_graph_response(content))
    finally:
        loop.close()


async def _stream_graph_response(content: str):
    """Stream graph response using conversational streaming."""
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

        # Initialize conversational processor for this session
        if "conversational_processor" not in st.session_state:
            st.session_state.conversational_processor = create_simple_conversational_processor()

        processor = st.session_state.conversational_processor

        # Reset for new conversation turn
        processor.reset_session()

        # Show processing indicator
        with st.spinner(f"Processing with {st.session_state.current_graph_info.name}..."):
            # Stream with conversational flow
            final_response = ""
            artifacts = []

            async for event in processor.stream_with_conversation(
                st.session_state.current_graph, input_state, config, context=context, stream_mode="values"
            ):
                # Events are automatically processed by the conversational adapter
                # We just need to extract final data for session state

                # Extract content from TokenStreamEvent
                from ai_engine.streaming.events import ChannelValueEvent, TokenStreamEvent

                if isinstance(event, TokenStreamEvent):
                    if event.accumulated_content:
                        final_response = event.accumulated_content

                # Extract artifacts from ChannelValueEvent
                elif isinstance(event, ChannelValueEvent):
                    if event.channel == "artifacts" and event.value:
                        artifacts = event.value

        # Add final response to session state for persistence
        if final_response:
            message_data = {"role": "assistant", "content": final_response, "message_id": str(uuid.uuid4())}

            # Add artifacts if present (ensure it's a list)
            if artifacts:
                if isinstance(artifacts, list):
                    message_data["artifacts"] = artifacts
                else:
                    # If it's not a list, try to convert or wrap it
                    message_data["artifacts"] = [artifacts] if artifacts is not None else []

            st.session_state.messages.append(message_data)

        # Trigger rerun to show persistent chat history
        st.rerun()

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
    return creativity_level.temperature
