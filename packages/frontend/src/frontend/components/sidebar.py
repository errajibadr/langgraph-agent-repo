"""Sidebar UI component with provider configuration and model selection."""

import os
from typing import Optional, Tuple

import streamlit as st
from core.types import ProviderType
from core.utils import get_env_values, get_provider_configs

from ..services.api import fetch_models_from_api
from ..services.model import auto_connect_model
from .configuration import render_llm_configuration
from .provider import render_model_selection, render_provider_selector


def render_sidebar() -> Tuple[ProviderType, str, str, str, str, float, Optional[float], int]:
    """Render the sidebar with provider configuration."""
    with st.sidebar:
        st.header("⚙️ Configuration")

        # Provider selection (always visible)
        selected_provider, selected_provider_name = render_provider_selector()
        provider_configs = get_provider_configs()
        provider_config = provider_configs[selected_provider]

        # Get environment values
        env_api_key, env_base_url, env_model_name, env_temperature, env_top_p, env_max_tokens = get_env_values(
            provider_config, selected_provider
        )

        # Auto-fetch models when provider changes and credentials are available
        should_auto_fetch = (
            env_api_key
            and env_base_url
            and (
                st.session_state.models_provider != selected_provider.value or len(st.session_state.fetched_models) == 0
            )
        )

        if should_auto_fetch:
            with st.spinner("Auto-fetching models..."):
                fetched_models = fetch_models_from_api(env_base_url, env_api_key)
                if fetched_models:
                    st.session_state.fetched_models = fetched_models
                    st.session_state.models_provider = selected_provider.value
                    st.rerun()

        # Collapsible Provider Configuration Section
        with st.expander(f"🔧 {selected_provider_name} Provider", expanded=True):
            # Configuration inputs
            api_key = st.text_input(
                f"API Key ({provider_config.get('api_key_env', 'API_KEY')})",
                value=env_api_key,
                type="password",
                help=f"Set via environment variable {provider_config.get('api_key_env', 'API_KEY')}",
            )

            base_url = st.text_input(
                f"Base URL ({provider_config.get('base_url_env', 'BASE_URL')})",
                value=env_base_url or provider_config.get("default_base_url", ""),
                help=f"Set via environment variable {provider_config.get('base_url_env', 'BASE_URL')}",
            )

            # Model fetching controls
            col1, col2 = st.columns([3, 1])
            with col1:
                if st.button("🔍 Fetch Available Models", disabled=not (api_key and base_url)):
                    with st.spinner("Fetching models..."):
                        fetched_models = fetch_models_from_api(base_url, api_key)
                        st.session_state.fetched_models = fetched_models
                        st.session_state.models_provider = selected_provider.value
                        if fetched_models:
                            st.rerun()

            with col2:
                if st.session_state.fetched_models and st.button("🗑️"):
                    st.session_state.fetched_models = []
                    st.rerun()

            # Model selection with auto-connect
            selected_model = render_model_selection(selected_provider, provider_config, env_model_name)

        # LLM Configuration Section
        has_top_p_env = bool(os.getenv(provider_config.get("top_p_env", "TOP_P")))
        temperature, top_p, max_tokens = render_llm_configuration(
            env_temperature, env_top_p, env_max_tokens, has_top_p_env
        )

        # Auto-connect when model is selected or LLM parameters change
        should_auto_connect = selected_model and api_key and base_url

        if should_auto_connect:
            # Check if any configuration has changed
            current_config = {
                "model": selected_model,
                "provider": selected_provider_name,
                "temperature": temperature,
                "top_p": top_p,
                "max_tokens": max_tokens,
            }

            last_config = st.session_state.get("last_config", {})
            config_changed = current_config != last_config

            if config_changed:
                # Show what changed for debugging
                if "last_config" in st.session_state and st.session_state.last_config:
                    old_top_p = st.session_state.last_config.get("top_p")
                    if old_top_p != top_p:
                        top_p_old = "Disabled" if old_top_p is None else f"{old_top_p}"
                        top_p_new = "Disabled" if top_p is None else f"{top_p}"
                        st.info(f"🔄 Top P changed: {top_p_old} → {top_p_new}")

                auto_connect_success = auto_connect_model(
                    selected_provider,
                    api_key,
                    base_url,
                    selected_model,
                    temperature,
                    top_p,
                    max_tokens,
                    selected_provider_name,
                )
                if auto_connect_success:
                    st.success(f"🟢 Connected to **{selected_model}**")
                    st.session_state.last_config = current_config
                else:
                    st.error("❌ Auto-connection failed")

        # Manual test connection (now optional)
        if st.button("🧪 Manual Test Connection"):
            if not all([api_key, base_url, selected_model]):
                st.error("Please fill in all required fields!")
            else:
                success = auto_connect_model(
                    selected_provider,
                    api_key,
                    base_url,
                    selected_model,
                    temperature,
                    top_p,
                    max_tokens,
                    selected_provider_name,
                )
                if success:
                    st.success("✅ Manual connection successful!")
                else:
                    st.error("❌ Manual connection failed!")

        # Current configuration display
        with st.expander("📋 Current Configuration"):
            config_display = {
                "provider": selected_provider.value,
                "api_key": f"{api_key[:8]}..." if api_key else "Not set",
                "base_url": base_url,
                "model": selected_model,
                "temperature": temperature,
                "top_p": "Disabled (None)" if top_p is None else top_p,
                "max_tokens": max_tokens,
            }
            st.json(config_display)

    return selected_provider, selected_provider_name, api_key, base_url, selected_model, temperature, top_p, max_tokens
