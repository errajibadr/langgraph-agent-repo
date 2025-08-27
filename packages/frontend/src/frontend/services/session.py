"""Session state management for Streamlit frontend."""

import streamlit as st


def init_session_state():
    """Initialize session state variables."""
    if "fetched_models" not in st.session_state:
        st.session_state.fetched_models = []
    if "models_provider" not in st.session_state:
        st.session_state.models_provider = None
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "current_model_name" not in st.session_state:
        st.session_state.current_model_name = None
    if "last_config" not in st.session_state:
        st.session_state.last_config = {}
