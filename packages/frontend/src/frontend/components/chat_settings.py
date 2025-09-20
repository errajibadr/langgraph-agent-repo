"""Chat settings components for model and creativity selection."""

from typing import Tuple

import streamlit as st

from frontend.types import CreativityLevel


def render_chat_settings() -> Tuple[str | None, float]:
    """
    Render model and creativity selection controls.

    Returns:
        Tuple of (selected_model, selected_temperature)
    """
    col1, col2 = st.columns([2, 2])

    with col1:
        selected_model = _render_model_selector()

    with col2:
        selected_temperature = _render_creativity_selector()

    return selected_model, selected_temperature


def _render_model_selector() -> str | None:
    """Render model selection dropdown."""
    available_models = [model.get("id", "Unknown") for model in st.session_state.get("fetched_models", [])]

    if not available_models:
        st.text("No models available")
        return None

    current_model = st.session_state.get("current_model_name", available_models[0])
    default_index = available_models.index(current_model) if current_model in available_models else 0

    selected_model = st.selectbox(
        "🤖 Model",
        options=available_models,
        index=default_index,
        key="quick_model_select",
    )

    return selected_model


def _render_creativity_selector() -> float:
    """Render creativity level selection dropdown."""
    creativity_options = CreativityLevel.get_options()

    # Get current selection or default to MEDIUM
    current_creativity = st.session_state.get("creativity_select", CreativityLevel.MEDIUM.value)
    default_index = (
        creativity_options.index(current_creativity) if current_creativity in creativity_options else 2  # MEDIUM index
    )

    selected_creativity_str = st.selectbox(
        "🎨 Creativity",
        options=creativity_options,
        index=default_index,
        key="creativity_select",
    )

    # Convert to temperature
    creativity_level = CreativityLevel.from_string(selected_creativity_str)
    return creativity_level.temperature
