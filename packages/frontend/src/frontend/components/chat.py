"""Chat interface UI component."""

import streamlit as st

from frontend.types import CreativityLevel

from .chat_settings import render_chat_settings
from .configuration import render_example_configurations


def render_chat_interface():
    """Render the main chat interface with 2-row layout."""
    # Header with clear button
    _render_header()

    if "current_model" in st.session_state:
        st.info(f"🟢 Connected to **{st.session_state.current_provider}** provider")

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
    """Process user message and generate AI response."""
    # Get current settings
    selected_temperature = _get_current_temperature()

    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Generate assistant response
    with st.chat_message("assistant"):
        try:
            with st.spinner("Thinking..."):
                # Update model temperature
                if hasattr(st.session_state.current_model, "temperature"):
                    st.session_state.current_model.temperature = selected_temperature

                response = st.session_state.current_model.invoke(prompt)
                response_content = response.content if hasattr(response, "content") else str(response)
                st.markdown(response_content)

                # Add to chat history
                st.session_state.messages.append({"role": "assistant", "content": response_content})

        except Exception as e:
            st.error(f"Error generating response: {str(e)}")


def _get_current_temperature() -> float:
    """Get current temperature from creativity selection."""
    selected_creativity = st.session_state.get("creativity_select", CreativityLevel.MEDIUM.value)
    creativity_level = CreativityLevel.from_string(selected_creativity)
    return creativity_level.temperature
