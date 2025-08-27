"""Chat interface UI component."""

import streamlit as st

from .configuration import render_example_configurations


def render_chat_interface():
    """Render the main chat interface."""
    st.header("💬 Chat Interface")

    if "current_model" in st.session_state:
        st.info(f"🟢 Connected to **{st.session_state.current_provider}** provider")

        # Display chat history
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # Chat input
        if prompt := st.chat_input("What would you like to ask?"):
            # Add user message
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            # Generate assistant response
            with st.chat_message("assistant"):
                try:
                    with st.spinner("Thinking..."):
                        response = st.session_state.current_model.invoke(prompt)
                        response_content = response.content if hasattr(response, "content") else str(response)
                        st.markdown(response_content)

                        # Add to chat history
                        st.session_state.messages.append({"role": "assistant", "content": response_content})

                except Exception as e:
                    st.error(f"Error generating response: {str(e)}")
    else:
        st.info("👈 Please configure a provider in the sidebar and test the connection to start chatting!")
        render_example_configurations()
