"""
Multi-Provider LLM Chat Interface

A Streamlit application for testing and interacting with different LLM providers
including LLMaaS, LLMaaS Dev, and Custom providers with configurable settings.
"""

import streamlit as st
from dotenv import load_dotenv
from frontend.components import render_chat_interface, render_sidebar
from frontend.services import init_session_state

# Load environment variables
load_dotenv()


def main():
    """Main application entry point."""
    # Page config
    st.set_page_config(page_title="Multi-Provider LLM Chat", page_icon="🤖", layout="wide")

    # Initialize session state
    init_session_state()

    # Header
    st.title("🤖 Multi-Provider LLM Chat Interface")
    st.markdown("Configure and test different LLM providers with ease!")

    # Render components
    render_sidebar()
    render_chat_interface()


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()

    main()
