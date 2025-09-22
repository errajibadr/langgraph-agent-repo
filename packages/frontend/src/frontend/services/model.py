"""Model connection and management service."""

from typing import Optional

import streamlit as st
from ai_engine.models.custom_chat_model import CustomChatModel
from core.types import ProviderType


def auto_connect_model(
    provider: ProviderType,
    api_key: str,
    base_url: str,
    model: str,
    temperature: float,
    top_p: Optional[float],
    max_tokens: int,
    provider_name: str,
) -> bool:
    """Auto-connect to a model and update session state."""
    if not all([api_key, base_url, model]):
        return False

    try:
        # Create model instance
        kwargs = {
            "provider": provider,
            "api_key": api_key,
            "base_url": base_url,
            "model": model,
            "temperature": temperature,
            "top_p": top_p,  # Always pass top_p, even if None (so model can filter it out)
            "max_tokens": max_tokens,
        }

        new_model = CustomChatModel(**kwargs)

        model_message = "Model" if "current_model" not in st.session_state else "🔄 Model Updated"
        # Check if this is a different model
        model_changed = (
            "current_model" not in st.session_state
            or st.session_state.get("current_model_name") != model
            or st.session_state.get("current_provider") != provider_name
        )

        # Store in session state
        st.session_state.current_model = new_model
        st.session_state.current_provider = provider_name
        st.session_state.current_model_name = model

        # Add system message if model changed
        if model_changed and "messages" in st.session_state:
            top_p_display = "Disabled" if top_p is None else f"{top_p}"
            system_msg = f" **{model_message}** - {provider_name}: `{model}` (T={temperature}, P={top_p_display}, Max={max_tokens})"
            st.session_state.messages.append({"role": "assistant", "content": system_msg})

        return True
    except Exception:
        return False
